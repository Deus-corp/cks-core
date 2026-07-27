"""
CLI command: validate.
"""

from __future__ import annotations

import html as html_lib
import json
import sys
from pathlib import Path
from typing import Optional

from ...serialization import parse as cks_parse, SerializationError
from ...validator import validate as cks_validate, validate_all
from ...diagnostics import DiagnosticSeverity
from ..formatters import format_json, format_text, format_html, format_markdown


def add_parser(subparsers):
    parser = subparsers.add_parser("validate", help="Validate a Knowledge Structure")
    parser.add_argument(
        "input", type=Path, nargs="+", help="Path(s) to canonical JSON file(s)"
    )
    parser.add_argument(
        "--format", "-f", choices=("text", "json", "html", "markdown"), default="text"
    )
    parser.add_argument("--output", "-o", type=Path, default=None)
    parser.add_argument(
        "--min-severity",
        choices=("error", "warning", "information"),
        default="error",
        help="Minimum severity to consider a structure invalid",
    )
    return parser


def handle(args):
    severity_map = {
        "error": DiagnosticSeverity.ERROR,
        "warning": DiagnosticSeverity.WARNING,
        "information": DiagnosticSeverity.INFORMATION,
    }
    min_severity = severity_map[args.min_severity]

    formatter_map = {
        "json": format_json,
        "text": format_text,
        "html": format_html,
        "markdown": format_markdown,
    }
    formatter = formatter_map[args.format]

    structures = []
    for path in args.input:
        try:
            raw = path.read_text(encoding="utf-8")
            structures.append(cks_parse(raw))
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        except SerializationError as exc:
            print(f"Serialization error in {path}: {exc}", file=sys.stderr)
            sys.exit(1)

    if len(structures) == 1:
        result = cks_validate(structures[0], min_severity=min_severity)
        output = formatter(result)
        _write_output(output, args.output)
        sys.exit(0 if result.is_valid else 1)
    else:
        results = validate_all(structures, min_severity=min_severity)
        valid_count = sum(1 for r in results if r.is_valid)
        output = _format_multi(args.format, args.input, results)
        _write_output(output, args.output)
        sys.exit(0 if valid_count == len(results) else 1)


def _format_multi(fmt: str, paths: list[Path], results: list) -> str:
    """Render a multi-file validation report in the requested --format.

    Mirrors the single-file formatters in ``formatters.py`` but adds a
    per-file breakdown plus an overall summary, so --format and
    --output are honoured for multi-file runs the same way they are
    for a single file.
    """
    total = len(results)
    valid_count = sum(1 for r in results if r.is_valid)

    if fmt == "json":
        data = {
            "total": total,
            "valid": valid_count,
            "invalid": total - valid_count,
            "files": [
                {
                    "path": str(path),
                    "valid": result.is_valid,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "information_count": result.information_count,
                    "constraints_evaluated": list(result.evaluated_constraints),
                    "diagnostics": [
                        {
                            "identity": d.identity,
                            "severity": d.severity.value,
                            "message": d.message,
                            "location": d.location,
                        }
                        for d in result.diagnostics
                    ],
                }
                for path, result in zip(paths, results)
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    if fmt == "html":
        sections = "".join(
            f"<h2>{html_lib.escape(str(path))}</h2>\n{format_html(result)}"
            for path, result in zip(paths, results)
        )
        return (
            "<!DOCTYPE html>\n<html>\n"
            "<head><meta charset='utf-8'><title>CKS Validation Report</title></head>\n"
            "<body>\n"
            f"<h1>Files validated: {total} — Valid: {valid_count} — "
            f"Invalid: {total - valid_count}</h1>\n"
            f"{sections}\n"
            "</body>\n</html>"
        )

    if fmt == "markdown":
        sections = "\n\n".join(
            f"## {path}\n\n{format_markdown(result)}"
            for path, result in zip(paths, results)
        )
        header = (
            f"# Validation Report\n\n"
            f"Files validated: {total}  Valid: {valid_count}  "
            f"Invalid: {total - valid_count}\n\n"
        )
        return header + sections

    # "text" (default)
    lines = [
        f"Files validated: {total}",
        f"Valid: {valid_count}",
        f"Invalid: {total - valid_count}",
        "",
    ]
    for path, result in zip(paths, results):
        status = "✅ Valid" if result.is_valid else "❌ Invalid"
        lines.append(f"{path}: {status}")
    return "\n".join(lines)


def _write_output(content: str, path: Optional[Path]) -> None:
    if path is None:
        print(content)
    else:
        path.write_text(content, encoding="utf-8")