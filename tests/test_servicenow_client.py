import pytest
import requests

from dora_reporting.servicenow_client import IncidentNotFound, ServiceNowClient, ServiceNowError


class FakeResponse:
    def __init__(self, status_code, result=None):
        self.status_code = status_code
        self._result = result or []

    def json(self):
        return {"result": self._result}


class FakeTableApi:
    """Answers Table API GET requests from in-memory tables, honouring
    sysparm_query (field=value or sys_idIN...) and sysparm_fields."""

    def __init__(self, tables, status_code=200, error=None):
        self.tables, self.status_code, self.error = tables, status_code, error
        self.auth, self.headers, self.requests = None, {}, []

    def get(self, url, params, timeout):
        table = url.rsplit("/api/now/table/", 1)[1]
        self.requests.append((table, params))
        if self.error:
            raise self.error
        if self.status_code != 200:
            return FakeResponse(self.status_code)
        query, fields = params["sysparm_query"], params["sysparm_fields"].split(",")
        if query.startswith("sys_idIN"):
            ids = query.removeprefix("sys_idIN").split(",")
            rows = [r for r in self.tables[table] if r["sys_id"] in ids]
        else:
            key, value = query.split("=", 1)
            rows = [r for r in self.tables[table] if r[key] == value]
        return FakeResponse(200, [{f: row[f] for f in fields if f in row} for row in rows])


def tables_from(raw):
    incident = raw["incident"]
    return {
        "incident": [incident],
        "task_cmdb_ci_service": [
            {"task.number": incident["number"], "cmdb_ci_service": s["sys_id"]}
            for s in reversed(raw["affected_services"])
        ],
        "cmdb_ci_service": raw["affected_services"]
        + [{"sys_id": "b1000000000000000000000000000004", "name": "DORA Reporting Service"}],
    }


def client_for(api):
    return ServiceNowClient("https://example.service-now.com/", "svc_dora_ci", "secret", session=api)


def test_fetch_incident_returns_the_raw_record(raw):
    api = FakeTableApi(tables_from(raw))
    assert client_for(api).fetch_incident("INC0010007") == raw
    assert [table for table, _ in api.requests] == ["incident", "task_cmdb_ci_service", "cmdb_ci_service"]
    assert api.auth == ("svc_dora_ci", "secret")
    assert all(p["sysparm_exclude_reference_link"] == "true" for _, p in api.requests)


def test_unknown_incident_raises_incident_not_found(raw):
    api = FakeTableApi(tables_from(raw))
    with pytest.raises(IncidentNotFound, match="INC0000001"):
        client_for(api).fetch_incident("INC0000001")


@pytest.mark.parametrize("api, expected", [
    (FakeTableApi({}, status_code=401), r"incident: HTTP 401"),
    (FakeTableApi({}, error=requests.Timeout()), r"incident: request failed \(Timeout\)"),
])
def test_http_error_raises_servicenow_error_with_table_and_status(api, expected):
    with pytest.raises(ServiceNowError, match=expected):
        client_for(api).fetch_incident("INC0010007")


def test_missing_environment_raises(monkeypatch):
    monkeypatch.setenv("SERVICENOW_INSTANCE", "https://example.service-now.com")
    monkeypatch.delenv("SERVICENOW_USER", raising=False)
    monkeypatch.delenv("SERVICENOW_PASSWORD", raising=False)
    with pytest.raises(ServiceNowError, match="SERVICENOW_USER, SERVICENOW_PASSWORD"):
        ServiceNowClient.from_env()


class NotJsonResponse:
    status_code = 200

    def json(self):
        raise requests.JSONDecodeError("Expecting value", "<html>Instance hibernating</html>", 0)


def test_non_json_response_raises_servicenow_error():
    api = FakeTableApi({})
    api.get = lambda url, params, timeout: NotJsonResponse()
    with pytest.raises(ServiceNowError, match="incident: response is not Table API JSON"):
        client_for(api).fetch_incident("INC0010007")
