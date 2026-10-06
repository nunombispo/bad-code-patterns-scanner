"""Render a scan result as text or JSON."""

from badscan.models import ScanResult
from badscan.report.json import render_json
from badscan.report.text import render_text

__all__ = ["render_json", "render_text"]


def render(result: ScanResult, style: str) -> str:
    if style == "text":
        return render_text(result)
    if style == "json":
        return render_json(result)
    raise ValueError(f"unknown format: {style}")
