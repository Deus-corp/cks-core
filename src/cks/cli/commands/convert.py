"""
CLI command: convert.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...serialization import serialize as cks_serialize


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "convert", help="Convert JSON‑LD, Turtle, or RDF/XML to CKS"
    )
    parser.add_argument("input", type=Path, help="Path to input file")
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Write CKS JSON to file"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("json-ld", "rdf-xml", "turtle"),
        default="json-ld",
        help="Input format (default: json-ld)",
    )
    return parser


def handle(args):
    try:
        raw = args.input.read_text(encoding="utf-8")
        data = json.loads(raw) if args.format == "json-ld" else raw
    except FileNotFoundError:
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {args.input}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.format == "json-ld":
            from ...adapters.jsonld_to_cks import JsonLdToCksConverter

            converter = JsonLdToCksConverter(data)
            structure = converter.convert()
        elif args.format in ("rdf-xml", "turtle"):
            from ...adapters.rdf_to_cks import RdfToCksConverter

            rdf_format = "xml" if args.format == "rdf-xml" else args.format
            converter = RdfToCksConverter(data, format=rdf_format)
            structure = converter.convert()
        else:
            print(f"Unknown format: {args.format}", file=sys.stderr)
            sys.exit(1)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        # Malformed source input (bad Turtle/RDF-XML syntax, a JSON-LD
        # document shaped unlike what the converter expects, duplicate
        # identities, etc.) surfaces here as one of these exception
        # types depending on which converter/stdlib call detected it.
        # Reported as a clean CLI error instead of a raw traceback,
        # matching how `validate`/`evolve`/`migrate` already handle
        # malformed input.
        print(f"Conversion error: {exc}", file=sys.stderr)
        sys.exit(1)

    output = cks_serialize(structure)
    if args.output is None:
        print(output)
    else:
        args.output.write_text(output, encoding="utf-8")