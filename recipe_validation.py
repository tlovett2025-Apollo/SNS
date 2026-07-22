"""Final meal-level invariants for generated Stock & Stir recipes."""

from math import ceil
import re

from ingredient_profiles import get_ingredient_profile


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def validate_recipe(candidate: dict, plan_items: list[dict]) -> dict:
    """Return blocking errors and useful warnings after planning, before API output.

    KOs own ingredient facts and the planner owns orchestration. This pass owns
    cross-cutting promises that neither layer can verify alone.
    """
    actions = [
        _clean(item.get("text")) for item in plan_items if item.get("kind") == "action"
    ]
    action_text = " ".join(actions)
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
            rf"\bthaw\w*\b[^.]*\b{escaped_name}\b|\b{escaped_name}\b[^.]*\bthaw\w*\b",
            action_text, re.IGNORECASE,
        ):
            errors.append(f"Fresh {name} received a frozen-only thawing instruction.")
        if state == "frozen raw":
            thaw_pattern = rf"\bthaw\w*\b[^.]*\b{escaped_name}\b|\b{escaped_name}\b[^.]*\bthaw\w*\b|\bdefrost\w*\b[^.]*\b{escaped_name}\b|\b{escaped_name}\b[^.]*\bdefrost\w*\b"
            if re.search(thaw_pattern, action_text, re.IGNORECASE):
                errors.append(f"Frozen {name} thawing appeared inside the timed cooking plan.")
            readiness_pattern = rf"before step 1[^.]*\b(?:thaw\w*|defrost\w*)\b[^.]*\b{escaped_name}\b|before step 1[^.]*\b{escaped_name}\b[^.]*\b(?:thaw\w*|defrost\w*)\b"
            if not re.search(readiness_pattern, all_text, re.IGNORECASE):
                errors.append(f"Frozen {name} has no pre-cook thaw-readiness statement.")

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
        if _key(name) in {_key(item) for item in candidate.get("coherence_omissions") or []}:
            continue
        requirement = next((
            item for item in candidate.get("inventory_requirements") or []
            if isinstance(item, dict) and _key(item.get("name")) == _key(name)
        ), {})
        if requirement.get("status") != "Omit" and name and _key(name) not in _key(action_text):
            errors.append(f"Selected extra {name} has no measured cooking or serving job.")

    # A kitchen-check resolution is authoritative. Instructions may not revert
    # to the unavailable original after promising a substitution or omission.
    for requirement in candidate.get("inventory_requirements") or []:
        if not isinstance(requirement, dict):
            continue
        original = _clean(requirement.get("name"))
        status = _clean(requirement.get("status"))
        resolved = _clean(requirement.get("resolved_name"))
        if status == "Substitute" and original and resolved and _key(original) != _key(resolved):
            if re.search(rf"\b{re.escape(original)}\b", action_text, re.IGNORECASE):
                errors.append(f"Instructions use {original} after the kitchen check substituted {resolved}.")
        if status == "Omit" and original and re.search(
            rf"\b(?:measure|add|stir in|season with|whisk in)\b[^.]*\b{re.escape(original)}\b",
            action_text, re.IGNORECASE,
        ):
            errors.append(f"Instructions use omitted ingredient {original}.")

        effective_name = resolved if status == "Substitute" else original
        # This rule applies to explicit measured requirements. Component rows
        # have an empty quantity, and a consolidated prep heading can mention
        # the component while measuring a different item in the same block.
        if (
            not effective_name
            or not _clean(requirement.get("quantity"))
            or _key(effective_name) in {_key("Water"), _key("Cold water")}
        ):
            continue
        measure_indexes = [
            index for index, text in enumerate(actions)
            if re.search(r"\bmeasure\b", text, re.IGNORECASE)
            and re.search(rf"\b{re.escape(effective_name)}\b", text, re.IGNORECASE)
        ]
        if measure_indexes:
            first_measure = measure_indexes[0]
            if any(
                re.search(rf"\b{re.escape(effective_name)}\b", text, re.IGNORECASE)
                for text in actions[:first_measure]
            ):
                errors.append(f"{effective_name} is used before it is measured or prepared.")

    component_forms = {
        _key(name): _key(form)
        for name, form in (candidate.get("component_forms") or {}).items()
    }
    for name in selected_components:
        if not name:
            continue
        form = component_forms.get(_key(name), "")
        if "canned" not in form and re.search(
            rf"\b{re.escape(name)}\b[^.]*\bwhen canned\b|\bwhen canned\b[^.]*\b{re.escape(name)}\b",
            action_text, re.IGNORECASE,
        ):
            errors.append(f"{name} received canned-form handling even though its selected form is {form or 'not canned'}.")

    foundation = _clean(candidate.get("foundation"))
    if foundation and _key(candidate.get("cooking_method", candidate.get("strategy"))) == "casserole":
        profile = get_ingredient_profile(foundation, "foundation")
        form = component_forms.get(_key(foundation), "")
        if "pasta" in set(profile.behavior_family_codes) and "dry" in form:
            boil_index = next((
                index for index, text in enumerate(actions)
                if _key(foundation) in _key(text) and re.search(r"\bboil\b", text, re.IGNORECASE)
            ), None)
            drain_index = next((
                index for index, text in enumerate(actions)
                if _key(foundation) in _key(text) and re.search(r"\bdrain\b", text, re.IGNORECASE)
            ), None)
            assemble_index = next((
                index for index, text in enumerate(actions)
                if re.search(
                    r"\b(?:arrange|combine)\b[^.]*\b(?:baking dish|dish|casserole)\b",
                    text,
                    re.IGNORECASE,
                )
            ), None)
            if boil_index is None or drain_index is None:
                errors.append(f"Dry {foundation} must be boiled and drained before casserole assembly.")
            elif assemble_index is not None and max(boil_index, drain_index) >= assemble_index:
                errors.append(f"Dry {foundation} is not cooked and drained before casserole assembly.")

    active = int(candidate.get("active_minutes") or 0)
    total = int(candidate.get("minutes") or 0)
    if _key(candidate.get("energy")) == "low" and total and active / total > .7:
        warnings.append("The low-energy label conflicts with a mostly active plan.")

    return {
        "production_ready": not errors,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
    }
