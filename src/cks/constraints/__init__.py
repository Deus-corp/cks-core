from .registry import registry
from .builtin import (
    BUILTIN_CONSTRAINTS,
    OPTIONAL_CONSTRAINTS,
    OPTIONAL_CONSTRAINTS_BY_NAME,
)

for constraint in BUILTIN_CONSTRAINTS:
    registry.register(constraint)

# OPTIONAL_CONSTRAINTS is intentionally NOT auto-registered here.
# It extends the CKS-001 core vocabulary but is not itself part of the
# normative specification, so cks.validate() must keep ignoring it
# until a caller opts in explicitly (see builtin.py for how).

__all__ = [
    "registry",
    "BUILTIN_CONSTRAINTS",
    "OPTIONAL_CONSTRAINTS",
    "OPTIONAL_CONSTRAINTS_BY_NAME",
]
