"""Deterministic production-release coverage for the trained SNS launch surface.

The matrix is intentionally pairwise rather than a meaningless full Cartesian
product.  Every public protein and produce item participates in every trained
public cooking environment, while cuisine, servings, energy, and meal shape
rotate across the pairs.  Named boundary cases cover the combinations most
likely to create a safe-looking but structurally broken recipe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import cycle
from typing import Iterable

from api_service import get_meal_builder_options
from config import DB_PATH
from ko_behavior import default_form_for, resolve_behavior
from recipe_engine import generate_candidates
from sample_pantry_catalog import audit_sample_pantries, audit_summary


METHODS = (
    ("skillet", "White rice", ("Stovetop",)),
    ("soup", "", ("Stovetop",)),
    ("casserole", "Egg noodles", ("Oven",)),
    ("handheld", "Bread", ("Stovetop",)),
    ("grill", "White rice", ("Outdoor Grill",)),
)
CUISINES = ("Comfort Food", "Italian", "Mexican", "BBQ", "Asian")
ENERGIES = ("Very Low", "Low", "Medium", "High")
SERVINGS = (1, 2, 4, 7, 12)


def _failure(case_id: str, message: str, **context) -> dict:
    return {"case_id": case_id, "message": message, "context": context}


def _gate(name: str, total: int, failures: list[dict], **details) -> dict:
    return {
        "name": name,
        "status": "pass" if not failures else "fail",
        "cases": total,
        "passed": total - len(failures),
        "failures": failures,
        **details,
    }


def _pairwise_catalog(options: dict) -> list[tuple[str, str]]:
    proteins = [item["name"] for item in options["proteins"]]
    produce = [item["name"] for item in options["produce"]]
    return list(dict.fromkeys([
        *((name, produce[index % len(produce)]) for index, name in enumerate(proteins)),
        *((proteins[index % len(proteins)], name) for index, name in enumerate(produce)),
    ]))


def _candidate(
    protein: str,
    vegetable: str,
    foundation: str,
    method: str,
    equipment: Iterable[str],
    *,
    protein_form: str,
    vegetable_form: str,
    foundation_form: str = "",
    cuisine: str = "Comfort Food",
    energy: str = "Medium",
    servings: int = 4,
    structure: str = "integrated",
) -> dict | None:
    forms = {protein: protein_form, vegetable: vegetable_form}
    if foundation:
        forms[foundation] = foundation_form or default_form_for(
            foundation, "foundation", DB_PATH
        )
    candidates = generate_candidates(
        protein,
        vegetable,
        foundation,
        cuisine,
        energy,
        "Moderate",
        600,
        servings,
        10,
        vegetable_names=[vegetable],
        protein_state=protein_form,
        requested_method=method,
        available_equipment=list(equipment),
        component_forms=forms,
        meal_structure=structure,
    )
    return next(
        (item for item in candidates if item.get("cooking_method") == method),
        None,
    )


def _run_pairwise(options: dict) -> dict:
    failures = []
    total = 0
    cuisines = cycle(CUISINES)
    energies = cycle(ENERGIES)
    servings_values = cycle(SERVINGS)
    for method, foundation, equipment in METHODS:
        for protein, vegetable in _pairwise_catalog(options):
            protein_form = default_form_for(protein, "protein", DB_PATH) or "Fresh Raw"
            vegetable_form = default_form_for(vegetable, "vegetable", DB_PATH) or "Fresh"
            if (
                resolve_behavior(protein, "protein", protein_form, method, DB_PATH).method is None
                or resolve_behavior(
                    vegetable, "vegetable", vegetable_form, method, DB_PATH
                ).method is None
            ):
                continue
            total += 1
            case_id = f"pair:{method}:{protein}:{vegetable}"
            candidate = _candidate(
                protein,
                vegetable,
                foundation,
                method,
                equipment,
                protein_form=protein_form,
                vegetable_form=vegetable_form,
                cuisine=next(cuisines),
                energy=next(energies),
                servings=next(servings_values),
                structure=("composed_plate" if method == "grill" else "integrated"),
            )
            if not candidate:
                failures.append(_failure(
                    case_id,
                    "No exact production candidate survived orchestration.",
                    method=method,
                    protein=protein,
                    vegetable=vegetable,
                ))
                continue
            validation = candidate.get("recipe_validation") or {}
            if not validation.get("production_ready"):
                failures.append(_failure(
                    case_id,
                    "Candidate failed whole-recipe validation.",
                    errors=validation.get("errors") or [],
                ))
    return _gate("pairwise_orchestration", total, failures)


BOUNDARY_CASES = (
    {
        "id": "frozen-chicken-dry-noodle-casserole",
        "protein": "Chicken breast", "protein_form": "Frozen Raw",
        "vegetable": "Green beans", "vegetable_form": "Canned",
        "foundation": "Egg noodles", "foundation_form": "Dry",
        "method": "casserole", "equipment": ("Oven",),
        "cuisine": "Italian", "energy": "Very Low", "servings": 12,
    },
    {
        "id": "canned-tuna-handheld-one-serving",
        "protein": "Canned tuna", "protein_form": "Canned",
        "vegetable": "Tomatoes", "vegetable_form": "Fresh",
        "foundation": "Bread", "foundation_form": "Shelf-stable",
        "method": "handheld", "equipment": ("Stovetop",),
        "cuisine": "Comfort Food", "energy": "Very Low", "servings": 1,
    },
    {
        "id": "raw-poultry-casserole-four",
        "protein": "Chicken thighs", "protein_form": "Fresh Raw",
        "vegetable": "Broccoli", "vegetable_form": "Fresh",
        "foundation": "White rice", "foundation_form": "Dry",
        "method": "casserole", "equipment": ("Oven",),
        "cuisine": "Comfort Food", "energy": "Low", "servings": 4,
    },
    {
        "id": "frozen-fish-grill-seven",
        "protein": "Salmon", "protein_form": "Frozen Raw",
        "vegetable": "Zucchini", "vegetable_form": "Fresh",
        "foundation": "White rice", "foundation_form": "Dry",
        "method": "grill", "equipment": ("Outdoor Grill",),
        "cuisine": "BBQ", "energy": "High", "servings": 7,
        "structure": "composed_plate",
    },
    {
        "id": "canned-protein-soup-two",
        "protein": "Canned chicken", "protein_form": "Canned",
        "vegetable": "Corn", "vegetable_form": "Canned",
        "foundation": "", "foundation_form": "",
        "method": "soup", "equipment": ("Stovetop",),
        "cuisine": "Mexican", "energy": "Low", "servings": 2,
    },
)


def _run_boundaries() -> dict:
    failures = []
    for case in BOUNDARY_CASES:
        candidate = _candidate(
            case["protein"], case["vegetable"], case["foundation"],
            case["method"], case["equipment"],
            protein_form=case["protein_form"],
            vegetable_form=case["vegetable_form"],
            foundation_form=case["foundation_form"],
            cuisine=case["cuisine"], energy=case["energy"],
            servings=case["servings"],
            structure=case.get("structure", "integrated"),
        )
        if not candidate:
            failures.append(_failure(
                case["id"], "Boundary case produced no production candidate.", **case
            ))
            continue
        validation = candidate.get("recipe_validation") or {}
        if not validation.get("production_ready"):
            failures.append(_failure(
                case["id"], "Boundary recipe was not production ready.",
                errors=validation.get("errors") or [],
            ))
    return _gate("boundary_and_high_risk", len(BOUNDARY_CASES), failures)


def build_release_matrix_report() -> dict:
    pantry = audit_summary(audit_sample_pantries())
    pantry_failures = [
        *[_failure("catalog", "Missing catalog ingredient.", name=name)
          for name in pantry["missing_catalog"]],
        *[_failure("behavior", "Ingredient has no behavior family.", name=name)
          for name in pantry["missing_behavior"]],
        *[_failure("method", "Food role has no public method.", name=name)
          for name in pantry["food_role_without_public_method"]],
    ]
    catalog_gate = _gate(
        "launch_catalog_knowledge",
        pantry["sample_items"],
        pantry_failures,
        resolved_items=pantry["resolved_items"],
        operational_items=pantry["operational_items"],
    )
    options = get_meal_builder_options({"equipment": [{"name": "Outdoor Grill"}]})
    gates = [catalog_gate, _run_pairwise(options), _run_boundaries()]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_ready": all(gate["status"] == "pass" for gate in gates),
        "summary": {
            "gates": len(gates),
            "passed_gates": sum(gate["status"] == "pass" for gate in gates),
            "cases": sum(gate["cases"] for gate in gates),
            "failed_cases": sum(len(gate["failures"]) for gate in gates),
        },
        "gates": gates,
    }

