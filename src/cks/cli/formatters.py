"""
CKS CLI — Output Formatters.

Formatters convert validation results and inspection summaries into
machine‑readable (JSON) or human‑readable (Plain Text, HTML, Markdown)
representations.
"""

from __future__ import annotations

import html
import json

from ..result import ValidationResult
from ..diagnostics import DiagnosticSeverity


def format_json(result: ValidationResult, *, indent: int = 2) -> str:
    """Return a JSON string suitable for machine processing."""
    data = {
        "valid": result.is_valid,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "information_count": result.information_count,
        "constraints_evaluated": list(result.evaluated_constraints),
        "diagnostics": [
            {
                "identity": d.identity,
                "severity": d.severity.value,
                "message": d.message,
                "location": d.location,
            }
            for d in result.diagnostics
        ],
    }
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_text(result: ValidationResult) -> str:
    """Return a human‑readable plain‑text summary."""
    lines = []
    if result.is_valid:
        lines.append("✅ Valid")
    else:
        lines.append("❌ Invalid")
        for d in result.diagnostics:
            prefix = {
                DiagnosticSeverity.ERROR: "  [ERROR]",
                DiagnosticSeverity.WARNING: "  [WARN] ",
                DiagnosticSeverity.INFORMATION: "  [INFO] ",
            }.get(d.severity, "  [????]")
            lines.append(f"{prefix} {d.message}")
    lines.append(
        f"\nErrors: {result.error_count}  "
        f"Warnings: {result.warning_count}  "
        f"Info: {result.information_count}"
    )
    return "\n".join(lines)


def format_html(result: ValidationResult) -> str:
    """Return a minimal HTML report."""
    status = "✅ Valid" if result.is_valid else "❌ Invalid"
    rows = []
    for d in result.diagnostics:
        rows.append(
            f"<tr>"
            f"<td>{html.escape(d.identity)}</td>"
            f"<td>{d.severity.value}</td>"
            f"<td>{html.escape(d.message)}</td>"
            f"<td>{html.escape(d.location or '')}</td>"
            f"</tr>"
        )
    diag_table = (
        "<table border='1'>"
        "<tr><th>Identity</th><th>Severity</th><th>Message</th><th>Location</th></tr>"
        + "".join(rows)
        + "</table>"
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>CKS Validation Report</title></head>
<body>
<h1>{status}</h1>
<p>Errors: {result.error_count} Warnings: {result.warning_count} Info: {result.information_count}</p>
{diag_table}
</body>
</html>"""


def format_markdown(result: ValidationResult) -> str:
    """Return a Markdown report."""
    lines = [
        f"## {'✅ Valid' if result.is_valid else '❌ Invalid'}",
        "",
        "| Severity | Identity | Message | Location |",
        "|----------|----------|---------|----------|",
    ]
    for d in result.diagnostics:
        lines.append(
            f"| {d.severity.value} | {d.identity} | {d.message} | {d.location or ''} |"
        )
    lines.append("")
    lines.append(
        f"Errors: {result.error_count}  "
        f"Warnings: {result.warning_count}  "
        f"Info: {result.information_count}"
    )
    return "\n".join(lines)