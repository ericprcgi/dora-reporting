"""Read a major incident and its related records from ServiceNow (Table API).

The result is a snapshot: the incident, the legal entities it refers to, the
affected services and the DORA reporting officer. Values are returned as
ServiceNow stores them (times in UTC, lists as comma-separated sys_ids).
"""
import os

import requests

from dora_reporting import settings

INCIDENT_FIELDS = [
    "sys_id", "number", "short_description", "description", "state", "company",
    "u_dora_major", "u_dora_detected_at", "u_dora_classified_at", "u_dora_criteria",
    "u_dora_discovery", "u_dora_bcp_activated", "u_dora_confirmed_entities",
    "u_dora_confirmed_by", "u_dora_confirmed_at",
]
COMPANY_FIELDS = ["sys_id", "name", "u_lei", "u_dora_entity_type", "parent"]
SERVICE_FIELDS = ["sys_id", "name", "company"]
USER_FIELDS = ["sys_id", "user_name", "name", "email", "phone"]
ENV_VARS = ("SERVICENOW_INSTANCE", "SERVICENOW_USER", "SERVICENOW_PASSWORD")


class ServiceNowError(Exception):
    """ServiceNow could not be read."""


class IncidentNotFound(ServiceNowError):
    """No incident with the given number."""


def _ids(value: str) -> list[str]:
    return [item for item in (value or "").split(",") if item]


class ServiceNowClient:
    def __init__(self, instance: str, user: str, password: str,
                 session: requests.Session | None = None, timeout: float = 30):
        self.base_url = instance.rstrip("/")
        self.session = session or requests.Session()
        self.session.auth = (user, password)
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "ServiceNowClient":
        missing = [name for name in ENV_VARS if not os.environ.get(name)]
        if missing:
            raise ServiceNowError("missing environment variables: " + ", ".join(missing))
        return cls(*(os.environ[name] for name in ENV_VARS))

    def _get(self, table: str, query: str, fields: list[str]) -> list[dict]:
        params = {
            "sysparm_query": query,
            "sysparm_fields": ",".join(fields),
            "sysparm_exclude_reference_link": "true",
            "sysparm_display_value": "false",
        }
        try:
            response = self.session.get(f"{self.base_url}/api/now/table/{table}",
                                        params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ServiceNowError(f"{table}: request failed ({type(exc).__name__})") from exc
        if response.status_code != 200:
            raise ServiceNowError(f"{table}: HTTP {response.status_code}")
        return response.json()["result"]

    def _get_by_ids(self, table: str, ids: list[str], fields: list[str]) -> list[dict]:
        return self._get(table, "sys_idIN" + ",".join(ids), fields) if ids else []

    def fetch_snapshot(self, number: str) -> dict:
        incidents = self._get("incident", f"number={number}", INCIDENT_FIELDS)
        if not incidents:
            raise IncidentNotFound(f"{number} not found in ServiceNow")
        incident = incidents[0]

        links = self._get("task_cmdb_ci_service", f"task.number={number}", ["cmdb_ci_service"])
        services = self._get_by_ids("cmdb_ci_service", [l["cmdb_ci_service"] for l in links],
                                    SERVICE_FIELDS)

        company_ids = {incident["company"], *_ids(incident["u_dora_confirmed_entities"])}
        company_ids |= {service["company"] for service in services}
        companies = self._get_by_ids("core_company", sorted(company_ids - {""}), COMPANY_FIELDS)

        user_name = settings.REPORTING_OFFICER_USER_NAME
        officers = self._get("sys_user", f"user_name={user_name}", USER_FIELDS)
        if not officers:
            raise ServiceNowError(f"reporting officer {user_name} not found in ServiceNow")

        return {
            "incident": incident,
            "companies": {company["sys_id"]: company for company in companies},
            "affected_services": sorted(services, key=lambda service: service["name"]),
            "reporting_officer": officers[0],
        }
