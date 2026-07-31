"""
CLI integration tests.

These tests invoke the `cks` command as a subprocess and verify its
observable behaviour using the reference corpus under `examples/corpus`.
"""

import json
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CORPUS = Path("examples/corpus")
VALID = CORPUS / "valid_theory_example.json"
DANGLING = CORPUS / "invalid_dangling_reference.json"
DUPLICATE = CORPUS / "invalid_duplicate_id.json"
CYCLE = CORPUS / "invalid_derivation_cycle.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["cks", *args],
        capture_output=True,
        check=False,
        text=True,
    )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def test_validate_valid():
    result = _run("validate", str(VALID))
    assert result.returncode == 0
    assert "✅ Valid" in result.stdout


def test_validate_dangling_reference():
    result = _run("validate", str(DANGLING))
    assert result.returncode != 0
    assert "❌ Invalid" in result.stdout
    assert "ERROR" in result.stdout


def test_validate_duplicate_id():
    result = _run("validate", str(DUPLICATE))
    assert result.returncode != 0
    assert "Duplicate" in result.stderr or "Duplicate" in result.stdout


def test_validate_derivation_cycle():
    result = _run("validate", str(CYCLE))
    assert result.returncode != 0
    assert "cycle" in result.stdout.lower()


def test_validate_json_format():
    result = _run("validate", str(VALID), "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["valid"] is True
    assert "constraints_evaluated" in data


def test_validate_output_file(tmp_path):
    out = tmp_path / "report.json"
    result = _run("validate", str(VALID), "--format", "json", "--output", str(out))
    assert result.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["valid"] is True


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------


def test_convert_malformed_turtle_reports_clean_error(tmp_path):
    """
    Regression test: `cks convert` did not catch conversion errors, so
    malformed input crashed with a raw Python traceback instead of a
    clean CLI error message (unlike `validate`/`evolve`/`migrate`).
    """
    bad = tmp_path / "bad.ttl"
    bad.write_text("not valid turtle {{{ ]]] ???")
    result = _run("convert", str(bad), "--format", "turtle")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "Conversion error" in result.stderr


def test_convert_rdf_xml_rejects_doctype(tmp_path):
    """`cks convert --format rdf-xml` refuses a DOCTYPE (billion-laughs
    hardening) with a clean error instead of hanging or crashing."""
    bad = tmp_path / "bomb.rdf"
    bad.write_text(
        '<?xml version="1.0"?>\n'
        "<!DOCTYPE rdf:RDF [\n"
        '  <!ENTITY a "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa">\n'
        '  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        "]>\n"
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">\n'
        '  <rdf:Description rdf:about="http://example.org/thing">\n'
        "    <rdfs:label>&b;</rdfs:label>\n"
        "  </rdf:Description>\n"
        "</rdf:RDF>\n"
    )
    result = _run("convert", str(bad), "--format", "rdf-xml")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "DOCTYPE" in result.stderr


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def test_parse():
    result = _run("parse", str(VALID))
    assert result.returncode == 0
    assert "Objects:" in result.stdout
    assert "Relations:" in result.stdout


# ---------------------------------------------------------------------------
# Inspect
# ---------------------------------------------------------------------------

def test_inspect():
    result = _run("inspect", str(VALID))
    assert result.returncode == 0
    assert "Definition: def-1" in result.stdout
    assert "Theorem: thm-1" in result.stdout


def test_inspect_json():
    result = _run("inspect", str(VALID), "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "objects" in data
    assert "relations" in data


# ---------------------------------------------------------------------------
# Evolve
# ---------------------------------------------------------------------------

def test_evolve_add(tmp_path):
    ops_file = tmp_path / "ops.json"
    ops_file.write_text(
        json.dumps(
            [
                {
                    "type": "add_object",
                    "identity": {"id": "new", "type": "Lemma", "name": "New"},
                    "structure": {},
                }
            ]
        )
    )
    result = _run("evolve", str(VALID), str(ops_file))
    assert result.returncode == 0
    data = json.loads(result.stdout)
    ids = [o["identity"]["id"] for o in data["objects"]]
    assert "new" in ids


def test_evolve_malformed_identity_reports_clean_error(tmp_path):
    """
    Regression test: an operations file with a malformed 'identity'
    (missing a required subfield) used to crash `cks evolve` with a
    raw Python traceback, since parse_operations raised an unprefixed
    TypeError that the CLI's `except ValueError` didn't catch.
    """
    ops_file = tmp_path / "ops.json"
    ops_file.write_text(
        json.dumps(
            [
                {
                    "type": "add_object",
                    "identity": {"id": "x", "type": "Foo"},  # missing 'name'
                    "structure": {},
                }
            ]
        )
    )
    result = _run("evolve", str(VALID), str(ops_file))
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "Invalid operations" in result.stderr


def test_evolve_output_file(tmp_path):
    ops_file = tmp_path / "ops.json"
    ops_file.write_text(
        json.dumps(
            [
                {
                    "type": "add_object",
                    "identity": {"id": "f-out", "type": "Lemma", "name": "Out"},
                    "structure": {},
                }
            ]
        )
    )
    out = tmp_path / "evolved.json"
    result = _run("evolve", str(VALID), str(ops_file), "--output", str(out))
    assert result.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text())
    ids = [o["identity"]["id"] for o in data["objects"]]
    assert "f-out" in ids