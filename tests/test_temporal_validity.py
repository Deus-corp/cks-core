"""
Tests for the optional TemporalValidityConstraint.

See ADR-003 ("Temporal Validity Constraint").
"""

from datetime import UTC, datetime, timedelta

from cks.constraints.temporal import TemporalValidityConstraint
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.diagnostics import DiagnosticSeverity
from cks.validator import validate


def make_object(oid: str, otype: str = "Claim", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=oid),
        structure=structure or {},
    )


PAST = (datetime.now(UTC) - timedelta(days=1)).isoformat()
FUTURE = (datetime.now(UTC) + timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# TemporalValidityConstraint.evaluate()
# ---------------------------------------------------------------------------


def test_passes_when_valid_until_absent():
    structure = KnowledgeStructure([make_object("a")])
    assert TemporalValidityConstraint().evaluate(structure) == []


def test_flags_expired_valid_until_with_warning():
    structure = KnowledgeStructure([make_object("a", structure={"valid_until": PAST})])
    diagnostics = TemporalValidityConstraint().evaluate(structure)

    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-TEMPORAL-VALIDITY"
    assert diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert diagnostics[0].location == "a"


def test_flags_malformed_valid_until_with_error():
    structure = KnowledgeStructure([make_object("a", structure={"valid_until": "not-a-date"})])
    diagnostics = TemporalValidityConstraint().evaluate(structure)

    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-TEMPORAL-VALIDITY"
    assert diagnostics[0].severity == DiagnosticSeverity.ERROR
    assert diagnostics[0].location == "a"


def test_passes_when_valid_until_in_future():
    structure = KnowledgeStructure([make_object("a", structure={"valid_until": FUTURE})])
    assert TemporalValidityConstraint().evaluate(structure) == []


def test_passes_when_valid_until_is_naive_future_datetime():
    naive_future = (datetime.now() + timedelta(days=1)).isoformat()  # noqa: DTZ005 (intentionally naive)
    structure = KnowledgeStructure([make_object("a", structure={"valid_until": naive_future})])
    assert TemporalValidityConstraint().evaluate(structure) == []


def test_evaluates_multiple_objects_independently():
    structure = KnowledgeStructure([
        make_object("expired", structure={"valid_until": PAST}),
        make_object("still-valid", structure={"valid_until": FUTURE}),
        make_object("no-window"),
        make_object("malformed", structure={"valid_until": 12345}),
    ])
    diagnostics = TemporalValidityConstraint().evaluate(structure)

    by_location = {d.location: d for d in diagnostics}
    assert set(by_location) == {"expired", "malformed"}
    assert by_location["expired"].severity == DiagnosticSeverity.WARNING
    assert by_location["malformed"].severity == DiagnosticSeverity.ERROR


# ---------------------------------------------------------------------------
# Opt-in through validate() / OPTIONAL_CONSTRAINTS_BY_NAME
# ---------------------------------------------------------------------------


def test_not_applied_by_default():
    structure = KnowledgeStructure([make_object("a", structure={"valid_until": PAST})])
    result = validate(structure)
    assert result.is_valid


def test_fires_when_opted_in_by_name():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME

    structure = KnowledgeStructure([make_object("a", structure={"valid_until": PAST})])
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["temporal_validity"]

    result = validate(structure, extra_constraints=[constraint])

    # WARNING severity: still "valid" under the default min_severity=ERROR
    # threshold, but the diagnostic must be present once opted in.
    assert result.is_valid
    assert any(d.identity == "CKS-EXT-TEMPORAL-VALIDITY" for d in result.diagnostics)

    strict_result = validate(
        structure, extra_constraints=[constraint], min_severity=DiagnosticSeverity.WARNING
    )
    assert not strict_result.is_valid


def test_registered_as_optional_not_builtin():
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS

    builtin_identities = [c.identity for c in BUILTIN_CONSTRAINTS]
    optional_identities = [c.identity for c in OPTIONAL_CONSTRAINTS]

    assert "CKS-EXT-TEMPORAL-VALIDITY" in optional_identities
    assert "CKS-EXT-TEMPORAL-VALIDITY" not in builtin_identities
