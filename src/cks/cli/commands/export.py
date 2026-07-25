"""
CLI command: export.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...serialization import parse as cks_parse, SerializationError


def add_parser(subparsers):
    parser = subparsers.add_parser("export", help="Export CKS to another format")
    parser.add_argument("input", type=Path, help="Path to CKS JSON file")
    parser.add_argument(
        "--format",
        "-f",
        choices=("json-ld", "turtle", "rdf-xml"),
        default="json-ld",
        help="Output format (default: json-ld)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write output to file instead of stdout",
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

    if args.format == "json-ld":
        from ...adapters.cks_to_jsonld import CksToJsonLdConverter

        converter = CksToJsonLdConverter(structure)
        output_data = converter.convert()
        formatted = json.dumps(output_data, indent=2)
    elif args.format == "turtle":
        from ...adapters.cks_to_rdf import CksToRdfConverter

        converter = CksToRdfConverter(structure)
        formatted = converter.to_turtle()
    elif args.format == "rdf-xml":
        from ...adapters.cks_to_rdf import CksToRdfConverter

        converter = CksToRdfConverter(structure)
        formatted = converter.to_rdfxml()
    else:
        print(f"Unknown export format: {args.format}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        print(formatted)
    else:
        args.output.write_text(formatted, encoding="utf-8")
