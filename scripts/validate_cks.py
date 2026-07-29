"""Pre-commit hook: validate CKS JSON files."""
import json
import sys
from pathlib import Path

from cks.serialization import SerializationError
from cks.serialization import parse as cks_parse
from cks.validator import validate as cks_validate

FAILED = False

for path in sys.argv[1:]:
    filepath = Path(path)
    try:
        raw = filepath.read_text(encoding="utf-8")
        structure = cks_parse(raw)
        result = cks_validate(structure)
        if result.is_valid:
            print(f"  ✅ {filepath}")
        else:
            print(f"  ❌ {filepath} ({result.error_count} errors)")
            FAILED = True
    except (SerializationError, json.JSONDecodeError) as exc:
        print(f"  ❌ {filepath}: {exc}")
        FAILED = True

if FAILED:
    sys.exit(1)