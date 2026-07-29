"""
CLI command: inspect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...serialization import SerializationError
from ...serialization import parse as cks_parse


def add_parser(subparsers):
    parser = subparsers.add_parser("inspect", help="Inspect a Knowledge Structure")
    parser.add_argument("input", type=Path, help="Path to canonical JSON file")
    parser.add_argument("--format", "-f", choices=("text", "json"), default="text")
    parser.add_argument("--output", "-o", type=Path, default=None)
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

    lines = [
        f"Objects: {len(structure.objects)}",
        f"Relations: {len(structure.relations())}",
        "",
    ]
    for obj in structure.objects:
        lines.append(f"  {obj.identity.type}: {obj.identity.id} ({obj.identity.name})")

    if args.format == "json":
        data = {
            "objects": [
                {
                    "id": obj.identity.id,
                    "type": obj.identity.type,
                    "name": obj.identity.name,
                }
                for obj in structure.objects
            ],
            "relations": [
                {
                    "id": r.identity.id,
                    "type": r.relation_type,
                    "participants": list(r.participants),
                }
                for r in structure.relations()
            ],
        }
        formatted = json.dumps(data, indent=2)
    else:
        formatted = "\n".join(lines)

    if args.output is None:
        print(formatted)
    else:
        args.output.write_text(formatted, encoding="utf-8")
