"""Unit tests for the VerificationRecordIntegrityConstraint extension."""

import pytest

from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS_BY_NAME
from cks.constraints.registry import ConstraintRegistry
from cks.constraints.verification import (
    VERIFICATION_RECORD_TYPE,
    VERIFIED_BY_RELATION,
)
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.validator import ReferenceValidator
from cks.validator import validate as default_validate


def make_object(oid: str, otype: str = "Definition", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=oid),
        structure=structure or {},
    )


def make_relation(oid: str, participants: list[str], relation_type: str) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def verification_validator() -> ReferenceValidator:
    registry = ConstraintRegistry()
    for c in (*BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS_BY_NAME["verification_record"]):
        registry.register(c)
    return ReferenceValidator(registry=registry)


def test_not_registered_by_default():
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["verification_record"]
    assert constraint.identity not in [c.identity for c in BUILTIN_CONSTRAINTS]


def test_default_validate_ignores_malformed_verification_record():
    bad = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={})
    structure = KnowledgeStructure([bad])
    result = default_validate(structure)
    assert result.is_valid is True


def test_valid_verification_record_passes():
    subject = make_object("doc-1", "Document")
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "automated_http_check",
        "http_status": 200,
    })
    link = make_relation("rel-1", ["doc-1", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([subject, record, link])
    result = verification_validator().validate(structure)
    assert result.is_valid is True


def test_missing_verified_by_relation_is_rejected():
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "manual_review",
    })
    structure = KnowledgeStructure([record])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("exactly one" in d.message for d in result.diagnostics)


def test_missing_subject_is_rejected():
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "automated_http_check",
    })
    link = make_relation("rel-1", ["ghost", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([record, link])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("unknown subject object" in d.message for d in result.diagnostics)


def test_bad_timestamp_is_rejected():
    subject = make_object("doc-1", "Document")
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "not-a-timestamp",
        "checked_via": "automated_http_check",
    })
    link = make_relation("rel-1", ["doc-1", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([subject, record, link])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("checked_at" in d.message for d in result.diagnostics)


def test_invalid_checked_via_is_rejected():
    subject = make_object("doc-1", "Document")
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "magic",
    })
    link = make_relation("rel-1", ["doc-1", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([subject, record, link])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("checked_via" in d.message for d in result.diagnostics)


@pytest.mark.parametrize("bad_status", ["200", True, 99, 600])
def test_invalid_http_status_is_rejected(bad_status):
    subject = make_object("doc-1", "Document")
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "automated_http_check",
        "http_status": bad_status,
    })
    link = make_relation("rel-1", ["doc-1", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([subject, record, link])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("http_status" in d.message for d in result.diagnostics)


def test_qualitative_fields_are_rejected():
    subject = make_object("doc-1", "Document")
    record = make_object("vr-1", VERIFICATION_RECORD_TYPE, structure={
        "checked_at": "2026-07-19T12:00:00Z",
        "checked_via": "manual_review",
        "reliability_score": 95,
        "confidence": "high",
    })
    link = make_relation("rel-1", ["doc-1", "vr-1"], VERIFIED_BY_RELATION)
    structure = KnowledgeStructure([subject, record, link])
    result = verification_validator().validate(structure)
    assert not result.is_valid
    assert any("qualitative judgment fields" in d.message for d in result.diagnostics)