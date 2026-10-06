"""Machine-readable scan report."""

import json

from badscan.models import ScanResult


def render_json(result: ScanResult) -> str:
    ordered = result.model_copy(
        update={
            "findings": sorted(
                result.findings,
                key=lambda finding: (finding.path, finding.start_line, finding.rule_id),
            )
        }
    )
    return json.dumps(ordered.model_dump(mode="json"), indent=2) + "\n"
