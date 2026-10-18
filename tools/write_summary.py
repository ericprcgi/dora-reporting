"""Write the CI summary tables (Markdown) to stdout.

    python tools/write_summary.py tests out/junit.xml >> "$GITHUB_STEP_SUMMARY"
    python tools/write_summary.py validation out/validation-v1.json out/validation-v2.json

The tests table lists each test with the FI requirement and source from its
fi_source marker ("<source>: <requirement>", see README: Test conventions).
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GROUPS = {
    "affectedEntityType": "Affected entities (1.4–1.6)",
    "affectedEntity-name": "Affected entities (1.4–1.6)",
    "affectedEntity-LEI": "Affected entities (1.4–1.6)",
    "detectionDateTime": "Date and time (2.2–2.3)",
    "classificationDateTime": "Date and time (2.2–2.3)",
    "primaryContact-phone": "Phone numbers (1.9, 1.12)",
    "secondaryContact-phone": "Phone numbers (1.9, 1.12)",
}


def group_of(field: str) -> str:
    return GROUPS.get(field, field)


def _cell(value) -> str:
    return "–" if value in (None, "") else str(value).replace("|", "\\|").replace("\n", " ")


def _breakable(name: str) -> str:
    """Zero-width spaces after "_" and "::" let a long test name wrap in GitHub's narrow summary column."""
    return name.replace("::", "::\u200b").replace("_", "_\u200b")


def _result(case) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "❌ failed"
    if case.find("skipped") is not None:
        return "⏭ skipped"
    return "✅ passed"


def tests_table(junit_xml: Path) -> str:
    """Tests with an fi_source marker are listed; all tests are counted."""
    rows, counts, unlisted = [], {"passed": 0, "failed": 0, "skipped": 0}, 0
    for case in ET.parse(junit_xml).getroot().iter("testcase"):
        result = _result(case)
        counts[result.split()[1]] += 1
        prop = case.find("properties/property[@name='fi_source']")
        if prop is None:
            unlisted += 1
            continue
        source, _, requirement = prop.get("value").partition(": ")
        test = f"{case.get('classname', '').split('.')[-1]}::{case.get('name')}"
        rows.append(f"| {_cell(requirement)} | {_cell(source)} | {_breakable(test)} | {result} |")
    tally = f"{counts['passed']} passed, {counts['failed']} failed"
    if counts["skipped"]:
        tally += f", {counts['skipped']} skipped"
    if unlisted:
        tally += f" ({unlisted} without an FI source not listed)"
    return "\n".join([
        "### FI requirements and tests", "",
        "| FI requirement | Source | Test | Result |", "|---|---|---|---|", *rows, "",
        f"**{sum(counts.values())} tests: {tally}**", "",
    ])


def validation_table(result_json: Path) -> str:
    result = json.loads(result_json.read_text(encoding="utf-8"))
    version, issues = result["schema_version"], result["issues"]
    groups: dict[str, list[dict]] = {}
    for issue in issues:
        groups.setdefault(group_of(issue["field"]), []).append(issue)
    status = "✅ passed" if result["valid"] else (
        f"❌ failed – {len(issues)} errors in {len(groups)} groups")
    lines = [
        f"### validate ({version}): {status}", "",
        f"Incident {result['incident']} · FI schema `{result['schema_file']}` · "
        f"SHA-256 `{result['sha256'][:16]}…` matches `schemas/SHA256SUMS`", "",
    ]
    if not issues:
        return "\n".join(lines)
    lines += ["| Group | Fields | Rule |", "|---|---|---|"]
    for name, members in groups.items():
        fields = ", ".join(dict.fromkeys(i["field"] for i in members))
        rules = ", ".join(dict.fromkeys(i["rule"] for i in members))
        lines.append(f"| {name} | {fields} | {rules} |")
    lines += ["", "| Field | Value | Message |", "|---|---|---|"]
    for issue in issues:
        lines.append(f"| `{issue['path']}` | {_cell(issue['value'])} | {_cell(issue['message'])} |")
    return "\n".join(lines + [""])


def main(argv: list[str] | None = None) -> int:
    kind, *paths = argv if argv is not None else sys.argv[1:]
    render = tests_table if kind == "tests" else validation_table
    for path in map(Path, paths):
        print(render(path) if path.is_file() else f"_No test results: {path} not found_\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
