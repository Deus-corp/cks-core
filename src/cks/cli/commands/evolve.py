"""
CLI command: evolve.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ...serialization import (
    parse as cks_parse,
    serialize as cks_serialize,
    SerializationError,
)
from ...evolution import compose, AddObject, AddRelation, RemoveObject, RemoveRelation
from ...core import KnowledgeObject, CanonicalRelation, ObjectIdentity
from ...evolution import StructuralOperator


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
        operators = _parse_operations(ops_data)
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


def _parse_operations(ops_data: list[dict]) -> list:
    operators: list[StructuralOperator] = []
    for i, op in enumerate(ops_data):
        op_type = op.get("type")
        if op_type is None:
            raise ValueError(f"Operation #{i}: missing 'type' field")
        if op_type == "add_object":
            identity_data = op.get("identity")
            if identity_data is None:
                raise ValueError(f"Operation #{i}: missing 'identity' field")
            identity = ObjectIdentity(**identity_data)
            obj = KnowledgeObject(identity=identity, structure=op.get("structure", {}))
            operators.append(AddObject(obj))
        elif op_type == "add_relation":
            identity_data = op.get("identity")
            if identity_data is None:
                raise ValueError(f"Operation #{i}: missing 'identity' field")
            identity = ObjectIdentity(**identity_data)
            participants = op.get("participants")
            if participants is None:
                raise ValueError(f"Operation #{i}: missing 'participants' field")
            relation_type = op.get("relation_type")
            if relation_type is None:
                raise ValueError(f"Operation #{i}: missing 'relation_type' field")
            relation = CanonicalRelation(
                identity=identity,
                participants=participants,
                relation_type=relation_type,
                structure=op.get("structure", {}),
            )
            operators.append(AddRelation(relation))
        elif op_type == "remove_object":
            object_id = op.get("object_id")
            if object_id is None:
                raise ValueError(f"Operation #{i}: missing 'object_id' field")
            operators.append(RemoveObject(object_id))
        elif op_type == "remove_relation":
            relation_id = op.get("relation_id")
            if relation_id is None:
                raise ValueError(f"Operation #{i}: missing 'relation_id' field")
            operators.append(RemoveRelation(relation_id))
        else:
            raise ValueError(f"Operation #{i}: unknown operation type '{op_type}'")
    return operators
