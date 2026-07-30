"""
CLI command: migrate.

Upgrades a CKS JSON file from the legacy format (pre-1.14.2, no
_cks_format_version key) to the current versioned format.

Usage
-----
    cks migrate input.cks.json output.cks.json
    cks migrate input.cks.json --in-place
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...serialization import (
    CanonicalDeserializer,
    CanonicalSerializer,
    FormatVersionError,
    SerializationError,
)


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "migrate",
        help="Upgrade a legacy CKS JSON file to the current versioned format",
    )
    parser.add_argument("input", type=Path, help="Path to the source CKS JSON file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="Destination path (omit when using --in-place)",
    )
    parser.add_argument(
        "--in-place",
        "-i",
        action="store_true",
        help="Overwrite the input file in place",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit 0 if the file is already current, exit 2 if migration "
            "is needed, without writing any output"
        ),
    )
    return parser


def handle(args) -> None:
    path: Path = args.input

    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    deserializer = CanonicalDeserializer()
    is_legacy = deserializer.is_legacy_format(data)

    if args.check:
        if is_legacy:
            print(f"NEEDS MIGRATION: {path} (legacy format, no _cks_format_version)")
            sys.exit(2)
        else:
            fmt = data.get("_cks_format_version", "?")
            print(f"OK: {path} (format version {fmt})")
            sys.exit(0)

    if not is_legacy:
        fmt = data.get("_cks_format_version", "?")
        print(f"Nothing to do: {path} is already at format version {fmt}.")
        sys.exit(0)

    # Determine destination
    if args.in_place:
        dest = path
    elif args.output is not None:
        dest = args.output
    else:
        print(
            "error: specify an output path or pass --in-place",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse (legacy path skips the version check in _validate_root because
    # _cks_min_reader_version is absent) and re-serialize with version metadata.
    try:
        structure = deserializer.deserialize(data)
    except (SerializationError, FormatVersionError) as exc:
        print(f"Serialization error in {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    serializer = CanonicalSerializer()
    output_json = serializer.serialize(structure)

    try:
        dest.write_text(output_json, encoding="utf-8")
    except OSError as exc:
        print(f"Cannot write {dest}: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.in_place:
        print(f"✓ Migrated {path} to format v1.0 (in place)")
    else:
        print(f"✓ Migrated {path} → {dest} (format v1.0)")
