#!/usr/bin/env python3
"""Run every mandatory SNS production gate and emit a JSON audit record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from release_matrix import build_release_matrix_report  # noqa: E402


def _full_suite_gate() -> dict:
    process = subprocess.Popen(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    lines = []
    assert process.stdout is not None
    for line in process.stdout:
        lines.append(line.rstrip("\n"))
        print(line, end="", flush=True)
    return_code = process.wait()
    output = "\n".join(lines)
    count_match = re.search(r"Ran (\d+) tests?", output)
    total = int(count_match.group(1)) if count_match else 0
    failures = []
    if return_code:
        failures.append({
            "case_id": "python-unittest-discover",
            "message": "The automated test suite did not pass.",
            "context": {"return_code": return_code},
        })
    return {
        "name": "full_automated_test_suite",
        "status": "pass" if not failures else "fail",
        "cases": total,
        "passed": total if not failures else 0,
        "failures": failures,
        "result_tail": output.splitlines()[-30:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="test-results/release-gate-report.json",
        help="JSON report path, relative to the repository root by default.",
    )
    parser.add_argument(
        "--matrix-only",
        action="store_true",
        help="Run the catalog/matrix gates without the complete unittest suite.",
    )
    args = parser.parse_args()

    print("[1/4] Checking all launch-pantry knowledge...", flush=True)
    print("[2/4] Running pairwise recipe orchestration...", flush=True)
    print("[3/4] Running boundary and high-risk recipes...", flush=True)
    report = build_release_matrix_report()
    for gate in report["gates"]:
        print(
            f"      {gate['name']}: {gate['status'].upper()} "
            f"({gate['passed']}/{gate['cases']})",
            flush=True,
        )
    if not args.matrix_only:
        print(
            "[4/4] Running the complete automated suite; individual tests follow...",
            flush=True,
        )
        report["gates"].append(_full_suite_gate())
        report["summary"]["gates"] = len(report["gates"])
        report["summary"]["passed_gates"] = sum(
            gate["status"] == "pass" for gate in report["gates"]
        )
        report["summary"]["cases"] = sum(gate["cases"] for gate in report["gates"])
        report["summary"]["failed_cases"] = sum(
            len(gate["failures"]) for gate in report["gates"]
        )
        report["production_ready"] = all(
            gate["status"] == "pass" for gate in report["gates"]
        )

    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    state = "PASS" if report["production_ready"] else "FAIL"
    print(
        f"SNS release gates: {state} — {summary['passed_gates']}/{summary['gates']} "
        f"gates, {summary['cases']} cases, {summary['failed_cases']} failures"
    )
    print(f"Report: {output}")
    if not report["production_ready"]:
        for gate in report["gates"]:
            for failure in gate["failures"]:
                print(f"- {gate['name']} / {failure['case_id']}: {failure['message']}")
                if gate.get("result_tail"):
                    print("\n".join(gate["result_tail"]))
    return 0 if report["production_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
