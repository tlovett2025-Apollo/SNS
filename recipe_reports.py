"""Validation for user-submitted recipe review reports."""

from __future__ import annotations

import json
from typing import Any


ALLOWED_ISSUE_CATEGORIES = frozenset({
    "recipe_ok",
    "general_review",
    "wrong_ingredients",
    "weird_instructions",
    "uncookable_combination",
    "timing_or_effort",
    "wrong_quantity",
})
ALLOWED_REPORT_OUTCOMES = frozenset({"OK", "NG"})


class RecipeReportError(ValueError):
    """Raised when a recipe report is incomplete or too large."""


def normalize_recipe_report(payload: dict[str, Any]) -> dict[str, Any]:
    recipe = payload.get("recipe_snapshot")
    if not isinstance(recipe, dict) or not recipe:
        raise RecipeReportError("The recipe could not be attached to this report.")

    encoded = json.dumps(recipe, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 200_000:
        raise RecipeReportError("This recipe report is too large to send.")

    candidate_id = str(payload.get("candidate_id") or recipe.get("candidate_id") or "").strip()
    if not candidate_id:
        raise RecipeReportError("The recipe identifier is missing.")

    outcome = str(payload.get("report_outcome") or "NG").strip().upper()
    if outcome not in ALLOWED_REPORT_OUTCOMES:
        raise RecipeReportError("Choose a valid recipe outcome.")

    default_categories = ["recipe_ok"] if outcome == "OK" else ["general_review"]
    requested = payload.get("issue_categories") or default_categories
    if not isinstance(requested, list):
        raise RecipeReportError("Choose a valid reason for the recipe review.")
    categories = list(dict.fromkeys(str(value).strip() for value in requested if str(value).strip()))
    if not categories:
        categories = ["general_review"]
    if len(categories) > 6 or any(value not in ALLOWED_ISSUE_CATEGORIES for value in categories):
        raise RecipeReportError("Choose a valid reason for the recipe review.")
    if outcome == "OK" and categories != ["recipe_ok"]:
        raise RecipeReportError("An OK recipe cannot include problem categories.")
    if outcome == "NG" and "recipe_ok" in categories:
        raise RecipeReportError("A recipe needing review cannot be marked OK.")

    provenance = recipe.get("build_provenance") or {}
    git = provenance.get("git") or {}
    rendered = str(payload.get("rendered_recipe_text") or "").strip()
    note = str(payload.get("user_note") or "").strip()
    if len(rendered) > 50_000:
        rendered = rendered[:50_000]
    if len(note) > 2_000:
        raise RecipeReportError("Please keep the note under 2,000 characters.")

    return {
        "p_candidate_id": candidate_id[:200],
        "p_build_id": str(provenance.get("build_id") or "")[:200],
        "p_commit_id": str(git.get("commit") or "")[:200],
        "p_recipe_snapshot": recipe,
        "p_rendered_recipe_text": rendered,
        "p_user_note": note,
        "p_issue_categories": categories,
        "p_report_outcome": outcome,
    }
