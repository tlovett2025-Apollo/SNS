"""Final meal-level invariants for generated Stock & Stir recipes."""

from math import ceil
import re


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def validate_recipe(candidate: dict, plan_items: list[dict]) -> dict:
    """Return blocking errors and useful warnings after planning, before API output.

    KOs own ingredient facts and the planner owns orchestration. This pass owns
    cross-cutting promises that neither layer can verify alone.
    """
    action_text = " ".join(
        _clean(item.get("text")) for item in plan_items if item.get("kind") == "action"
    )
    all_text = " ".join(_clean(item.get("text")) for item in plan_items)
    lowered = all_text.lower()
    errors = []
    warnings = []

    if re.search(r"\bKO(?:-approved)?\b|knowledge object", all_text, re.IGNORECASE):
        errors.append("Internal KO terminology reached the customer recipe.")

    for spec in candidate.get("proteins") or []:
        if not isinstance(spec, dict):
            continue
        name = _clean(spec.get("name"))
        state = _key(spec.get("state"))
        escaped_name = re.escape(name)
        if state == "fresh raw" and re.search(
            rf"\bthaw\b[^.]*\b{escaped_name}\b|\b{escaped_name}\b[^.]*\bthaw\b",
            action_text, re.IGNORECASE,
        ):
            errors.append(f"Fresh {name} received a frozen-only thawing instruction.")

        role = _key(spec.get("role"))
        if role in {"supporting", "accent"}:
            planned = (candidate.get("quantity_plan") or {}).get(_key(name), {})
            display = _clean(planned.get("display"))
            match = re.match(r"(\d+(?:\.\d+)?)\s+(?:piece|pieces|strip|strips|egg|eggs)", display)
            if match:
                factor = .5 if role == "accent" else .25
                allowed = max(1, ceil(float(candidate.get("effective_portions") or 4) * factor))
                if float(match.group(1)) > allowed:
                    errors.append(f"Supporting protein {name} was portioned as a second entree.")

    selected_components = [
        *[_clean(item.get("name")) for item in candidate.get("proteins") or [] if isinstance(item, dict)],
        *[part.strip() for part in _clean(candidate.get("vegetable")).split(" & ") if part.strip()],
        _clean(candidate.get("foundation")),
    ]
    for name in selected_components:
        if name and _key(name) not in _key(action_text):
            errors.append(f"Selected component {name} has no job in the cooking instructions.")

    for name in candidate.get("selected_extras") or []:
        name = _clean(name)
        requirement = next((
            item for item in candidate.get("inventory_requirements") or []
            if isinstance(item, dict) and _key(item.get("name")) == _key(name)
        ), {})
        if requirement.get("status") != "Omit" and name and _key(name) not in _key(action_text):
            errors.append(f"Selected extra {name} has no measured cooking or serving job.")

    active = int(candidate.get("active_minutes") or 0)
    total = int(candidate.get("minutes") or 0)
    if _key(candidate.get("energy")) == "low" and total and active / total > .7:
        warnings.append("The low-energy label conflicts with a mostly active plan.")

    return {
        "production_ready": not errors,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
    }
