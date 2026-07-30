"""
CKS Command-Line Interface.

Canonical entry point for interacting with CKS from the terminal.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .commands import (
    convert,
    evolve,
    export,
    inspect,
    migrate,
    parse,
    plugin,
    schema,
    validate,
)


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cks",
        description="Canonical Knowledge Structure — CLI",
    )

    parser.add_argument(
        "--strict", action="store_true", help="Fail on any plugin loading error"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    validate.add_parser(sub)
    parse.add_parser(sub)
    inspect.add_parser(sub)
    evolve.add_parser(sub)
    convert.add_parser(sub)
    export.add_parser(sub)
    schema.add_parser(sub)
    plugin.add_parser(sub)
    migrate.add_parser(sub)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _create_parser()
    args = parser.parse_args(argv)

    from cks.plugin import load_external_constraints

    load_external_constraints(strict=args.strict)

    if args.command == "validate":
        validate.handle(args)
    elif args.command == "parse":
        parse.handle(args)
    elif args.command == "inspect":
        inspect.handle(args)
    elif args.command == "evolve":
        evolve.handle(args)
    elif args.command == "convert":
        convert.handle(args)
    elif args.command == "export":
        export.handle(args)
    elif args.command == "schema":
        schema.handle(args)
    elif args.command == "plugin":
        plugin.handle(args)
    elif args.command == "migrate":
        migrate.handle(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
