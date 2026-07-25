"""
CLI command: plugin.
"""

from __future__ import annotations


def add_parser(subparsers):
    parser = subparsers.add_parser("plugin", help="Manage plugins")
    sub = parser.add_subparsers(dest="plugin_command", required=True)
    _ = sub.add_parser("list", help="List loaded constraints")
    return parser


def handle(args):
    from ...constraints import registry

    constraints = registry.constraints()
    if not constraints:
        print("No constraints registered.")
        return
    for c in constraints:
        print(f"  {c.identity} — {c.description or '(no description)'}")
