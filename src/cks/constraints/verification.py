"""
CKS Extension Constraints — Verification Records.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS
in `builtin.py`); callers must opt in explicitly.

Rationale
---------
CKS-001 ("Documents as Structural Projections") treats every concrete
representation of a Canonical Knowledge Structure as a projection,
never as a primary source of semantics:

    Document = Projection(CKS)

`projection.py` already extends this to vector-space representations.
This module extends it once more, in the opposite direction: instead
of projecting a Knowledge Object *outward* into a representation, a
VerificationRecord projects an *external* ground-truth check *back
into* the canonical graph:

    VerificationRecord = Projection(external check) onto a Knowledge Object

A VerificationRecord is a specialised Knowledge Object recording the
technical fact that some other canonical object (typically a
Document) was checked against an outside source of truth -- an HTTP
request, a search result, a human review -- at a specific time, with
a specific outcome. It exists to close a specific, observed failure
mode: an LLM narrating a plausible-looking verification ("HTTP 200",
a reliability score, a confidence table) without ever performing it.

What this constraint can and cannot guarantee
----------------------------------------------
This constraint enforces *shape*: required fields present and
well-typed, exactly one `verified_by` link to an existing subject,
and no qualitative judgment smuggled in alongside the technical
fact. It CANNOT verify *provenance* -- that the recorded check
actually happened. A well-formed but entirely fabricated
VerificationRecord passes this constraint exactly as cleanly as a
genuine one; static structural validation has no way to distinguish
them, and this is not a gap that can be closed inside cks-core
(CKS-001 Non-Goals: execution environments and tool ecosystems are
explicitly out of scope for the Core Specification).

Real provenance enforcement belongs one layer up: a dedicated
runtime/MCP tool should be the *sole* sanctioned constructor of
VerificationRecord objects, building them itself from the result of
an actual tool call rather than accepting caller-supplied JSON --
the same pattern already used by `validate_knowledge`, which computes
`valid` itself instead of trusting a caller-supplied boolean.

`checked_via` is deliberately a small, closed, implementation-
independent vocabulary rather than concrete tool names (e.g.
"web_fetch") -- naming a specific vendor's tool inside cks-core would
violate Representation/Implementation Independence (CKS-000,
Principle 2). A runtime adapter maps its actual tool call onto one of
these categories when constructing the record.
"""

from __future__ import annotations

from datetime import datetime

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension.
VERIFIED_BY_RELATION = "verified_by"
VERIFICATION_RECORD_TYPE = "VerificationRecord"

# Required structural content keys.
_HTTP_STATUS_KEY = "http_status"
_CHECKED_AT_KEY = "checked_at"
_CHECKED_VIA_KEY = "checked_via"

# Implementation-independent verification method categories. A runtime
# adapter maps its concrete tool (web_fetch, a browser, a human review
# queue, ...) onto one of these before constructing the record; core
# never sees vendor-specific tool names.
_ALLOWED_CHECKED_VIA = frozenset(
    {
        "automated_http_check",
        "automated_search_check",
        "manual_review",
    }
)

# A VerificationRecord states a technical fact about a check, not an
# opinion about the subject. Qualitative judgment must not be smuggled
# in alongside it -- this is the exact shape of the fabricated
# "reliability score" table this constraint exists to make impossible
# to pass off as verified fact.
_DISALLOWED_QUALITATIVE_KEYS = (
    "reliability_score",
    "confidence",
    "score",
    "reasons",
    "warning_signs",
    "recommendations",
)


def _error(*, identity: str, message: str, location: str | None = None) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


def _is_valid_iso8601(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        # Accept the common "...Z" suffix alongside stdlib's native offset format.
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


class VerificationRecordIntegrityConstraint(Constraint):
    """
    Every VerificationRecord object shall:

      1. have exactly one 'verified_by' relation, linking an existing
         subject object to this record;
      2. carry a well-formed 'checked_at' (ISO 8601) timestamp;
      3. carry a 'checked_via' value drawn from the closed,
         implementation-independent method vocabulary;
      4. carry a well-formed 'http_status' (100-599) when present --
         it is optional, since not every verification method
         produces one;
      5. never carry qualitative judgment fields (reliability
         scoring, confidence, recommendations) -- those are opinions
         about the subject, not facts about the check, and must not
         be presented as though they were mechanically verified.

    Deliberately NOT checked: whether 'checked_at' lies in the past.
    Comparing against wall-clock time at evaluation time would make
    Validity depend on when it is evaluated rather than exclusively
    on canonical structure, violating the Determinism principle
    (CKS-005) and Canonical Law 9 (Computability, CKS-001).

    This constraint is additive: Knowledge Structures that do not use
    the VerificationRecord type are entirely unaffected by it.
    """

    identity = "CKS-EXT-VERIFICATION-RECORD"
    stage = ValidationStage.SEMANTIC
    description = (
        "VerificationRecord objects must carry exactly one valid "
        "provenance link and a well-formed, purely factual check record."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        existing = {obj.identity.id for obj in structure.objects}

        # record_id -> [subject_id, ...]
        subjects_by_record: dict[str, list[str]] = {}
        for relation in structure.relations():
            if relation.relation_type != VERIFIED_BY_RELATION:
                continue
            if len(relation.participants) != 2:
                continue
            subject_id, record_id = relation.participants
            subjects_by_record.setdefault(record_id, []).append(subject_id)

        for obj in structure.objects:
            if obj.identity.type != VERIFICATION_RECORD_TYPE:
                continue

            subjects = subjects_by_record.get(obj.identity.id, [])
            if len(subjects) != 1:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"VerificationRecord '{obj.identity.id}' must have "
                            f"exactly one '{VERIFIED_BY_RELATION}' relation to "
                            f"the subject it verifies (found {len(subjects)})."
                        ),
                        location=obj.identity.id,
                    )
                )
            elif subjects[0] not in existing:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"VerificationRecord '{obj.identity.id}' references "
                            f"unknown subject object '{subjects[0]}'."
                        ),
                        location=obj.identity.id,
                    )
                )

            checked_at = obj.structure.get(_CHECKED_AT_KEY)
            if not _is_valid_iso8601(checked_at):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"VerificationRecord '{obj.identity.id}' must carry "
                            f"a well-formed ISO 8601 '{_CHECKED_AT_KEY}' "
                            f"timestamp (got {checked_at!r})."
                        ),
                        location=obj.identity.id,
                    )
                )

            checked_via = obj.structure.get(_CHECKED_VIA_KEY)
            if checked_via not in _ALLOWED_CHECKED_VIA:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"VerificationRecord '{obj.identity.id}' has "
                            f"'{_CHECKED_VIA_KEY}'={checked_via!r}, which is not "
                            f"one of the recognized verification methods "
                            f"({', '.join(sorted(_ALLOWED_CHECKED_VIA))})."
                        ),
                        location=obj.identity.id,
                    )
                )

            if _HTTP_STATUS_KEY in obj.structure:
                http_status = obj.structure.get(_HTTP_STATUS_KEY)
                if (
                    not isinstance(http_status, int)
                    or isinstance(http_status, bool)
                    or not (100 <= http_status <= 599)
                ):
                    diagnostics.append(
                        _error(
                            identity=self.identity,
                            message=(
                                f"VerificationRecord '{obj.identity.id}' has "
                                f"'{_HTTP_STATUS_KEY}'={http_status!r}, which is "
                                f"not a valid HTTP status code (100-599)."
                            ),
                            location=obj.identity.id,
                        )
                    )

            leaked = [k for k in _DISALLOWED_QUALITATIVE_KEYS if k in obj.structure]
            if leaked:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"VerificationRecord '{obj.identity.id}' must not "
                            f"carry qualitative judgment fields "
                            f"({', '.join(sorted(leaked))}); a verification "
                            f"record states a technical fact about the check, "
                            f"not an opinion about the subject."
                        ),
                        location=obj.identity.id,
                    )
                )

        return diagnostics


__all__ = [
    "VerificationRecordIntegrityConstraint",
    "VERIFIED_BY_RELATION",
    "VERIFICATION_RECORD_TYPE",
]
