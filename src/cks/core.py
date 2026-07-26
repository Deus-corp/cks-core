"""
CKS Core — Canonical Knowledge Objects.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Literal, Mapping, Union


def _freeze(value: Any) -> Any:
    """Recursively freeze a canonical value."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _freeze_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({key: _freeze(value) for key, value in mapping.items()})


# ============================================================================
# Canonical (Merkle-style) Hashing
# ============================================================================
#
# _canonical_hash(value) is a deterministic digest of a frozen CKS
# value, used to give KnowledgeObject/CanonicalRelation a leaf hash and
# KnowledgeStructure a root hash for O(1) structural-equivalence
# comparison (see KnowledgeStructure.structurally_equivalent below).
#
# Every recursive call returns a FIXED-SIZE 32-byte SHA-256 digest.
# This is what makes the encoding provably unambiguous without needing
# a length prefix between every concatenated piece: once a child value
# has been reduced to a fixed-width digest, concatenating any number
# of such digests can never be mis-parsed as a different grouping of
# digests, the way concatenating variable-length strings can (e.g.
# str(tuple(...)) is NOT a safe hash preimage -- Python's repr rules
# for 1-tuples vs 2-tuples happen to block the simplest such collision,
# but that is an accident of CPython's repr, not a guaranteed property
# of the encoding). Only true leaves (str/int/float/bool/None/...) and
# the element *count* of a container are length-prefixed, since those
# are the only variable-width pieces left once children are digests.
#
# This hash is used for equivalence checks and diffing, not as a
# cryptographic commitment exposed outside the process -- a negligible
# collision probability under SHA-256 is an accepted trade-off for
# O(1) comparison, consistent with how e.g. git or Merkle-based
# storage systems treat content hashes.

_HASH_TAG_MAP = b"map"
_HASH_TAG_SEQ = b"seq"
_HASH_TAG_SET = b"set"
_HASH_TAG_LEAF = b"leaf"


def _uint32(n: int) -> bytes:
    return n.to_bytes(4, "big", signed=False)


def _canonical_hash(value: Any) -> bytes:
    """Return a 32-byte deterministic digest of a frozen CKS value."""
    if isinstance(value, Mapping):
        entries = sorted(
            (_canonical_hash(key), _canonical_hash(val)) for key, val in value.items()
        )
        body = b"".join(k_digest + v_digest for k_digest, v_digest in entries)
        return hashlib.sha256(_HASH_TAG_MAP + _uint32(len(entries)) + body).digest()

    if isinstance(value, (list, tuple)):
        body = b"".join(_canonical_hash(item) for item in value)
        return hashlib.sha256(_HASH_TAG_SEQ + _uint32(len(value)) + body).digest()

    if isinstance(value, (set, frozenset)):
        digests = sorted(_canonical_hash(item) for item in value)
        body = b"".join(digests)
        return hashlib.sha256(_HASH_TAG_SET + _uint32(len(digests)) + body).digest()

    # Leaf value (str, int, float, bool, None, ...). Both the type
    # name and the value's repr are individually length-prefixed, so
    # e.g. the leaf (type="str", value="5") can never be confused with
    # (type="int", value="5") or with a differently-split byte stream.
    type_name = type(value).__name__.encode("ascii")
    value_bytes = repr(value).encode("utf-8")
    payload = (
        _uint32(len(type_name)) + type_name + _uint32(len(value_bytes)) + value_bytes
    )
    return hashlib.sha256(_HASH_TAG_LEAF + payload).digest()


def _compute_leaf_hash(
    identity: "ObjectIdentity", structure: Mapping[str, Any]
) -> bytes:
    """Merkle leaf hash for one KnowledgeObject: its identity plus its
    (already-frozen) semantic structure."""
    identity_tuple = (identity.id, identity.type, identity.name)
    return _canonical_hash((identity_tuple, structure))


@dataclass(frozen=True, slots=True)
class ObjectIdentity:
    id: str
    type: str
    name: str


@dataclass(frozen=True, slots=True)
class KnowledgeObject:
    identity: ObjectIdentity
    structure: Mapping[str, Any] = field(default_factory=dict)

    #: Merkle leaf hash, computed once in __post_init__. Not part of
    #: the dataclass's generated __eq__/__repr__ (init=False,
    #: compare=False) since it is fully determined by identity+structure
    #: -- it is a cached derivation, not independent state.
    _hash: bytes = field(init=False, repr=False, compare=False)

    #: Canonical hash of just ``identity.id``, cached once here so
    #: KnowledgeStructure.__init__ can build ``_identity_hash`` by
    #: sorting/concatenating already-computed digests instead of
    #: recomputing a SHA-256 leaf hash per id on every single
    #: structure construction (every StructuralOperator.apply()
    #: builds a brand new KnowledgeStructure, so this constructor
    #: runs far more often than any individual object changes).
    _id_hash: bytes = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        frozen_structure = _freeze_mapping(self.structure)
        object.__setattr__(self, "structure", frozen_structure)
        object.__setattr__(
            self, "_hash", _compute_leaf_hash(self.identity, frozen_structure)
        )
        object.__setattr__(self, "_id_hash", _canonical_hash(self.identity.id))

    # ------------------------------------------------------------------
    # Copy semantics
    # ------------------------------------------------------------------
    # KnowledgeObject is immutable by contract, so copy/deepcopy can
    # safely return the same instance rather than attempting to clone
    # the internal MappingProxyType (which the stdlib copy module
    # cannot pickle-based deep-copy).
    def __copy__(self) -> "KnowledgeObject":
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> "KnowledgeObject":
        memo[id(self)] = self
        return self


class CanonicalRelation(KnowledgeObject):
    def __init__(
        self,
        identity: ObjectIdentity,
        *,
        participants: Iterable[str],
        relation_type: str,
        structure: Mapping[str, Any] | None = None,
    ) -> None:
        # A bare str/bytes value is technically Iterable[str]-compatible
        # (iterating one yields one-character strings), so tuple(...)
        # below would otherwise silently succeed and split e.g. "earth"
        # into ('e', 'a', 'r', 't', 'h') instead of raising -- almost
        # certainly not what a caller who forgot to wrap a single id in
        # a list intended. Checking here, in CanonicalRelation's own
        # constructor, protects every caller (direct construction,
        # cks.evolution.parse_operations, the CLI, or anywhere else),
        # not just CanonicalDeserializer, which already guards against
        # this independently in serialization.py.
        if isinstance(participants, (str, bytes)):
            raise TypeError(
                "CanonicalRelation participants must be a list of object "
                f"ids, not a bare {type(participants).__name__} "
                f"({participants!r}). Did you mean to wrap it in a list?"
            )
        frozen_participants = tuple(participants)
        if len(frozen_participants) < 2:
            raise ValueError(
                "CanonicalRelation requires at least two participants, "
                f"got {len(frozen_participants)}: {frozen_participants!r}."
            )
        if not all(isinstance(p, str) for p in frozen_participants):
            raise ValueError(
                "CanonicalRelation participants must all be strings, got "
                f"{frozen_participants!r}."
            )
        struct = dict(structure or {})
        for key, expected in (
            ("participants", frozen_participants),
            ("relation_type", relation_type),
        ):
            if key in struct:
                existing = struct[key]
                if key == "participants" and isinstance(existing, list):
                    existing = tuple(existing)
                if existing != expected:
                    raise ValueError(
                        f"Conflicting value for '{key}' in structure: "
                        f"expected {expected!r}, got {struct[key]!r}"
                    )
        struct["participants"] = frozen_participants
        struct["relation_type"] = relation_type
        frozen_struct = _freeze_mapping(struct)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "structure", frozen_struct)
        object.__setattr__(self, "_hash", _compute_leaf_hash(identity, frozen_struct))
        object.__setattr__(self, "_id_hash", _canonical_hash(identity.id))

    @property
    def participants(self) -> tuple[str, ...]:
        return tuple(self.structure["participants"])

    @property
    def relation_type(self) -> str:
        return str(self.structure["relation_type"])


def _normalize_structure(
    structure: Mapping[str, Any],
) -> tuple[tuple[str, object], ...]:
    frozen = _freeze_mapping(structure)
    return tuple(sorted(frozen.items()))


class KnowledgeStructure:
    __slots__ = ("_objects", "_index", "_relations", "_root_hash", "_identity_hash")

    def __init__(self, objects: Iterable[KnowledgeObject]) -> None:
        object_list: list[KnowledgeObject] = []
        index: dict[str, KnowledgeObject] = {}
        relations: list[CanonicalRelation] = []
        for obj in objects:
            oid = obj.identity.id
            if oid in index:
                raise ValueError(f"Duplicate canonical identity '{oid}'.")
            index[oid] = obj
            object_list.append(obj)
            if isinstance(obj, CanonicalRelation):
                relations.append(obj)
        self._objects = tuple(object_list)
        self._index = index
        self._relations = tuple(relations)

        # Merkle root: hash of the sorted set of leaf hashes. Sorting
        # makes the root independent of construction/insertion order,
        # matching the order-independence _canonical_signature already
        # guaranteed before this hash existed.
        sorted_leaf_hashes = sorted(obj._hash for obj in object_list)
        self._root_hash = hashlib.sha256(
            _HASH_TAG_SET
            + _uint32(len(sorted_leaf_hashes))
            + b"".join(sorted_leaf_hashes)
        ).digest()

        # A second, narrower hash over identities only (ids present),
        # backing identity_equivalent -- unaffected by content changes.
        # Uses each object's cached _id_hash (set once when that
        # KnowledgeObject was constructed) rather than recomputing
        # _canonical_hash(id) here, since this constructor runs on
        # every structural edit regardless of how many ids actually
        # changed.
        sorted_id_hashes = sorted(obj._id_hash for obj in object_list)
        self._identity_hash = hashlib.sha256(
            _HASH_TAG_SET + _uint32(len(sorted_id_hashes)) + b"".join(sorted_id_hashes)
        ).digest()

    def __len__(self) -> int:
        return len(self._objects)

    def __iter__(self) -> Iterator[KnowledgeObject]:
        return iter(self._objects)

    def __contains__(self, identity: str) -> bool:
        return identity in self._index

    @property
    def objects(self) -> tuple[KnowledgeObject, ...]:
        return self._objects

    def relations(self) -> tuple[CanonicalRelation, ...]:
        return self._relations

    def get(self, identity: str) -> KnowledgeObject | None:
        return self._index.get(identity)

    @property
    def root_hash(self) -> str:
        """Hex digest of the Merkle root, for external comparison/logging."""
        return self._root_hash.hex()

    def _canonical_signature(self) -> tuple:
        signature = []
        for obj in self._objects:
            structure = _normalize_structure(obj.structure)
            signature.append(
                (obj.identity.id, obj.identity.type, obj.identity.name, structure)
            )
        return tuple(sorted(signature))

    def structurally_equivalent(self, other: object) -> bool:
        """
        Whether `other` has the same content as this structure.

        Implemented as O(1) root-hash comparison rather than the
        O(N log N) signature comparison this used before: two
        structures with the same objects (any order) hash to the same
        SHA-256 root, and a hash collision between genuinely different
        structures is cryptographically negligible -- the same
        trade-off git and other Merkle-based systems make for content
        equality.
        """
        if not isinstance(other, KnowledgeStructure):
            return False
        return self._root_hash == other._root_hash

    def identity_equivalent(self, other: object) -> bool:
        if not isinstance(other, KnowledgeStructure):
            return False
        return self._identity_hash == other._identity_hash

    def __eq__(self, other: object) -> bool:
        return self.structurally_equivalent(other)

    def __hash__(self) -> int:
        # KnowledgeStructure was previously unhashable (an __eq__
        # without a matching __hash__ makes Python set __hash__ =
        # None). Now that equality is itself hash-based, exposing a
        # consistent __hash__ is both correct (equal objects already
        # share a root hash, so they trivially share this too) and
        # useful -- e.g. structures as dict keys or set members.
        return hash(self._root_hash)

    def __repr__(self) -> str:
        return f"KnowledgeStructure(objects={len(self._objects)}, relations={len(self._relations)})"

    # ------------------------------------------------------------------
    # Copy semantics
    # ------------------------------------------------------------------
    # KnowledgeStructure is immutable by contract. Returning self
    # avoids deep-copying internal MappingProxyType-bearing objects.
    def __copy__(self) -> "KnowledgeStructure":
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> "KnowledgeStructure":
        memo[id(self)] = self
        return self

    # ------------------------------------------------------------------
    # Structural Diff
    # ------------------------------------------------------------------

    def diff(self, target: "KnowledgeStructure") -> list[Any]:
        """
        Compute the ordered list of StructuralOperators that, applied
        via cks.evolution.compose(self, ops), reconstruct `target`.

        Cascade correctness: RemoveObject.apply() removes not just the
        target object but every CanonicalRelation that references it
        (see RemoveObject's own docstring/contract). A diff that only
        compares "which ids differ between source and target" would
        miss this: a relation whose own hash is UNCHANGED but which
        references an object being removed or replaced would be
        silently destroyed by that cascade and never scheduled to
        come back -- the resulting structure would then NOT actually
        equal `target`, defeating the purpose of a diff. This method
        explicitly finds every such relation and folds it into the
        remove/add sets, even though from a pure id-comparison
        standpoint it "didn't change".

        Operation order -- relations removed, then objects removed,
        then objects added, then relations added -- guarantees no
        relation ever transiently references a nonexistent object
        during application (preserving referential integrity, i.e.
        NoDanglingRelationConstraint, at every intermediate step).
        """
        # Imported lazily (not at module scope) to avoid a circular
        # import: cks.evolution imports KnowledgeStructure/
        # CanonicalRelation from this module, so importing
        # cks.evolution back at module scope here would make the two
        # modules unable to finish initializing each other.
        from cks.evolution import AddObject, AddRelation, RemoveObject, RemoveRelation

        source_ids = set(self._index.keys())
        target_ids = set(target._index.keys())
        common_ids = source_ids & target_ids

        added_ids = target_ids - source_ids
        removed_ids = source_ids - target_ids
        modified_ids = {
            oid
            for oid in common_ids
            if self._index[oid]._hash != target._index[oid]._hash
        }

        def is_relation(structure: "KnowledgeStructure", oid: str) -> bool:
            return isinstance(structure._index[oid], CanonicalRelation)

        # Direct (non-cascade) changes, split into objects vs relations.
        direct_remove_relations = {
            oid for oid in (removed_ids | modified_ids) if is_relation(self, oid)
        }
        direct_remove_objects = {
            oid for oid in (removed_ids | modified_ids) if not is_relation(self, oid)
        }
        direct_add_relations = {
            oid for oid in (added_ids | modified_ids) if is_relation(target, oid)
        }
        direct_add_objects = {
            oid for oid in (added_ids | modified_ids) if not is_relation(target, oid)
        }

        # Cascade: every relation in SOURCE that references an object
        # about to disappear (removed outright, or modified -- which
        # requires remove-then-add since there is no in-place modify
        # operator) will be cascade-deleted by RemoveObject.apply(),
        # regardless of whether it was otherwise scheduled for removal.
        cascade_relations = {
            rel.identity.id
            for rel in self._relations
            if any(pid in direct_remove_objects for pid in rel.participants)
        }
        cascade_only_relations = cascade_relations - direct_remove_relations

        all_remove_relations = direct_remove_relations | cascade_only_relations
        # A cascade-only relation must be re-added afterwards using
        # target's copy IF it still exists there; if it doesn't, the
        # cascade deletion was correct and nothing more is needed.
        all_add_relations = direct_add_relations | (cascade_only_relations & target_ids)

        operators: list[Any] = []
        for rid in all_remove_relations:
            operators.append(RemoveRelation(rid))
        for oid in direct_remove_objects:
            operators.append(RemoveObject(oid))
        for oid in direct_add_objects:
            operators.append(AddObject(target._index[oid]))
        for rid in all_add_relations:
            operators.append(AddRelation(target._index[rid]))

        return operators

    # ------------------------------------------------------------------
    # Three-Way Merge
    # ------------------------------------------------------------------

    def merge(
        self,
        branch_a: "KnowledgeStructure",
        branch_b: "KnowledgeStructure",
        *,
        resolutions: Mapping[str, "MergeResolution"] | None = None,
        dropped_relations: list[str] | None = None,
    ) -> "KnowledgeStructure":
        """
        Three-way merge. ``self`` is the common ancestor (base);
        ``branch_a`` and ``branch_b`` are two structures independently
        evolved from it.

        An identity is a conflict only when BOTH branches changed it
        (added, removed, or modified relative to base) AND ended up
        with different results:

        - both branches introducing the identical object/relation
          (same id, same content) is NOT a conflict -- it converges;
        - both branches removing the same identity is NOT a conflict
          -- they agree it's gone;
        - one branch removing an identity while the other modifies
          it (or leaves a different value under the same id) IS a
          conflict -- there is no way to reconcile "gone" with
          "changed to X" without the caller deciding;
        - both branches modifying the same identity to different
          content IS a conflict.

        This mirrors :meth:`diff`'s own id-and-hash comparison rather
        than introspecting evolution operators: comparing final
        object hashes at each touched id is both simpler and more
        precise than trying to tell "these two operators represent
        the same change" apart from bare id overlap.

        Referential integrity: if an object is removed by either
        branch, any relation that still references it -- even one
        neither branch's own ``touched`` set flags, e.g. inherited
        unchanged from ``self`` -- is dropped from the result rather
        than emitting a structure with a dangling reference. This is
        the same contract :class:`~cks.evolution.RemoveObject` itself
        enforces via cascade deletion, applied here defensively so
        ``merge()`` never depends on both inputs having been built
        through operators that already cascade correctly. This
        includes relations introduced by a ``resolutions`` override:
        a custom resolution whose participants don't all survive the
        merge is dropped the same way.

        Parameters
        ----------
        branch_a, branch_b
            Structures assumed to have evolved from ``self`` (though
            this is not verified -- callers are responsible for
            supplying structures that actually share ``self`` as an
            ancestor; merging unrelated structures will simply treat
            every identity present in one but not ``self`` as an
            addition).
        resolutions
            Optional per-identity conflict resolutions, keyed by
            object id. This turns ``merge`` into a *partial* merge:
            every non-conflicting identity is still merged
            automatically as usual, and any conflicting identity
            present in ``resolutions`` is resolved using the supplied
            value instead of blocking the merge. Only identities that
            conflict AND have no entry in ``resolutions`` still raise
            ``MergeConflictError`` -- with a conflict list narrowed to
            just those remaining identities, so a caller can supply
            resolutions incrementally across retries. Each value is
            one of:

            - ``"branch_a"`` -- take ``branch_a``'s value for this id
              (removing it from the result if ``branch_a`` removed it).
            - ``"branch_b"`` -- take ``branch_b``'s value for this id,
              symmetrically.
            - ``None`` -- resolve by deliberately dropping the
              identity from the merged result, regardless of what
              either branch did.
            - a ``KnowledgeObject``/``CanonicalRelation`` instance --
              use this exact object as the merged content for that id
              (its ``identity.id`` must equal the key). This is how a
              caller reconciles two irreconcilable positions into a
              new, synthesized value rather than picking one side.
        dropped_relations
            Optional output list. When given, the ``identity.id`` of
            every relation excluded from the result because one or
            more of its participants didn't survive the merge (see
            "Referential integrity" above) is appended to it. This
            does not change what merge() returns -- referential
            integrity is enforced either way -- it only makes an
            otherwise-silent exclusion visible to the caller, e.g. to
            report "relation X was not restored because node Y was
            removed" back to whoever is resolving the conflict.

        Returns
        -------
        KnowledgeStructure
            The merged result: every identity either branch added,
            removed, or modified is reflected; identities neither
            branch touched are carried over from ``self`` unchanged;
            resolved conflicts reflect their resolution.

        Raises
        ------
        MergeConflictError
            One or more identities were changed by both branches to
            different, irreconcilable results, and (if ``resolutions``
            was given) still have no entry there. ``error.conflicts``
            lists every such identity together with its value in
            ``self``, ``branch_a``, and ``branch_b`` (``None`` meaning
            "absent in that structure") so the caller can present or
            resolve each one.
        ValueError
            A ``resolutions`` entry names an id that isn't actually in
            conflict, uses an unrecognized string value, or supplies
            an object whose ``identity.id`` doesn't match its key.
        """
        base_ids = set(self._index)
        a_ids = set(branch_a._index)
        b_ids = set(branch_b._index)
        resolutions = resolutions or {}

        for oid, value in resolutions.items():
            if isinstance(value, (KnowledgeObject, CanonicalRelation)):
                if value.identity.id != oid:
                    raise ValueError(
                        f"resolutions['{oid}']: resolution object's "
                        f"identity.id ('{value.identity.id}') must "
                        f"equal the key."
                    )
            elif value not in ("branch_a", "branch_b", None):
                raise ValueError(
                    f"resolutions['{oid}']: expected 'branch_a', "
                    f"'branch_b', None, or a KnowledgeObject/"
                    f"CanonicalRelation instance; got {value!r}."
                )

        def touched_ids(ids: set, index: Mapping[str, KnowledgeObject]) -> set:
            added = ids - base_ids
            removed = base_ids - ids
            modified = {
                oid
                for oid in (base_ids & ids)
                if self._index[oid]._hash != index[oid]._hash
            }
            return added | removed | modified

        a_touched = touched_ids(a_ids, branch_a._index)
        b_touched = touched_ids(b_ids, branch_b._index)

        conflicts: list[MergeConflict] = []
        resolved: dict[str, "MergeResolution"] = {}
        # Ids actually in conflict, i.e. touched by both branches AND
        # ending up with different results -- narrower than
        # `a_touched & b_touched`, which also contains ids both
        # branches touched but converged on (same hash). Used below to
        # validate `resolutions`: a resolution for a converged id is
        # not "in conflict" even though it was touched by both
        # branches, and must be rejected the same way a resolution for
        # an untouched id would be.
        actual_conflict_ids: set[str] = set()
        for oid in sorted(a_touched & b_touched):
            a_obj = branch_a._index.get(oid)
            b_obj = branch_b._index.get(oid)
            a_hash = a_obj._hash if a_obj is not None else None
            b_hash = b_obj._hash if b_obj is not None else None
            if a_hash == b_hash:
                continue
            actual_conflict_ids.add(oid)
            if oid in resolutions:
                resolved[oid] = resolutions[oid]
            else:
                conflicts.append(
                    MergeConflict(
                        object_id=oid,
                        base=self._index.get(oid),
                        branch_a=a_obj,
                        branch_b=b_obj,
                    )
                )

        unused = set(resolutions) - actual_conflict_ids
        if unused:
            raise ValueError(
                "resolutions given for identities that are not "
                f"actually in conflict: {', '.join(sorted(unused))}."
            )

        if conflicts:
            raise MergeConflictError(conflicts)

        merged: dict[str, KnowledgeObject] = dict(self._index)
        for oid in a_touched:
            if oid in a_ids:
                merged[oid] = branch_a._index[oid]
            else:
                merged.pop(oid, None)
        for oid in b_touched:
            if oid in b_ids:
                merged[oid] = branch_b._index[oid]
            else:
                merged.pop(oid, None)
        for oid, value in resolved.items():
            if value == "branch_a":
                target = branch_a._index.get(oid)
            elif value == "branch_b":
                target = branch_b._index.get(oid)
            elif value is None:
                target = None
            else:
                target = value
            if target is None:
                merged.pop(oid, None)
            else:
                merged[oid] = target

        surviving_ids = set(merged)
        final_objects = []
        for obj in merged.values():
            if isinstance(obj, CanonicalRelation) and not set(obj.participants) <= surviving_ids:
                if dropped_relations is not None:
                    dropped_relations.append(obj.identity.id)
                continue
            final_objects.append(obj)

        return KnowledgeStructure(final_objects)

    # ------------------------------------------------------------------
    # Subgraph Query
    # ------------------------------------------------------------------

    def query_subgraph(
        self,
        seed_ids: str | Iterable[str],
        depth: int = 1,
        *,
        include_relation_types: set[str] | None = None,
        include_object_types: set[str] | None = None,
        max_tokens: int | None = None,
        max_objects: int | None = None,
        type_weights: dict[str, float] | None = None,
    ) -> "SubgraphResult":
        """
        Extract the local neighborhood around ``seed_ids`` out to
        ``depth`` hops, as a self-contained ``KnowledgeStructure`` with
        its own Merkle ``root_hash``.

        Referential integrity: a relation is included only if EVERY
        one of its participants is present in the returned node set.
        This is the standard vertex-induced-subgraph rule (the same
        one e.g. networkx's ``G.subgraph()`` uses): it applies to
        every relation in ``self``, not only ones actually crossed
        during the BFS, so an edge whose endpoints both happen to
        survive is kept even if traversal reached them by different
        paths. There is never a relation in the result referencing an
        object outside it -- callers never see a dangling reference.

        Traversal follows relations as (possibly n-ary) hyperedges:
        from any current-frontier participant, every other participant
        of a shared relation is reachable in one hop, matching
        ``CanonicalRelation.participants`` not being restricted to
        exactly two ids.

        Budget (optional): when ``max_tokens`` and/or ``max_objects``
        is given and the full neighborhood exceeds it, candidates
        (everything but the seeds, which are always kept) are ranked
        by

            score(v) = (degree(v) * type_weight(v)) / (distance(v) + 1)

        and taken highest-score-first until the budget is spent.
        ``degree`` counts relation-participations anywhere in ``self``
        (a hub/architectural-node signal, not just within this
        neighborhood); ``distance`` is hop count from the nearest seed;
        ``type_weight`` defaults to 1.0 for any type not present in
        ``type_weights``. Budget-driven omission never breaks the
        no-dangling-relation guarantee above -- an omitted node's
        relations are simply excluded too.

        Parameters
        ----------
        seed_ids
            One id, or a set of ids, to start from. Ids absent from
            ``self`` are silently ignored; if none are valid, an empty
            result is returned rather than raising.
        depth
            Maximum number of hops from any seed. ``0`` returns just
            the (valid) seeds themselves.
        include_relation_types
            If given, only relations whose ``relation_type`` is in
            this set are traversed AND included in the result -- a
            relation type excluded here neither connects nodes nor
            appears in the output.
        include_object_types
            If given, restricts which *discovered* (non-seed) objects
            are allowed into the neighborhood. Seeds are always
            included regardless of their own type.
        max_tokens, max_objects
            Optional budget(s) on the returned neighborhood, beyond
            the always-kept seeds. A candidate already over
            ``max_tokens`` is skipped (smaller candidates further down
            the ranking may still fit); ``max_objects`` is a hard cap
            on returned node count (seeds do not count towards this budget)
            and stops selection outright once hit.
        type_weights
            Optional per-``identity.type`` multiplier used only in the
            budget-ranking score above; irrelevant when no budget is
            given (the full neighborhood is returned as found).

        Returns
        -------
        SubgraphResult
            Wraps the extracted ``structure`` together with
            ``total_found_nodes`` (the full neighborhood, pre-budget),
            ``returned_nodes``, ``is_truncated``, ``truncation_reason``,
            and ``suggested_next_seed`` -- the single highest-ranked
            node left out by the budget, if any, so a caller (e.g. an
            LLM agent) can explicitly continue exploring from there
            instead of wrongly concluding the neighborhood ends where
            the response did.
        """
        if isinstance(seed_ids, str):
            seeds = {seed_ids}
        else:
            seeds = set(seed_ids)

        # A Relation's own id is never a valid seed -- seeding on one
        # would let a bare CanonicalRelation into the result with none
        # of its participants present, violating the no-dangling-
        # reference guarantee documented above. Discovered relations
        # are already excluded the same way further down; mirror that
        # here for seeds.
        valid_seeds = {
            sid
            for sid in seeds
            if sid in self._index
            and not isinstance(self._index[sid], CanonicalRelation)
        }
        if not valid_seeds:
            return SubgraphResult(
                structure=KnowledgeStructure([]),
                total_found_nodes=0,
                returned_nodes=0,
                is_truncated=False,
                truncation_reason=None,
                suggested_next_seed=None,
            )

        # Single pass: adjacency (for BFS) and degree (for scoring),
        # both restricted to the traversable relation types.
        adj_relations: dict[str, list[CanonicalRelation]] = {}
        degree_map: dict[str, int] = {}
        for rel in self._relations:
            if (
                include_relation_types
                and rel.relation_type not in include_relation_types
            ):
                continue
            for pid in rel.participants:
                adj_relations.setdefault(pid, []).append(rel)
                degree_map[pid] = degree_map.get(pid, 0) + 1

        # BFS out to `depth` hops, recording each discovered object's
        # distance from the nearest seed (seeds are distance 0).
        distance_map: dict[str, int] = {sid: 0 for sid in valid_seeds}
        visited_object_ids = set(valid_seeds)
        frontier = set(valid_seeds)

        for current_depth in range(1, depth + 1):
            next_frontier = set()
            for current_id in frontier:
                for rel in adj_relations.get(current_id, []):
                    for part_id in rel.participants:
                        if part_id in self._index and part_id not in visited_object_ids:
                            obj = self._index[part_id]
                            if isinstance(obj, CanonicalRelation):
                                continue
                            if (
                                include_object_types
                                and obj.identity.type not in include_object_types
                            ):
                                continue
                            visited_object_ids.add(part_id)
                            distance_map[part_id] = current_depth
                            next_frontier.add(part_id)
            frontier = next_frontier
            if not frontier:
                break

        total_found_nodes = len(visited_object_ids)

        # Budget selection: seeds are unconditional; candidates are
        # ranked and taken highest-score-first until spent.
        selected_object_ids = set(valid_seeds)
        current_tokens = sum(
            _estimate_subgraph_tokens(self._index[sid]) for sid in valid_seeds
        )
        candidate_ids = visited_object_ids - valid_seeds
        ranked_candidates: list[str] = []
        hit_max_objects = False
        hit_max_tokens = False

        if (max_tokens or max_objects) and candidate_ids:
            weights = type_weights or {}

            def compute_score(oid: str) -> float:
                obj = self._index[oid]
                dist = distance_map.get(oid, depth)
                deg = degree_map.get(oid, 1)
                type_w = weights.get(obj.identity.type, 1.0)
                return (deg * type_w) / (dist + 1.0)

            ranked_candidates = sorted(candidate_ids, key=compute_score, reverse=True)

            for oid in ranked_candidates:
                if max_objects and len(selected_object_ids) >= max_objects:
                    hit_max_objects = True
                    break

                obj_tokens = _estimate_subgraph_tokens(self._index[oid])
                if max_tokens and (current_tokens + obj_tokens) > max_tokens:
                    hit_max_tokens = True
                    continue

                selected_object_ids.add(oid)
                current_tokens += obj_tokens
        else:
            selected_object_ids = set(visited_object_ids)

        # Iterate self._index (insertion-ordered) rather than the plain
        # `selected_object_ids` set directly -- the same
        # PYTHONHASHSEED-dependent ordering issue previously fixed in
        # merge() would otherwise resurface here.
        extracted_objects: list[KnowledgeObject] = [
            obj for oid, obj in self._index.items() if oid in selected_object_ids
        ]
        extracted_relations: list[KnowledgeObject] = [
            rel
            for rel in self._relations
            if not (
                include_relation_types
                and rel.relation_type not in include_relation_types
            )
            and all(pid in selected_object_ids for pid in rel.participants)
        ]

        returned_nodes = len(selected_object_ids)
        is_truncated = returned_nodes < total_found_nodes

        truncation_reason: str | None = None
        if hit_max_objects and hit_max_tokens:
            truncation_reason = "max_objects_and_max_tokens_exceeded"
        elif hit_max_objects:
            truncation_reason = "max_objects_exceeded"
        elif hit_max_tokens:
            truncation_reason = "max_tokens_exceeded"

        suggested_next_seed = next(
            (oid for oid in ranked_candidates if oid not in selected_object_ids),
            None,
        )

        return SubgraphResult(
            structure=KnowledgeStructure(extracted_objects + extracted_relations),
            total_found_nodes=total_found_nodes,
            returned_nodes=returned_nodes,
            is_truncated=is_truncated,
            truncation_reason=truncation_reason,
            suggested_next_seed=suggested_next_seed,
        )


# ============================================================================
# Three-Way Merge support types
# ============================================================================


MergeResolution = Union[
    Literal["branch_a", "branch_b"],
    "KnowledgeObject",
    "CanonicalRelation",
    None,
]
"""
Per-identity conflict resolution accepted by
:meth:`KnowledgeStructure.merge`'s ``resolutions`` parameter -- see
its docstring for what each variant means.
"""


@dataclass(frozen=True, slots=True)
class MergeConflict:
    """
    One identity that ``branch_a`` and ``branch_b`` both changed,
    relative to a common ``base``, to different results.

    ``base``, ``branch_a``, and ``branch_b`` hold the object as it
    existed in each structure -- ``None`` means the identity was
    absent there (e.g. ``base=None`` for an id both branches
    introduced independently with different content).
    """

    object_id: str
    base: "KnowledgeObject | None"
    branch_a: "KnowledgeObject | None"
    branch_b: "KnowledgeObject | None"

    def __repr__(self) -> str:
        return f"MergeConflict(object_id={self.object_id!r})"


class MergeConflictError(ValueError):
    """
    Raised by :meth:`KnowledgeStructure.merge` when ``branch_a`` and
    ``branch_b`` changed one or more of the same identities to
    different, irreconcilable results.
    """

    def __init__(self, conflicts: list["MergeConflict"]) -> None:
        self.conflicts = conflicts
        ids = ", ".join(c.object_id for c in conflicts)
        super().__init__(f"Merge conflict on identities: {ids}")


# ============================================================================
# Subgraph Query support types
# ============================================================================


def _estimate_subgraph_tokens(obj: "KnowledgeObject") -> int:
    """
    Rough, fast token estimate for a KnowledgeObject (~1 token per 4
    chars of its identity+structure text), used only to budget
    ``query_subgraph``'s ``max_tokens`` -- not a real tokenizer count,
    and callers must not treat it as one.
    """
    text_repr = (
        f"{obj.identity.id}:{obj.identity.type}:{obj.identity.name}:{obj.structure}"
    )
    return len(text_repr) // 4 + 10


@dataclass(frozen=True, slots=True)
class SubgraphResult:
    """
    Result of :meth:`KnowledgeStructure.query_subgraph`.

    ``structure`` is the extracted, self-contained subgraph (its own
    valid ``KnowledgeStructure`` with a fresh ``root_hash``, no
    dangling relations). The remaining fields describe how it relates
    to the full neighborhood that was actually found, before any
    budget was applied -- without these, a caller has no way to tell
    "this is everything nearby" from "this is a budget-truncated
    slice", which is exactly the ambiguity that leads an LLM agent to
    wrongly conclude a neighborhood ends where the response did.
    """

    #: The extracted subgraph.
    structure: "KnowledgeStructure"

    #: Size of the full neighborhood discovered by BFS, before any
    #: ``max_tokens``/``max_objects`` budget was applied.
    total_found_nodes: int

    #: Number of (non-relation) objects actually present in
    #: ``structure`` -- equal to ``total_found_nodes`` unless
    #: ``is_truncated``.
    returned_nodes: int

    #: Whether a budget cut the neighborhood down from what was found.
    is_truncated: bool

    #: ``None`` when not truncated; otherwise one of
    #: ``"max_objects_exceeded"``, ``"max_tokens_exceeded"``, or
    #: ``"max_objects_and_max_tokens_exceeded"``.
    truncation_reason: str | None

    #: The single highest-ranked node the budget left out, or ``None``
    #: when not truncated. A caller that needs more of the
    #: neighborhood can pass this back in as a seed for a follow-up
    #: ``query_subgraph`` call.
    suggested_next_seed: str | None