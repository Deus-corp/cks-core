"""
CLI command: schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def add_parser(subparsers):
    parser = subparsers.add_parser("schema", help="Schema-related utilities")
    sub = parser.add_subparsers(dest="schema_command", required=True)
    validate_parser = sub.add_parser(
        "validate", help="Validate a JSON document against the canonical schema"
    )
    validate_parser.add_argument("input", type=Path, help="Path to JSON file")
    return parser


def handle(args):
    try:
        raw = args.input.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError:
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    from ...schema import validate_json, SchemaValidationError

    try:
        validate_json(data)
        print("✅ Schema valid")
    except SchemaValidationError as exc:
        print(f"❌ Schema invalid: {exc}")
        sys.exit(1)
