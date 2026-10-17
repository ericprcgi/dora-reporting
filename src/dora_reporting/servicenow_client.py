"""Read a major incident and its affected services from ServiceNow (Table API).

The result has the same form as a saved fixture: the incident record, whose
description ends with the DORA classification block, and the affected business
services. Legal entities and contacts come from the reference data.
"""
import os

import requests

INCIDENT_FIELDS = ["sys_id", "number", "short_description", "description", "state"]
SERVICE_FIELDS = ["sys_id", "name"]
ENV_VARS = ("SERVICENOW_INSTANCE", "SERVICENOW_USER", "SERVICENOW_PASSWORD")


class ServiceNowError(Exception):
    """ServiceNow could not be read."""


class IncidentNotFound(ServiceNowError):
    """No incident with the given number."""


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
        try:
            return response.json()["result"]
        except (ValueError, KeyError) as exc:
            # For example the page of a hibernating instance or a login page.
            raise ServiceNowError(f"{table}: response is not Table API JSON") from exc

    def fetch_incident(self, number: str) -> dict:
        incidents = self._get("incident", f"number={number}", INCIDENT_FIELDS)
        if not incidents:
            raise IncidentNotFound(f"{number} not found in ServiceNow")
        links = self._get("task_cmdb_ci_service", f"task.number={number}", ["cmdb_ci_service"])
        ids = [link["cmdb_ci_service"] for link in links]
        services = self._get("cmdb_ci_service", "sys_idIN" + ",".join(ids), SERVICE_FIELDS) if ids else []
        return {
            "incident": incidents[0],
            "affected_services": sorted(services, key=lambda service: service["name"]),
        }
