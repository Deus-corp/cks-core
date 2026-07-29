"""
CLI command: evolve.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...evolution import compose, parse_operations
from ...serialization import (
    SerializationError,
)
from ...serialization import (
    parse as cks_parse,
)
from ...serialization import (
    serialize as cks_serialize,
)


def add_parser(subparsers):
    parser = subparsers.add_parser("evolve", help="Apply structural evolution")
    parser.add_argument("input", type=Path, help="Path to canonical JSON file")
    parser.add_argument("operations", type=Path, help="JSON file describing operations")
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Write result to file"
    )
    return parser


def handle(args):
    try:
        raw = args.input.read_text(encoding="utf-8")
        structure = cks_parse(raw)
    except FileNotFoundError:
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except SerializationError as exc:
        print(f"Serialization error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        ops_data = json.loads(args.operations.read_text(encoding="utf-8"))
        operators = parse_operations(ops_data)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in operations file: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Invalid operations: {exc}", file=sys.stderr)
        sys.exit(1)

    new_structure = compose(structure, operators)
    result = cks_serialize(new_structure)

    if args.output is None:
        print(result)
    else:
        args.output.write_text(result, encoding="utf-8")