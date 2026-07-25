"""
CLI command: validate.
"""

from __future__ import annotations

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
        total = len(results)
        valid_count = sum(1 for r in results if r.is_valid)
        print(f"Files validated: {total}")
        print(f"Valid: {valid_count}")
        print(f"Invalid: {total - valid_count}")
        print()
        for path, result in zip(args.input, results):
            status = "✅ Valid" if result.is_valid else "❌ Invalid"
            print(f"{path}: {status}")
        sys.exit(0 if valid_count == total else 1)


def _write_output(content: str, path: Optional[Path]) -> None:
    if path is None:
        print(content)
    else:
        path.write_text(content, encoding="utf-8")
