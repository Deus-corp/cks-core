"""
Rename — Identity Mutation (CKS-004).
"""

from __future__ import annotations

from ..core import CanonicalRelation, KnowledgeObject
from .base import OperatorContract, StructuralOperator


class RenameObject(StructuralOperator):
    """
    Rename an existing KnowledgeObject: change its ``identity.name``
    while leaving ``identity.id`` and ``identity.type`` untouched.

    This is strictly weaker than a full identity change: ``id`` is the
    canonical reference key used by every ``CanonicalRelation``'s
    ``participants`` list, so keeping it means no relation is invalidated
    and no cascade is needed. Only the human-readable ``name`` field —
    which carries no structural semantics inside the graph — is updated.

    Use ``RemoveObject`` + ``AddObject`` if you need to change the ``id``
    or ``type`` of an object (at the cost of cascade-removing all
    referencing relations first).
    """

    def __init__(self, object_id: str, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("new_name must be a non-empty string.")
        self._object_id = object_id
        self._new_name = new_name

    @property
    def object_id(self) -> str:
        """The id of the object to rename."""
        return self._object_id

    @property
    def new_name(self) -> str:
        """The new human-readable name for the object."""
        return self._new_name

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        target = objects.get(self._object_id)
        if target is None:
            raise ValueError(f"Object '{self._object_id}' does not exist.")

        from ..core import ObjectIdentity

        new_identity = ObjectIdentity(
            id=target.identity.id,
            type=target.identity.type,
            name=self._new_name,
        )
        if isinstance(target, CanonicalRelation):
            objects[self._object_id] = CanonicalRelation(
                identity=new_identity,
                participants=list(target.participants),
                relation_type=target.relation_type,
                structure={
                    k: v
                    for k, v in target.structure.items()
                    if k not in ("participants", "relation_type")
                },
            )
        else:
            objects[self._object_id] = KnowledgeObject(
                identity=new_identity,
                structure=dict(target.structure),
            )

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=(
                f"Rename KnowledgeObject '{self._object_id}' "
                f"to '{self._new_name}'."
            ),
            preconditions=("The object must exist.",),
            postconditions=(
                "The object's identity.name is updated to the new value.",
                "The object's identity.id and identity.type are unchanged.",
            ),
            invariant_obligations=(
                (
                    "Referential integrity is preserved (no relation is "
                    "touched, since the object's id does not change)."
                ),
            ),
        )
