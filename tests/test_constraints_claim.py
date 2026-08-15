"""Unit tests for the ClaimIntegrityConstraint extension."""

from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS_BY_NAME
from cks.constraints.claim import CLAIM_TYPE
from cks.constraints.registry import ConstraintRegistry
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.validator import ReferenceValidator
from cks.validator import validate as default_validate


def make_object(oid: str, otype: str = "Claim", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=oid),
        structure=structure or {},
    )


def make_claim(oid: str, **overrides) -> KnowledgeObject:
    data = {
        "statement": "The Earth orbits the Sun.",
        "confidence": 0.97,
        "author": "researcher-agent",
        "created_at": "2026-08-15T00:00:00Z",
        "status": "accepted",
    }
    data.update(overrides)
    return make_object(oid, CLAIM_TYPE, data)


def claim_validator() -> ReferenceValidator:
    registry = ConstraintRegistry()
    for c in (*BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS_BY_NAME["claim_integrity"]):
        registry.register(c)
    return ReferenceValidator(registry=registry)


def test_not_registered_by_default():
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["claim_integrity"]
    assert constraint.identity not in [c.identity for c in BUILTIN_CONSTRAINTS]


def test_constraint_not_run_unless_explicitly_enabled():
    bad = make_claim("c1", statement="")
    structure = KnowledgeStructure([bad])
    result = default_validate(structure)
    assert result.is_valid is True


def test_valid_claim_passes():
    claim = make_claim("c1")
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert result.is_valid is True


def test_non_claim_objects_unaffected():
    obj = make_object("d1", "Definition", {"anything": "goes"})
    structure = KnowledgeStructure([obj])
    result = claim_validator().validate(structure)
    assert result.is_valid is True


def test_missing_statement_is_flagged():
    claim = make_claim("c1", statement="")
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("statement" in d.message for d in result.diagnostics)


def test_confidence_out_of_bounds_is_flagged():
    claim = make_claim("c1", confidence=1.2)
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("confidence" in d.message for d in result.diagnostics)


def test_invalid_status_is_flagged():
    claim = make_claim("c1", status="not-a-status")
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("status" in d.message for d in result.diagnostics)


def test_malformed_iso_timestamp_is_flagged():
    claim = make_claim("c1", created_at="not-a-date")
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("created_at" in d.message for d in result.diagnostics)


def test_dangling_provenance_id_is_flagged():
    claim = make_claim("c1", provenance_ids=["missing-1"])
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("provenance_ids" in d.message for d in result.diagnostics)


def test_supporting_claim_pointing_at_non_claim_is_flagged():
    other = make_object("d1", "Definition")
    claim = make_claim("c1", supporting_claims=["d1"])
    structure = KnowledgeStructure([other, claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("supporting_claims" in d.message for d in result.diagnostics)


def test_self_support_is_flagged():
    claim = make_claim("c1", supporting_claims=["c1"])
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("itself" in d.message for d in result.diagnostics)


def test_self_contradiction_is_flagged():
    claim = make_claim("c1", contradicting_claims=["c1"])
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("itself" in d.message for d in result.diagnostics)


def test_same_id_in_supporting_and_contradicting_is_flagged():
    c2 = make_claim("c2")
    claim = make_claim("c1", supporting_claims=["c2"], contradicting_claims=["c2"])
    structure = KnowledgeStructure([c2, claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("both" in d.message for d in result.diagnostics)


def test_valid_supporting_and_contradicting_claims_pass():
    c2 = make_claim("c2")
    c3 = make_claim("c3")
    claim = make_claim("c1", supporting_claims=["c2"], contradicting_claims=["c3"])
    structure = KnowledgeStructure([c2, c3, claim])
    result = claim_validator().validate(structure)
    assert result.is_valid is True


def test_malformed_id_list_type_is_flagged():
    claim = make_claim("c1", provenance_ids="not-a-list")
    structure = KnowledgeStructure([claim])
    result = claim_validator().validate(structure)
    assert not result.is_valid
    assert any("provenance_ids" in d.message for d in result.diagnostics)
