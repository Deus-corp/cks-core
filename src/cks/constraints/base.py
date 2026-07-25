from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic
from ..validation import ValidationStage


class Constraint(ABC):
    """
    Canonical validation constraint.
    """

    identity: str

    stage: ValidationStage

    description: str = ""

    @abstractmethod
    def evaluate(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]: ...

    def __call__(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]:
        return self.evaluate(structure)
