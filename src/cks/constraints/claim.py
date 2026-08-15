"""
CKS Extension Constraints — Claim.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS
in `builtin.py`); callers must opt in explicitly.

Rationale
---------
A Claim is a regular immutable KnowledgeObject (`identity.type ==
"Claim"`) carrying a single asserted statement together with the
confidence, authorship, validity window, and provenance needed to
reason about it. Claims may support or contradict one another,
forming a graph of assertions layered on top of the canonical
structure without requiring any change to `KnowledgeObject`,
`KnowledgeStructure`, or the serialization model.

This constraint enforces *shape* only: required fields present and
well-typed, referenced ids resolving to existing objects, and
internal consistency of the support/contradiction graph (no
self-reference, no id appearing in both lists at once). It is
entirely deterministic and requires no LLM calls.
"""

from __future__ import annotations

from datetime import datetime

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension.
CLAIM_TYPE = "Claim"

_STATEMENT_KEY = "statement"
_CONFIDENCE_KEY = "confidence"
_AUTHOR_KEY = "author"
_AGENT_KEY = "agent"
_CREATED_AT_KEY = "created_at"
_VALID_FROM_KEY = "valid_from"
_VALID_UNTIL_KEY = "valid_until"
_PROVENANCE_IDS_KEY = "provenance_ids"
_SUPPORTING_CLAIMS_KEY = "supporting_claims"
_CONTRADICTING_CLAIMS_KEY = "contradicting_claims"
_STATUS_KEY = "status"

_ALLOWED_STATUS = frozenset(
    {"draft", "proposed", "accepted", "rejected", "superseded"}
)

_ID_LIST_KEYS = (
    _PROVENANCE_IDS_KEY,
    _SUPPORTING_CLAIMS_KEY,
    _CONTRADICTING_CLAIMS_KEY,
)

_CLAIM_ID_LIST_KEYS = (
    _SUPPORTING_CLAIMS_KEY,
    _CONTRADICTING_CLAIMS_KEY,
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
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        return True
    except ValueError:
        return False


def _is_string_list(value: object) -> bool:
    # KnowledgeObject.structure may store sequences as tuples rather than
    # lists (immutability), so accept either.
    return isinstance(value, (list, tuple)) and all(
        isinstance(item, str) for item in value
    )


def is_claim_object(obj: object) -> bool:
    """Return True if `obj` is a KnowledgeObject with identity.type == 'Claim'."""
    identity = getattr(obj, "identity", None)
    return getattr(identity, "type", None) == CLAIM_TYPE


class ClaimIntegrityConstraint(Constraint):
    """
    Every Claim object shall:

      1. carry the required fields ('statement', 'confidence',
         'author', 'created_at', 'status'), well-typed;
      2. carry a 'confidence' in [0, 1];
      3. carry a 'status' drawn from the closed vocabulary
         {draft, proposed, accepted, rejected, superseded};
      4. carry well-formed ISO 8601 timestamps for 'created_at',
         and, when present, 'valid_from' / 'valid_until';
      5. carry 'provenance_ids', 'supporting_claims', and
         'contradicting_claims' as lists of strings, when present,
         each referencing an existing object in the same structure;
      6. restrict 'supporting_claims' and 'contradicting_claims' to
         ids of other objects whose identity.type is also 'Claim';
      7. never reference itself in 'supporting_claims' or
         'contradicting_claims';
      8. never place the same id in both 'supporting_claims' and
         'contradicting_claims'.

    This constraint is additive: Knowledge Structures that do not use
    the Claim type are entirely unaffected by it.
    """

    identity = "CKS-EXT-CLAIM-INTEGRITY"
    stage = ValidationStage.SEMANTIC
    description = (
        "Claim objects must carry well-formed required fields and a "
        "self-consistent support/contradiction graph."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        objects_by_id = {obj.identity.id: obj for obj in structure.objects}

        for obj in structure.objects:
            if obj.identity.type != CLAIM_TYPE:
                continue

            oid = obj.identity.id
            data = obj.structure

            statement = data.get(_STATEMENT_KEY)
            if not isinstance(statement, str) or not statement:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' must carry a non-empty string "
                            f"'{_STATEMENT_KEY}' (got {statement!r})."
                        ),
                        location=oid,
                    )
                )

            confidence = data.get(_CONFIDENCE_KEY)
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not (0 <= confidence <= 1)
            ):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' must carry a '{_CONFIDENCE_KEY}' "
                            f"number in [0, 1] (got {confidence!r})."
                        ),
                        location=oid,
                    )
                )

            author = data.get(_AUTHOR_KEY)
            if not isinstance(author, str) or not author:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' must carry a non-empty string "
                            f"'{_AUTHOR_KEY}' (got {author!r})."
                        ),
                        location=oid,
                    )
                )

            status = data.get(_STATUS_KEY)
            if status not in _ALLOWED_STATUS:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' has '{_STATUS_KEY}'={status!r}, "
                            f"which is not one of the recognized statuses "
                            f"({', '.join(sorted(_ALLOWED_STATUS))})."
                        ),
                        location=oid,
                    )
                )

            if not _is_valid_iso8601(data.get(_CREATED_AT_KEY)):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' must carry a well-formed ISO 8601 "
                            f"'{_CREATED_AT_KEY}' timestamp "
                            f"(got {data.get(_CREATED_AT_KEY)!r})."
                        ),
                        location=oid,
                    )
                )

            for key in (_VALID_FROM_KEY, _VALID_UNTIL_KEY):
                if (
                    key in data
                    and data.get(key) is not None
                    and not _is_valid_iso8601(data.get(key))
                ):
                    diagnostics.append(
                        _error(
                            identity=self.identity,
                            message=(
                                f"Claim '{oid}' has '{key}'="
                                f"{data.get(key)!r}, which is not a "
                                f"well-formed ISO 8601 timestamp."
                            ),
                            location=oid,
                        )
                    )

            if (
                _AGENT_KEY in data
                and data.get(_AGENT_KEY) is not None
                and not isinstance(data.get(_AGENT_KEY), str)
            ):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' has '{_AGENT_KEY}'="
                            f"{data.get(_AGENT_KEY)!r}, which must be a "
                            f"string when present."
                        ),
                        location=oid,
                    )
                )

            malformed_id_list = False
            for key in _ID_LIST_KEYS:
                if key in data and not _is_string_list(data.get(key)):
                    malformed_id_list = True
                    diagnostics.append(
                        _error(
                            identity=self.identity,
                            message=(
                                f"Claim '{oid}' has '{key}'="
                                f"{data.get(key)!r}, which must be a list of "
                                f"strings when present."
                            ),
                            location=oid,
                        )
                    )

            if malformed_id_list:
                # Referential and graph-consistency checks below assume
                # well-typed lists; skip them for this object rather than
                # cascading confusing secondary diagnostics.
                continue

            for key in _ID_LIST_KEYS:
                for ref_id in data.get(key, []) or []:
                    if ref_id not in objects_by_id:
                        diagnostics.append(
                            _error(
                                identity=self.identity,
                                message=(
                                    f"Claim '{oid}' references unknown object "
                                    f"'{ref_id}' in '{key}'."
                                ),
                                location=oid,
                            )
                        )

            for key in _CLAIM_ID_LIST_KEYS:
                for ref_id in data.get(key, []) or []:
                    target = objects_by_id.get(ref_id)
                    if target is not None and not is_claim_object(target):
                        diagnostics.append(
                            _error(
                                identity=self.identity,
                                message=(
                                    f"Claim '{oid}' references '{ref_id}' in "
                                    f"'{key}', but that object's "
                                    f"identity.type is "
                                    f"{target.identity.type!r}, not "
                                    f"'{CLAIM_TYPE}'."
                                ),
                                location=oid,
                            )
                        )

            supporting = set(data.get(_SUPPORTING_CLAIMS_KEY, []) or [])
            contradicting = set(data.get(_CONTRADICTING_CLAIMS_KEY, []) or [])

            if oid in supporting or oid in contradicting:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' must not reference itself in "
                            f"'{_SUPPORTING_CLAIMS_KEY}' or "
                            f"'{_CONTRADICTING_CLAIMS_KEY}'."
                        ),
                        location=oid,
                    )
                )

            overlap = supporting & contradicting
            if overlap:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Claim '{oid}' has the same id(s) "
                            f"({', '.join(sorted(overlap))}) in both "
                            f"'{_SUPPORTING_CLAIMS_KEY}' and "
                            f"'{_CONTRADICTING_CLAIMS_KEY}'."
                        ),
                        location=oid,
                    )
                )

        return diagnostics


__all__ = [
    "CLAIM_TYPE",
    "ClaimIntegrityConstraint",
    "is_claim_object",
]
