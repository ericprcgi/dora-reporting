"""Command line used locally and by the CI workflows.

    python -m dora_reporting.cli generate --incident INC0010007 --source fixture --schema v1
    python -m dora_reporting.cli checksums
"""
import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from dora_reporting.mapper_initial import ReportError, build_initial_report
from dora_reporting.servicenow_client import ServiceNowError
from dora_reporting.sources import SOURCES, SourceError, load_snapshot
from dora_reporting.validate import VERSIONS, ChecksumError, validate_report, verify_checksums

INCIDENT_NUMBER = re.compile(r"INC\d{7}")


def _incident(value: str) -> str:
    if not INCIDENT_NUMBER.fullmatch(value):
        raise argparse.ArgumentTypeError(f"invalid incident number: {value!r} (expected INC + 7 digits)")
    return value


def _write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate(report: dict, args) -> int:
    issues = validate_report(report, args.schema)
    name = f"fi/{args.schema}/dora_initial_schema.json"
    _write_json(Path(args.out) / f"validation-{args.schema}.json", {
        "incident": args.incident,
        "schema_version": args.schema,
        "schema_file": f"schemas/{name}",
        "sha256": verify_checksums()[name],
        "valid": not issues,
        "issues": [asdict(issue) for issue in issues],
    })
    if not issues:
        print(f"validate ({args.schema}): passed")
        return 0
    print(f"validate ({args.schema}): failed - {len(issues)} errors")
    for issue in issues:
        print(f"  {issue.path}: {issue.rule}: {issue.message}")
    return 1


def _generate(args) -> int:
    try:
        report = build_initial_report(load_snapshot(args.incident, args.source))
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        _write_json(out / f"{args.incident}_initial.json", report)
        print(f"report: {out / f'{args.incident}_initial.json'}")
        return _validate(report, args) if args.schema else 0
    except (SourceError, ServiceNowError, ReportError, ChecksumError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _checksums(args) -> int:
    try:
        sums = verify_checksums()
    except ChecksumError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for name, digest in sums.items():
        print(f"OK  {digest}  schemas/{name}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dora_reporting.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="generate the Initial report for an incident")
    generate.add_argument("--incident", required=True, type=_incident)
    generate.add_argument("--source", choices=SOURCES, default="fixture")
    generate.add_argument("--schema", choices=VERSIONS, help="validate against FI's schema")
    generate.add_argument("--out", default="out")
    generate.set_defaults(run=_generate)
    checksums = commands.add_parser("checksums", help="verify FI's schema files")
    checksums.set_defaults(run=_checksums)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
