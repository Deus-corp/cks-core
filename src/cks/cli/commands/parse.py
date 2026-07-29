"""
CLI command: parse.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ...serialization import SerializationError
from ...serialization import parse as cks_parse


def add_parser(subparsers):
    parser = subparsers.add_parser("parse", help="Parse a canonical JSON file")
    parser.add_argument("input", type=Path, help="Path to canonical JSON file")
    return parser


def handle(args):
    try:
        raw = args.input.read_text(encoding="utf-8")
        structure = cks_parse(raw)
        print(f"Objects: {len(structure.objects)}")
        print(f"Relations: {len(structure.relations())}")
    except FileNotFoundError:
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except SerializationError as exc:
        print(f"Serialization error: {exc}", file=sys.stderr)
        sys.exit(1)
