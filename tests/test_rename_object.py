"""
Unit tests for RenameObject operator and public operator properties.
"""

from __future__ import annotations

import pytest

from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.evolution import (
    AddObject,
    AddRelation,
    RemoveObject,
    RemoveRelation,
    RenameObject,
    UpdateObject,
    compose,
    parse_operations,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obj(oid: str, otype: str = "Concept", name: str = "") -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid)
    )


def _make_rel(
    oid: str,
    participants: list[str],
    relation_type: str = "related_to",
    name: str = "",
) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=name or oid),
        participants=participants,
        relation_type=relation_type,
    )


def _make_structure() -> KnowledgeStructure:
    return KnowledgeStructure(
        [
            _make_obj("obj-1", name="Alpha"),
            _make_obj("obj-2", name="Beta"),
            _make_rel("rel-1", ["obj-1", "obj-2"]),
        ]
    )


# ===========================================================================
# Public properties — all operators
# ===========================================================================


class TestPublicProperties:
    def test_add_object_obj_property(self):
        obj = _make_obj("x")
        op = AddObject(obj)
        assert op.obj is obj

    def test_add_relation_relation_property(self):
        rel = _make_rel("r", ["a", "b"])
        op = AddRelation(rel)
        assert op.relation is rel

    def test_remove_object_object_id_property(self):
        op = RemoveObject("my-id")
        assert op.object_id == "my-id"

    def test_remove_relation_relation_id_property(self):
        op = RemoveRelation("rel-42")
        assert op.relation_id == "rel-42"

    def test_update_object_properties(self):
        op = UpdateObject("obj-x", {"k": "v"}, mode="replace")
        assert op.object_id == "obj-x"
        assert op.structure_patch == {"k": "v"}
        assert op.mode == "replace"

    def test_update_object_structure_patch_is_copy(self):
        patch = {"k": "v"}
        op = UpdateObject("obj-x", patch)
        op.structure_patch["extra"] = 99
        # The returned dict should be a copy — mutating it must not affect op
        assert "extra" not in op.structure_patch

    def test_rename_object_properties(self):
        op = RenameObject("obj-1", "Gamma")
        assert op.object_id == "obj-1"
        assert op.new_name == "Gamma"


# ===========================================================================
# RenameObject — basic behaviour
# ===========================================================================


class TestRenameObject:
    def test_rename_plain_object(self):
        structure = _make_structure()
        op = RenameObject("obj-1", "Gamma")
        result = op.apply(structure)

        renamed = result.get("obj-1")
        assert renamed is not None
        assert renamed.identity.name == "Gamma"

    def test_rename_preserves_id_and_type(self):
        structure = _make_structure()
        original = structure.get("obj-1")
        op = RenameObject("obj-1", "NewName")
        result = op.apply(structure)

        updated = result.get("obj-1")
        assert updated.identity.id == original.identity.id
        assert updated.identity.type == original.identity.type

    def test_rename_preserves_structure_dict(self):
        ks = KnowledgeStructure(
            [
                KnowledgeObject(
                    identity=ObjectIdentity(id="obj-1", type="X", name="Old"),
                    structure={"content": "hello", "score": 42},
                )
            ]
        )
        result = RenameObject("obj-1", "New").apply(ks)
        assert result.get("obj-1").structure["content"] == "hello"
        assert result.get("obj-1").structure["score"] == 42

    def test_rename_does_not_cascade_relations(self):
        structure = _make_structure()
        op = RenameObject("obj-1", "Gamma")
        result = op.apply(structure)

        # rel-1 links obj-1 and obj-2; it must survive unmodified
        rel = result.get("rel-1")
        assert rel is not None
        assert isinstance(rel, CanonicalRelation)
        assert "obj-1" in rel.participants

    def test_rename_total_object_count_unchanged(self):
        structure = _make_structure()
        result = RenameObject("obj-1", "Z").apply(structure)
        assert len(result.objects) == len(structure.objects)

    def test_rename_relation_object(self):
        """RenameObject should also rename CanonicalRelation nodes."""
        structure = _make_structure()
        op = RenameObject("rel-1", "MyRenamedRelation")
        result = op.apply(structure)

        renamed_rel = result.get("rel-1")
        assert renamed_rel is not None
        assert renamed_rel.identity.name == "MyRenamedRelation"
        assert isinstance(renamed_rel, CanonicalRelation)
        # Semantic fields must be preserved
        assert renamed_rel.relation_type == "related_to"
        assert set(renamed_rel.participants) == {"obj-1", "obj-2"}

    def test_rename_nonexistent_object_raises(self):
        structure = _make_structure()
        op = RenameObject("ghost", "Whatever")
        with pytest.raises(ValueError, match="does not exist"):
            op.apply(structure)

    def test_rename_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            RenameObject("obj-1", "")

    def test_rename_whitespace_only_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            RenameObject("obj-1", "   ")

    def test_contract_mentions_object_id_and_new_name(self):
        op = RenameObject("obj-1", "Gamma")
        c = op.contract()
        assert "obj-1" in c.description
        assert "Gamma" in c.description

    def test_rename_is_callable(self):
        structure = _make_structure()
        op = RenameObject("obj-2", "Delta")
        result = op(structure)
        assert result.get("obj-2").identity.name == "Delta"

    def test_root_hash_changes_after_rename(self):
        structure = _make_structure()
        result = RenameObject("obj-1", "NewName").apply(structure)
        assert result.root_hash != structure.root_hash

    # -------------------------------------------------------------------
    # compose integration
    # -------------------------------------------------------------------

    def test_rename_in_compose_batch(self):
        structure = _make_structure()
        ops = [
            RenameObject("obj-1", "Alpha-Renamed"),
            RenameObject("obj-2", "Beta-Renamed"),
        ]
        result = compose(structure, ops)
        assert result.get("obj-1").identity.name == "Alpha-Renamed"
        assert result.get("obj-2").identity.name == "Beta-Renamed"
        # Relations must be intact
        assert result.get("rel-1") is not None

    def test_rename_then_update_in_compose(self):
        structure = _make_structure()
        ops = [
            RenameObject("obj-1", "Alpha-v2"),
            UpdateObject("obj-1", {"note": "added"}),
        ]
        result = compose(structure, ops)
        obj = result.get("obj-1")
        assert obj.identity.name == "Alpha-v2"
        assert obj.structure.get("note") == "added"


# ===========================================================================
# parse_operations — rename_object wire format
# ===========================================================================


class TestParseRenameObject:
    def test_parse_rename_object(self):
        ops = parse_operations(
            [{"type": "rename_object", "object_id": "obj-1", "new_name": "New"}]
        )
        assert len(ops) == 1
        assert isinstance(ops[0], RenameObject)
        assert ops[0].object_id == "obj-1"
        assert ops[0].new_name == "New"

    def test_parse_missing_object_id_raises(self):
        with pytest.raises(ValueError, match="missing 'object_id'"):
            parse_operations([{"type": "rename_object", "new_name": "X"}])

    def test_parse_missing_new_name_raises(self):
        with pytest.raises(ValueError, match="missing 'new_name'"):
            parse_operations([{"type": "rename_object", "object_id": "obj-1"}])

    def test_parse_empty_new_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            parse_operations(
                [{"type": "rename_object", "object_id": "obj-1", "new_name": ""}]
            )

    def test_parse_rename_then_apply(self):
        structure = _make_structure()
        ops = parse_operations(
            [{"type": "rename_object", "object_id": "obj-2", "new_name": "Zeta"}]
        )
        result = compose(structure, ops)
        assert result.get("obj-2").identity.name == "Zeta"

    def test_parse_mixed_operations_including_rename(self):
        structure = _make_structure()
        ops = parse_operations(
            [
                {
                    "type": "add_object",
                    "identity": {"id": "obj-3", "type": "Concept", "name": "Gamma"},
                    "structure": {},
                },
                {
                    "type": "rename_object",
                    "object_id": "obj-1",
                    "new_name": "Alpha-Renamed",
                },
            ]
        )
        result = compose(structure, ops)
        assert result.get("obj-3") is not None
        assert result.get("obj-1").identity.name == "Alpha-Renamed"
