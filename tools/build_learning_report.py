#!/usr/bin/env python3
"""Build a machine-readable SNS learning-operations report."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_operations import (  # noqa: E402
    build_enrichment_queue,
    cluster_recipe_reports,
    monitoring_snapshot,
    release_decision,
)
from release_matrix import build_release_matrix_report  # noqa: E402


def _load(path):
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("items") or []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports")
    parser.add_argument("--retail-drafts")
    parser.add_argument("--unmatched-items")
    parser.add_argument("--output", default="test-results/learning-operations.json")
    args = parser.parse_args()

    reports = _load(args.reports)
    clusters = cluster_recipe_reports(reports)
    queue = build_enrichment_queue(
        clusters, _load(args.retail_drafts), _load(args.unmatched_items)
    )
    release_report = build_release_matrix_report()
    result = {
        "schema_version": "learning_operations_v1",
        "monitoring": monitoring_snapshot(reports, clusters, queue),
        "clusters": clusters,
        "enrichment_queue": queue,
        "release_decision": release_decision(release_report, clusters, queue),
        "release_matrix": release_report,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Learning operations report: {output}")
    return 0 if result["release_decision"]["release"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

