"""Validate reports against FI's published JSON schemas.

FI's schema files are stored unchanged in schemas/fi/ and checked against
schemas/SHA256SUMS before every validation, so a green result always means
"valid against FI's own file".
"""
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
VERSIONS = ("v1", "v2")


class ChecksumError(Exception):
    """An FI schema file does not match schemas/SHA256SUMS."""


@dataclass
class ValidationIssue:
    path: str
    field: str
    rule: str
    message: str
    value: str | None = None


def schema_path(version: str) -> Path:
    if version not in VERSIONS:
        raise ValueError(f"unknown schema version: {version}")
    return SCHEMA_DIR / "fi" / version / "dora_initial_schema.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksums() -> dict[str, str]:
    """Return {relative path: sha256} for all FI files, or raise ChecksumError."""
    result = {}
    for line in (SCHEMA_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        actual = _sha256(SCHEMA_DIR / name)
        if actual != expected:
            raise ChecksumError(f"{name}: SHA-256 {actual} does not match SHA256SUMS ({expected})")
        result[name] = actual
    return result


def load_schema(version: str) -> dict:
    verify_checksums()
    return json.loads(schema_path(version).read_text(encoding="utf-8"))


def _join(*parts) -> str:
    return ".".join(str(p) for p in parts if p != "")


def _issues_from(error) -> list[ValidationIssue]:
    parent = _join(*error.absolute_path)
    if error.validator == "additionalProperties":
        allowed = set(error.schema.get("properties", {}))
        return [
            ValidationIssue(_join(parent, name), name, "additionalProperties",
                            f"'{name}' is not allowed here (additionalProperties is false)")
            for name in sorted(set(error.instance) - allowed)
        ]
    if error.validator == "required":
        name = re.match(r"'(.+)' is a required property", error.message).group(1)
        return [ValidationIssue(_join(parent, name), name, "required", error.message)]
    field = next((p for p in reversed(error.absolute_path) if isinstance(p, str)), parent)
    value = error.instance if isinstance(error.instance, (str, int, float, bool)) else None
    return [ValidationIssue(parent, field, error.validator, error.message,
                            None if value is None else str(value))]


def validate_report(report: dict, version: str) -> list[ValidationIssue]:
    """Validate against FI's schema with format checking (dates, URIs)."""
    validator = Draft7Validator(load_schema(version), format_checker=FormatChecker())
    issues = []
    for error in sorted(validator.iter_errors(report), key=lambda e: list(map(str, e.absolute_path))):
        issues.extend(_issues_from(error))
    return issues
