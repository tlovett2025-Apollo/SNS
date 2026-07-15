"""Deterministic build and test provenance for generated Stock & Stir meals."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
_SOURCE_SUFFIXES = {".py", ".html", ".css", ".js", ".json", ".toml", ".yaml", ".yml", ".csv"}
_SOURCE_NAMES = {"requirements.txt"}
_EXCLUDED_PARTS = {
    ".git", "__pycache__", ".pytest_cache", "releases", "incoming_release",
    "next_import", "test_plans",
}


def _git_value(args: list[str], root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_metadata(root: Path) -> dict[str, Any]:
    commit = os.getenv("RENDER_GIT_COMMIT") or _git_value(["rev-parse", "HEAD"], root)
    branch = os.getenv("RENDER_GIT_BRANCH") or _git_value(
        ["rev-parse", "--abbrev-ref", "HEAD"], root
    )
    status = _git_value(["status", "--porcelain"], root)
    return {
        "commit": commit[:12] if commit else "unavailable",
        "branch": branch or "unavailable",
        "dirty": bool(status),
    }


def _source_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in _EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in _SOURCE_SUFFIXES or path.name in _SOURCE_NAMES:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _fingerprints(root: Path) -> list[dict[str, str]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:12],
        }
        for path in _source_files(root)
    ]


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def collect_build_provenance(
    runtime_configuration: dict[str, Any] | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return a stable build ID plus exact files and settings for one result."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    git = _git_metadata(root)
    files = _fingerprints(root)
    configuration = {
        str(key): _json_safe(value)
        for key, value in sorted((runtime_configuration or {}).items())
    }
    identity = json.dumps(
        {"git": git, "files": files}, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schema_version": "1.0",
        "build_id": f"SNS-{hashlib.sha256(identity).hexdigest()[:12]}",
        "git": git,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "configuration": configuration,
        "files": files,
    }
