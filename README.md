# dora-reporting

Generates Swedish Bank AB's DORA major incident reports (Initial report) for
Finansinspektionen (FI) from ServiceNow.

The DORA reporting officer uploads the report in FI's reporting portal Fidac.
This repository never submits anything to FI.

## How it works

ServiceNow → snapshot → mapper → validation → report file

1. `servicenow_client.py` reads the major incident, the legal entities it refers
   to, the affected services and the DORA reporting officer from ServiceNow
   (Table API). ServiceNow stores times in UTC.
2. `mapper_initial.py` builds the Initial report in FI's JSON format. Field
   sources and transformations are documented in Confluence:
   **Data Dictionary – Initial Report**.
3. `validate.py` checks the SHA-256 of FI's schema file and validates the
   report against it, including formats such as dates.
4. `cli.py` ties it together and writes `out/<incident>_initial.json` and
   `out/validation-<schema>.json`.

## Running locally

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest
PYTHONPATH=src python -m dora_reporting.cli generate --incident INC0009817 --source fixture --schema v1
PYTHONPATH=src python -m dora_reporting.cli checksums
```

- `--source fixture` reads a saved snapshot from `tests/fixtures/`.
- `--source servicenow` reads from ServiceNow and needs `SERVICENOW_INSTANCE`,
  `SERVICENOW_USER` and `SERVICENOW_PASSWORD`.
- Exit codes: 0 valid, 1 not valid against the schema, 2 error (for example an
  unknown incident or an incident that is not classified as major).

## CI workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `baseline` | Manual: `incident` (default INC0009817), `source` (default fixture) | Generates the report with the current mapper and validates it against FI's v1 and v2 schemas in two jobs, `validate (v1)` and `validate (v2)`. The summary groups the errors |
| `pr-check` | Every pull request to `main` | Checks FI's files (SHA-256), runs the tests, validates the INC0009817 report against FI's v2 schema and writes the summary tables. Required before merge |
| `generate-report` | Manual: `incident` (required), `source` (default servicenow) | Generates the report for a major incident with the code on `main`, validates it against FI's v2 schema and stores the JSON file as an artifact |

## FI schema files

`schemas/fi/v1` and `schemas/fi/v2` hold FI's JSON schema and mapping files for
the Initial report, unchanged as downloaded from fi.se. `schemas/SHA256SUMS`
holds their checksums, and every validation checks them first. Never edit these
files; add a new version directory instead.

- v1: FI package 2025-03-26 (updated 2025-05-08). The mapper produces v1.
- v2: FI package 2026-09-10. FI: applies in Fidac from 19 October 2026.

## Test conventions

- Tests live in `tests/` and run with `python -m pytest`.
- Every test that verifies an FI requirement is marked with its source:

  ```python
  @pytest.mark.fi_source("v1 schema: detectionDateTime format date-time")
  def test_invalid_calendar_date_is_rejected():
      ...
  ```

- The marker text is `"<source>: <requirement>"`. The source is the document
  the requirement comes from, for example `v1 schema`, `v2 schema`,
  `FI guidance` or `DORA Article 19`.
- `pr-check` builds a table from the markers with the columns FI requirement,
  source, test and result (`tools/write_summary.py`), so every FI requirement
  can be traced to its test.
- Use the shared `snapshot` fixture (INC0009817, see `tests/conftest.py`) and
  change it inside the test rather than adding fixture files.
- One behaviour per test, named after the behaviour.

## Branch naming and change process

Changes follow Confluence: **Change Process – Regulatory Reporting**.

- Every change has a Jira story in the DORA Reporting project, with its source.
- Branch from `main` as `feature/<JIRA-KEY>-short-description`, for example
  `feature/DORA-5-log-fidac-reference-code`.
- Keep the diff minimal. Small files, LF line endings (see `.gitattributes`).
- Open a pull request that references the Jira story. A green `pr-check` and
  reviews by compliance and the technical reviewer (`.github/CODEOWNERS`) are
  required before merge.
- Deployment needs a normal change request in ServiceNow approved by the change
  advisory board, and the data dictionary in Confluence is updated with a
  valid-from date.
