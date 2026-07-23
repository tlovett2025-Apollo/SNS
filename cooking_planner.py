"""
Cooking Timeline Engine for Stock & Stir / SNS.

This module turns a selected recipe candidate into ordered cooking steps.
It is intentionally practical and conservative: first make the engine work,
then deepen the cooking intelligence as more CKB fields become available.
"""

from dataclasses import dataclass, field
from math import ceil
import re
from datetime import date
from typing import Dict, List, Optional
from ingredient_profiles import KitchenActivity, get_ingredient_profile, ingredient_relationships
from ko_behavior import resolve_behavior
from config import DB_PATH
from equipment_profiles import (
    build_rice_equipment_activities,
    choose_braise_equipment,
    choose_rice_equipment,
)
from meal_components import component_by_archetype
from side_archetypes import side_activity_instruction
from sauce_profiles import get_sauce_profile
from flavor_identity import ingredient_affinity_status
from planner_voice import (
    activity_message,
    completion_message,
    meal_introduction,
    transition_message,
)


@dataclass
class CookingStep:
    order: int
    phase: str
    instruction: str
    minutes: Optional[int] = None
    parallel_ok: bool = False

@dataclass
class TimelineBlock:
    stage: int
    steps: List[CookingStep]

def _clean(value):
    return "" if value is None else str(value).strip()


def _strategy(candidate):
    return _clean((candidate or {}).get("strategy") or (candidate or {}).get("cooking_method")) or "plate"

def _join(items):
    cleaned = []
    for item in items:
        item = _clean(item)
        if item and item not in cleaned:
            cleaned.append(item)
    if not cleaned:
        return "the meal components"
    if len(cleaned) == 1:
        return cleaned[0]
    return " & ".join(cleaned)


def _steam_side_vegetables(candidate: dict) -> List[str]:
    """Return selected vegetables that can share a covered steaming vessel."""
    return [
        name for name in _split_joined_items(candidate.get("vegetable"))
        if "steam-friendly" in set(
            get_ingredient_profile(name, "vegetable").physical_traits
        )
    ]


def _extras_instruction(candidate: dict, strategy: str, phase: str = "finish") -> str:
    """Give every user-selected pantry/fridge extra an explicit job."""
    sauce_profile = get_sauce_profile(_clean(candidate.get("sauce")))
    sauce_keys = {
        _clean(item.name).lower() for item in (sauce_profile.ingredients if sauce_profile else [])
    }
    for sauce_item in (sauce_profile.ingredients if sauce_profile else []):
        resolved = _resolved_requirement_name(candidate, sauce_item.name)
        if resolved:
            sauce_keys.add(resolved.lower())
    extras = [
        _clean(item) for item in candidate.get("selected_extras") or [] if _clean(item)
        and _clean(item).lower() not in sauce_keys
        and _clean(item).lower() != _clean(candidate.get("soup_liquid")).lower()
    ]
    cuisine = _clean(candidate.get("cuisine")).lower()
    incompatible = []
    for item in extras:
        affinity = _clean(resolve_behavior(
            item, "ingredient", db_path=DB_PATH
        ).attributes.get("cuisine_affinity"))
        allowed = [_clean(value) for value in affinity.split(",") if _clean(value)]
        if ingredient_affinity_status(cuisine, allowed) == "conflicting":
            incompatible.append(item)
    if incompatible:
        omissions = candidate.setdefault("coherence_omissions", [])
        for item in incompatible:
            if item not in omissions:
                omissions.append(item)
        extras = [item for item in extras if item not in incompatible]
    if not extras:
        return ""
    family_codes = {
        item: set(get_ingredient_profile(item, "ingredient").behavior_family_codes)
        for item in extras
    }
    has_side_cheese = any("melting_cheese" in family_codes[item] for item in extras)
    reserved_for_vegetable_side = {
        item for item in extras
        if _clean(candidate.get("meal_structure")) == "composed_plate"
        and _steam_side_vegetables(candidate)
        and (
            "melting_cheese" in family_codes[item]
            or (has_side_cheese and "milk_cream" in family_codes[item])
        )
    }
    table_families = (
        {"cultured_creamy"}
        if strategy == "soup"
        else {"prepared_condiment", "cultured_creamy"}
    )
    table = [
        item for item in extras
        if family_codes[item] & table_families
    ]
    cooking = [
        item for item in extras
        if item not in table and item not in reserved_for_vegetable_side
        and not (strategy == "skillet" and "cooking_fat" in family_codes[item])
    ]
    parts = []
    if strategy == "handheld":
        return f"Spread, spoon, or layer {_join(extras)} into the handheld during assembly."
    if strategy == "soup":
        if phase == "build" and cooking:
            parts.append(f"Stir {_join(cooking)} into the cooking liquid before the long simmer.")
        if phase == "finish" and table:
            parts.append(f"Take the pot off the heat, then serve {_join(table)} on top or alongside.")
    elif strategy == "casserole":
        if cooking:
            parts.append(f"Mix in {_join(cooking)} before baking.")
        if table:
            parts.append(f"Serve {_join(table)} on top or alongside after baking.")
    else:
        if cooking:
            parts.append(f"Stir {_join(cooking)} into the skillet as the sauce finishes.")
        if table:
            parts.append(f"Serve {_join(table)} on top or alongside the finished meal.")
    return " ".join(parts)

def _foundation_step(foundation: str, strategy: str) -> Optional[CookingStep]:
    if not foundation:
        return None

    if strategy in {"quick_bowl", "casserole", "plate"}:
        instruction = f"Start or prepare {foundation} first so it is ready when the protein and vegetables are done."
    elif strategy == "soup":
        instruction = f"Prepare {foundation} only if it needs a head start before being added to the soup."
    elif strategy == "handheld":
        instruction = f"Prepare {foundation} as a side or filling support if it belongs with the handheld meal."
    else:
        instruction = f"Prepare {foundation} early if it needs simmering, baking, boiling, or resting time."

    return CookingStep(
        order=20,
        phase="foundation",
        instruction=instruction,
        minutes=15,
        parallel_ok=True,
    )

def _split_joined_items(value: str) -> list:
    value = _clean(value)
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(" & ")
        if item.strip()
    ]


def _requirement(candidate: dict, name: str) -> dict:
    wanted = _clean(name).lower()
    return next((
        item for item in candidate.get("inventory_requirements") or []
        if isinstance(item, dict) and _clean(item.get("name")).lower() == wanted
    ), {})


def _resolved_requirement_name(candidate: dict, name: str) -> str:
    requirement = _requirement(candidate, name)
    if requirement.get("status") in {"Have", "Need"}:
        return _clean(requirement.get("name"))
    if requirement.get("status") == "Substitute":
        return _clean(requirement.get("resolved_name"))
    return ""


def _resolved_requirements_by_ko(candidate: dict, family_codes=(), functions=()) -> list[str]:
    wanted_families = set(family_codes)
    wanted_functions = set(functions)
    matches = []
    for requirement in candidate.get("inventory_requirements") or []:
        if not isinstance(requirement, dict) or requirement.get("status") not in {"Have", "Need", "Substitute"}:
            continue
        name = _clean(requirement.get("resolved_name") or requirement.get("name"))
        if not name:
            continue
        profile = get_ingredient_profile(name, "ingredient")
        if wanted_families & set(profile.behavior_family_codes) or wanted_functions & set(profile.culinary_functions):
            matches.append(name)
    return list(dict.fromkeys(matches))


def _comfort_sauce_prep(candidate: dict, fallback: str) -> str:
    """Prepare only ingredients that survived the kitchen eligibility gate."""
    if not candidate.get("inventory_requirements"):
        return fallback

    instructions = []
    seasonings = _resolved_requirements_by_ko(
        candidate, family_codes=("dry_seasoning", "salt_seasoning")
    )
    if seasonings:
        instructions.append(f"Measure {_join(seasonings)}.")

    broth = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("broth_liquid",))), "")
    milk = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("milk_cream",))), "")
    if broth and milk and broth.lower() != milk.lower():
        instructions.append(f"Whisk the {broth} and {milk} together.")
    elif broth and milk:
        instructions.append(f"Measure 1 cup {broth} for the pan sauce.")
    elif broth or milk:
        instructions.append(f"Measure {(broth or milk)} for the pan sauce.")

    thickener = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("thickener",))), "")
    if thickener:
        instructions.append(
            f"In a small cup, stir the {thickener} with 1 tablespoon cold water until smooth."
        )
    return " ".join(instructions)


def _resolved_sauce_prep(candidate: dict, sauce_profile) -> str:
    """Measure only the sauce ingredients the kitchen check approved."""
    if not sauce_profile:
        return ""
    measurements = []
    for ingredient in sauce_profile.ingredients:
        requirement = _requirement(candidate, ingredient.name)
        if requirement and requirement.get("status") == "Omit":
            continue
        name = _clean(
            requirement.get("resolved_name")
            if requirement.get("status") == "Substitute"
            else requirement.get("name")
        ) if requirement else ingredient.name
        quantity = _clean(requirement.get("quantity")) if requirement else ingredient.quantity
        if "lime" in name.lower() and "lemon" in quantity.lower():
            quantity = re.sub(r"\blemons?\b", "lime", quantity, flags=re.IGNORECASE)
        elif "lemon" in name.lower() and "lime" in quantity.lower():
            quantity = re.sub(r"\blimes?\b", "lemon", quantity, flags=re.IGNORECASE)
        if not name or not quantity or "to taste" in quantity.lower() or "after tasting" in quantity.lower():
            continue
        singular_name = name.rstrip("s").lower()
        measurements.append(
            f"Measure {quantity}."
            if singular_name and singular_name in quantity.lower()
            else f"Measure {quantity} {name}."
        )
    return " ".join(measurements)


def _resolved_sauce_finish(candidate: dict, sauce_profile) -> str:
    instruction = sauce_profile.cook_instruction if sauce_profile else ""
    for ingredient in sauce_profile.ingredients if sauce_profile else []:
        requirement = _requirement(candidate, ingredient.name)
        if not requirement or requirement.get("status") != "Substitute":
            continue
        original = ingredient.name.rstrip("s")
        resolved = _clean(requirement.get("resolved_name")).rstrip("s")
        if original and resolved:
            instruction = re.sub(
                rf"\b{re.escape(original)}s?\b", resolved.lower(), instruction,
                flags=re.IGNORECASE,
            )
    return instruction


def _resolved_braise_sauce_prep(candidate: dict, sauce_profile) -> str:
    """Preserve useful braise mixing guidance without reviving omitted items."""
    if not sauce_profile or sauce_profile.name != "BBQ Sauce":
        return _resolved_sauce_prep(candidate, sauce_profile)

    broth = next(iter(_resolved_requirements_by_ko(
        candidate, family_codes=("broth_liquid",)
    )), "") or _resolved_requirement_name(candidate, "Broth or water") or "broth or water"
    parts = [
        f"Measure 1 1/2 cups {broth}.",
        f"Whisk 1/2 cup BBQ sauce with 1 cup of it; reserve the remaining 1/2 cup to adjust the liquid level during the braise.",
    ]

    approved = {}
    for ingredient in sauce_profile.ingredients:
        requirement = _requirement(candidate, ingredient.name)
        if requirement and requirement.get("status") == "Omit":
            continue
        resolved = _clean(
            requirement.get("resolved_name")
            if requirement and requirement.get("status") == "Substitute"
            else requirement.get("name") if requirement else ingredient.name
        )
        if resolved:
            approved[ingredient.name.lower()] = resolved

    condiments = [
        ("worcestershire sauce", "1 tablespoon"),
        ("mustard", "1 tablespoon"),
        ("ketchup", "2 tablespoons"),
    ]
    selected_condiments = [
        (approved[key], quantity) for key, quantity in condiments if key in approved
    ]
    seasonings = [
        approved[key] for key in ("garlic powder", "onion powder", "black pepper")
        if key in approved
    ]
    additions = []
    if selected_condiments:
        additions.append(" and ".join(
            f"{quantity} {name}" for name, quantity in selected_condiments
        ))
    if seasonings:
        additions.append(f"the measured {_join(seasonings)}")
    if additions:
        parts.append(f"Add {' plus '.join(additions)}.")
    return " ".join(parts)


def _comfort_sauce_finish(candidate: dict, fallback: str) -> str:
    """Finish the sauce without instructing the cook to use rejected items."""
    if not candidate.get("inventory_requirements"):
        return fallback

    broth = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("broth_liquid",))), "")
    milk = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("milk_cream",))), "")
    liquids = _join([broth, milk])
    acidic_vegetable = any(
        "acidic" in set(get_ingredient_profile(name, "vegetable").physical_traits)
        for name in _split_joined_items(candidate.get("vegetable"))
    )
    if milk and acidic_vegetable:
        parts = [
            f"Add {broth or 'the broth'} to the skillet and scrape up the browned flavor.",
            "Bring it to a gentle simmer, then reduce the heat to low.",
            f"Stir in {milk} gradually without letting the sauce boil; gentle heat helps it stay smooth around the tomatoes.",
        ]
    elif milk:
        parts = [
            f"Add {liquids or 'the prepared liquid'} to the skillet and scrape up the browned flavor.",
            "Bring it to a gentle simmer, then reduce the heat; do not boil after the milk is added.",
        ]
    else:
        parts = [
            f"Add {liquids or 'the prepared liquid'} to the skillet and scrape up the browned flavor.",
            "Bring it to a gentle simmer.",
        ]
    thickener = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("thickener",))), "")
    if thickener:
        parts.append(
            f"Stir the {thickener} mixture again, add it gradually, and stir until the sauce lightly coats everything in the skillet."
        )
    else:
        parts.append("Stir until everything is hot and coated with the loose, spoonable pan sauce.")
    if _resolved_requirements_by_ko(candidate, family_codes=("salt_seasoning",)):
        parts.append("Taste before adding salt; add only what is needed.")
    else:
        parts.append("Taste the sauce; the broth may already provide enough seasoning.")
    return " ".join(parts)

def _vegetable_guidance_steps(vegetable: str, strategy: str) -> List[CookingStep]:
    vegetables = _split_joined_items(vegetable)
    steps = []

    staged = []

    for veg in vegetables:
        profile = get_ingredient_profile(veg, "vegetable")
        staged.append((veg, profile))

    stage_order = {
        "early": 0,
        "middle": 1,
        "late": 2,
    }

    staged.sort(
        key=lambda item: stage_order.get(
            getattr(item[1], "add_stage", "middle"),
            1,
        )
    )

    for index, (veg, profile) in enumerate(staged):
       if profile:
            instruction = profile.cook_instruction(strategy)
            note = profile.finish_note()
            if note:
                instruction = f"{instruction} {note}"
            else:
                instruction = f"Cook {veg} until it reaches the texture you like."
            steps.append(CookingStep(
                order=40 + index,
                phase="vegetable",
                instruction=instruction,
                minutes=profile.total_active_minutes if profile else 8,
                parallel_ok=profile.parallel_ok if profile else True,
        ))

    return steps

def _protein_guidance_step(protein: str, strategy: str, state_name: str = "Fresh Raw") -> Optional[CookingStep]:
    protein = _clean(protein)
    if not protein:
        return None

    profile = get_ingredient_profile(protein, "protein")

    if profile:
        state_name = _clean(state_name) or "Fresh Raw"
        if state_name == "Frozen Raw":
            instruction = (
                f"Cook {protein} from frozen using a covered or moist method. "
                "Allow extra time and verify that the thickest part is safely cooked through."
            )
        elif state_name == "Cooked":
            instruction = f"Slice, shred, or dice {protein}, then reheat it gently until hot."
        else:
            instruction = profile.cook_instruction(strategy)

        note = profile.finish_note()
        if note:
            instruction = f"{instruction} {note}"

        return CookingStep(
            order=30,
            phase="protein",
            instruction=instruction,
            minutes=profile.total_active_minutes,
            parallel_ok=profile.parallel_ok,
        )

    return CookingStep(
        order=30,
        phase="protein",
        instruction=f"Cook {protein} until safe and ready.",
        minutes=12,
        parallel_ok=False,
    )

def _vegetable_stage_instruction(vegetable: str, strategy: str) -> str:
    profile = get_ingredient_profile(vegetable, "vegetable")

    if profile and profile.timing_note:
        return profile.cook_instruction(strategy) + " " + profile.timing_note

    return (
        f"Add {vegetable} based on how well it holds: "
        "start sturdy vegetables first, add quick-cooking or wilting vegetables near the end, "
        "and keep tender vegetables close to serving time."
    )

def build_timeline_blocks(steps: List[CookingStep]) -> List[TimelineBlock]:
    """
    Group cooking steps into timeline blocks.

    Heat 1 teaches the planner that compatible steps can overlap.
    This does not assign clock times yet.
    """

    blocks: List[TimelineBlock] = []

    for step in sorted(steps, key=lambda s: s.order):
        placed = False

        if step.parallel_ok:
            for block in blocks:
                if all(existing.parallel_ok for existing in block.steps):
                    block.steps.append(step)
                    placed = True
                    break

        if not placed:
            blocks.append(TimelineBlock(
                stage=len(blocks) + 1,
                steps=[step],
            ))

    return blocks

def _planner_activity(activity_type, instruction, minutes=None, human_busy=True, stage="middle", depends_on=None, equipment="counter"):
    """Create a meal-level orchestration activity owned by the planner."""

    return KitchenActivity(
        component="meal",
        activity_type=activity_type,
        instruction=instruction,
        minutes=minutes,
        human_busy=human_busy,
        stage=stage,
        parallel_ok=False,
        depends_on=list(depends_on or []),
        source="planner",
        equipment=equipment,
        activity_id=f"{activity_type}:meal",
    )


def _ready_to_eat_state(value) -> bool:
    return _clean(value).lower() in {
        "canned", "cooked", "ready to eat", "ready-to-eat",
    }


def build_cooking_activities(candidate: dict) -> List[KitchenActivity]:
    """Collect KO-published activities and add only meal-level orchestration."""

    protein = _clean(candidate.get("protein"))
    protein_specs = [
        item for item in candidate.get("proteins") or []
        if isinstance(item, dict) and _clean(item.get("name"))
    ] or [{"name": protein, "state": _clean(candidate.get("protein_state")) or "Fresh Raw", "role": "main"}]
    protein_names = [_clean(item.get("name")) for item in protein_specs]
    vegetables = _split_joined_items(candidate.get("vegetable"))
    foundation = _clean(candidate.get("foundation"))
    strategy = _strategy(candidate)
    protein_state = _clean(candidate.get("protein_state")) or "Fresh Raw"
    component_forms = {
        _clean(name).lower(): _clean(form)
        for name, form in (candidate.get("component_forms") or {}).items()
    }
    sauce = _clean(candidate.get("sauce")) or "simple sauce"
    sauce_profile = get_sauce_profile(sauce)
    components = [item for item in [*protein_names, *vegetables, foundation] if item]

    activities: List[KitchenActivity] = [
        _planner_activity(
            "gather",
            f"Gather the ingredients and equipment for {_join(components)}.",
            minutes=0,
            human_busy=False,
            stage="early",
            equipment="counter",
        )
    ]

    if foundation:
        activities.extend(
            get_ingredient_profile(foundation, "foundation").publish_activities(
                strategy, component_forms.get(foundation.lower(), "")
            )
        )
    for item in protein_specs:
        name = _clean(item.get("name"))
        state = _clean(item.get("state")) or (protein_state if name == protein else "Fresh Raw")
        published = get_ingredient_profile(name, "protein").publish_activities(strategy, state)
        if (
            name.lower() == "chicken breast"
            and ("thin" in state.lower() or "cutlet" in state.lower())
        ):
            for activity in published:
                if activity.activity_type == "cook" and strategy == "skillet":
                    activity.minutes = 8
                    activity.active_minutes = min(int(activity.active_minutes or 0), 5)
                    activity.instruction = (
                        "Cook the 1/2-inch chicken breast slices in a single layer for "
                        "about 3–4 minutes on the first side and 2–4 minutes after turning. "
                        "Stop when the thickest slice reaches 165°F; remove finished slices "
                        "individually rather than overcooking the whole batch."
                    )
                elif activity.activity_type == "prep":
                    activity.instruction = (
                        "Do not rinse the thin-sliced chicken breast. Pat it dry and "
                        "season both sides; no pounding or thickness-evening is needed."
                    )
        activities.extend(published)
    for vegetable in vegetables:
        activities.extend(
            get_ingredient_profile(vegetable, "vegetable").publish_activities(
                strategy, component_forms.get(vegetable.lower(), "")
            )
        )

    selected_keys = {_clean(item).lower() for item in components}
    for lot in candidate.get("inventory_lots") or []:
        if not isinstance(lot, dict) or _clean(lot.get("name")).lower() not in selected_keys:
            continue
        form = _clean(lot.get("form")).lower()
        unit = _clean(lot.get("unit")).lower()
        quantity = float(lot.get("quantity") or 0)
        opened_at = _clean(lot.get("opened_at"))
        is_opened_can = bool(opened_at) or (unit in {"can", "cans"} and quantity % 1 != 0)
        if not is_opened_can or not ("canned" in form or unit in {"can", "cans"}):
            continue
        name = _clean(lot.get("name"))
        item_profile = get_ingredient_profile(name, "vegetable")
        high_acid = "acidic" in set(item_profile.physical_traits)
        limit = 7 if high_acid else 4
        age = None
        try:
            age = (date.today() - date.fromisoformat(opened_at)).days if opened_at else None
        except ValueError:
            age = None
        refrigerated = lot.get("refrigerated_after_opening")
        if refrigerated is False:
            instruction = f"Do not use the opened {name}; it was not refrigerated promptly. Choose another can or a substitution."
        elif age is not None and age > limit:
            instruction = f"Do not use the opened {name}; it has been refrigerated for {age} days, beyond the {limit}-day window for this food."
        elif age is None:
            instruction = (
                f"Before using the opened {name}, confirm when it was opened and that it was refrigerated promptly. "
                f"Use it only within {limit} refrigerated days. Discard it for mold, discoloration, an unusual odor, or if you are unsure; appearance and smell alone cannot prove safety."
            )
        else:
            instruction = (
                f"The opened {name} is recorded as {age} day{'s' if age != 1 else ''} old. Confirm it stayed refrigerated. "
                "Discard it for mold, discoloration, or an unusual odor; passing that check does not replace the storage-time limit."
            )
        check_id = f"check opened can:{name}"
        activities.append(_planner_activity(
            "check opened can", instruction, minutes=1, human_busy=True,
            stage="early", depends_on=["gather:meal"], equipment="counter",
        ))
        activities[-1].component = name
        activities[-1].activity_id = check_id
        for activity in activities:
            if activity.component == name and activity.activity_type == "prep" and check_id not in activity.depends_on:
                activity.depends_on.append(check_id)

    component_finishes = [
        f"{activity.activity_type}:{activity.component}"
        for activity in activities
        if activity.source == "ko" and activity.stage in {"middle", "late", "finish"}
    ]

    ko_activities = [activity for activity in activities if activity.source == "ko"]
    if strategy == "skillet" and protein:
        seasoning_names = _resolved_requirements_by_ko(
            candidate, family_codes=("dry_seasoning", "salt_seasoning")
        )
        selected_fat = next((
            _clean(item) for item in candidate.get("selected_extras") or []
            if "cooking_fat" in set(get_ingredient_profile(_clean(item), "ingredient").behavior_family_codes)
        ), "")
        prep_activity = next((
            activity for activity in ko_activities
            if activity.component == protein and activity.activity_type == "prep"
        ), None)
        cook_activity = next((
            activity for activity in ko_activities
            if activity.component == protein and activity.activity_type == "cook"
        ), None)
        if prep_activity and seasoning_names:
            prep_activity.instruction = (
                prep_activity.instruction.rstrip(". ")
                + f". Season with {_join(seasoning_names)}."
            )
        if cook_activity and selected_fat:
            cook_activity.instruction = f"Heat {selected_fat} in the skillet. {cook_activity.instruction}"
    if _clean(candidate.get("meal_structure")) == "composed_plate":
        for activity in ko_activities:
            if activity.component == foundation and activity.activity_type in {"cook", "reheat", "warm"}:
                activity.instruction = (
                    f"{activity.instruction} Keep it separate from the protein cooking vessel so each component retains its own texture."
                )
    referenced = {
        dependency
        for activity in ko_activities
        for dependency in activity.depends_on
    }

    def terminal_ids(component_names):
        names = set(component_names)
        return [
            _activity_id(activity)
            for activity in ko_activities
            if activity.component in names and _activity_id(activity) not in referenced
        ]

    if strategy in {"braise", "oven_braise"}:
        # A braise is one shared cooking environment. Ingredient KOs still own
        # handling knowledge, but supporting proteins and vegetables join the
        # main braise in form-aware stages instead of becoming parallel entrees.
        state_changes = [activity for activity in ko_activities if activity.activity_type == "thaw"]
        prep_activities = [activity for activity in ko_activities if activity.activity_type == "prep"]
        finish_components = []
        early_vegetables = []
        staged_vegetables = []
        for name in vegetables:
            profile = get_ingredient_profile(name, "vegetable")
            traits = set(profile.behavior_traits) | set(profile.physical_traits)
            if "finish-only-default" in traits or profile.add_stage == "finish":
                finish_components.append(name)
            elif "flavor-builder" in set(profile.culinary_functions):
                early_vegetables.append(name)
            else:
                behavior = resolve_behavior(
                    name, "vegetable", component_forms.get(name.lower(), "Fresh"),
                    strategy, DB_PATH,
                )
                cook_minutes = max(5, min(45, int(
                    getattr(behavior.method, "cook_minutes", 15) or 15
                )))
                staged_vegetables.append((name, cook_minutes))

        supporting = protein_specs[1:]
        raw_supporting = [
            _clean(item.get("name")) for item in supporting
            if _clean(item.get("state")).lower() not in {"cooked", "canned", "ready to eat"}
        ]
        ready_supporting = [
            _clean(item.get("name")) for item in supporting
            if _clean(item.get("state")).lower() in {"cooked", "canned", "ready to eat"}
        ]
        for activity in prep_activities:
            activity.instruction = (
                activity.instruction
                .replace("on this stovetop schedule", "on this braising schedule")
                .replace("for a skillet meal", "for the braise")
            )
            if activity.component in raw_supporting:
                activity.instruction = (
                    f"Leave {activity.component} whole so it cooks evenly and its center can be checked before slicing."
                )
        activities = [activities[0], *state_changes, *prep_activities]
        prep_ids = [_activity_id(activity) for activity in prep_activities]
        main_prep = next((item for item in prep_ids if item.endswith(f":{protein}")), "gather:meal")
        braise_device = (
            choose_braise_equipment(
                candidate.get("available_equipment") or [], candidate.get("max_time_minutes") or 0
            )
            if strategy == "braise" else "oven"
        )
        heat_equipment = {
            "pressure cooker": "pressure cooker",
            "slow cooker": "slow cooker",
            "dutch oven": "burner",
            "stovetop": "burner",
            "oven": "oven",
        }[braise_device]

        sauce_profile = get_sauce_profile(sauce)
        if sauce_profile:
            sauce_prep = _resolved_braise_sauce_prep(candidate, sauce_profile)
            selected_broth = next((
                _clean(item) for item in candidate.get("selected_extras") or []
                if "broth_liquid" in set(get_ingredient_profile(_clean(item), "ingredient").behavior_family_codes)
            ), "") or _resolved_requirement_name(candidate, "Broth or water")
            if selected_broth:
                sauce_prep = sauce_prep.replace("broth or water", selected_broth)
            activities.append(_planner_activity(
                "mix braising sauce", sauce_prep,
                minutes=max(2, sauce_profile.prep_minutes), human_busy=True,
                stage="early", depends_on=prep_ids or ["gather:meal"], equipment="counter",
            ))
            brown_dependencies = ["mix braising sauce:meal"]
        else:
            brown_dependencies = [main_prep]

        selected_fat = _resolved_requirement_name(candidate, "Cooking oil or butter")
        fat_text = (
            f"Add 1 tablespoon {selected_fat}"
            if selected_fat and _clean(selected_fat).lower() != "cooking oil or butter"
            else "Add 1 tablespoon cooking oil or butter"
        )
        activities.append(_planner_activity(
            "brown main protein",
            (
                f"Heat the braising vessel. {fat_text}, then brown {protein} on its broad sides. "
                "Work in batches only when the pieces would crowd the vessel."
            ),
            minutes=8, human_busy=True, stage="early", depends_on=brown_dependencies,
            equipment="pressure cooker" if braise_device == "pressure cooker" else "burner",
        ))
        seasoning_names = _resolved_requirements_by_ko(
            candidate, family_codes=("dry_seasoning", "salt_seasoning")
        )
        sauce_text = (
            _comfort_sauce_finish(candidate, sauce_profile.cook_instruction)
            if sauce_profile and sauce_profile.name == "simple comfort pan sauce"
            else sauce_profile.cook_instruction if sauce_profile
            else "Add enough broth or water to come one-third to halfway up the meat and scrape up the browned bits."
        )
        build_parts = [sauce_text]
        if seasoning_names and not sauce_profile:
            build_parts.append(f"Stir in {_join(seasoning_names)}.")
        if early_vegetables:
            build_parts.append(f"Add {_join(early_vegetables)} around the meat.")
        if braise_device == "pressure cooker":
            build_parts.append(
                "Scrape the bottom completely clean, then lock the pressure-cooker lid and close the valve."
            )
        elif braise_device == "slow cooker":
            build_parts.append("Transfer everything to the slow cooker and cover it.")
        else:
            build_parts.append(
                "Bring the liquid to a gentle simmer, then cover the vessel."
                if strategy == "braise" else
                "Bring the liquid to a simmer, cover the vessel, and transfer it to a 325°F oven."
            )
        activities.append(_planner_activity(
            "build braise", " ".join(build_parts), minutes=4, human_busy=True,
            stage="early", depends_on=["brown main protein:meal"],
            equipment="pressure cooker" if braise_device == "pressure cooker" else "burner",
        ))

        main_profile = get_ingredient_profile(protein, "protein")
        if braise_device == "pressure cooker":
            total_braise = 60
            main_instruction = (
                f"Cook {protein} at high pressure for 45 minutes, then allow a 15-minute natural release. "
                "Release any remaining pressure carefully before opening the lid away from your face."
            )
        elif braise_device == "slow cooker":
            total_braise = 360
            main_instruction = ""
        else:
            total_braise = max(60, int(main_profile.cook_minutes or 120))
            main_instruction = ""

        stage_groups = {}
        if braise_device != "pressure cooker":
            for name, cook_minutes in staged_vegetables:
                stage_groups.setdefault(cook_minutes, []).append(name)
        support_window = (
            30 if braise_device == "slow cooker" and raw_supporting
            else 15 if raw_supporting or ready_supporting or foundation else 0
        )
        if support_window:
            stage_groups.setdefault(support_window, []).extend([
                *raw_supporting, *ready_supporting, *([foundation] if foundation else []),
            ])
        longest_stage = max(stage_groups, default=0)
        first_window = max(1, total_braise - longest_stage)
        if braise_device == "slow cooker":
            main_instruction = (
                f"Cook {protein} covered on LOW for about {first_window} minutes. "
                "Keep the lid closed; add liquid only if the cooker is becoming dry."
            )
        activities.append(_planner_activity(
            "covered braise",
            main_instruction or (
                f"Cook {protein} covered over very gentle heat for about {first_window} minutes. "
                "Keep the liquid below a hard boil and add a small splash only if the vessel is becoming dry."
            ),
            minutes=first_window, human_busy=False, stage="middle",
            depends_on=["build braise:meal"], equipment=heat_equipment,
        ))
        finish_dependency = "covered braise:meal"
        ordered_windows = sorted(stage_groups, reverse=True)
        for index, window in enumerate(ordered_windows):
            names = list(dict.fromkeys(stage_groups[window]))
            raw_in_group = [name for name in names if name in raw_supporting]
            safety_text = (
                " Verify the center: 165°F for poultry sausage; 160°F for pork or beef sausage."
                if raw_in_group else ""
            )
            add_activity = _planner_activity(
                "add braise component",
                f"Add {_join(names)} to the braise, cover again, and return it to gentle heat.{safety_text}",
                minutes=2, human_busy=True, stage="late",
                depends_on=[finish_dependency], equipment=heat_equipment,
            )
            add_activity.component = _join(names)
            add_activity.activity_id = f"add braise component:{'-'.join(_clean(name).lower().replace(' ', '-') for name in names)}"
            activities.append(add_activity)
            next_window = ordered_windows[index + 1] if index + 1 < len(ordered_windows) else 0
            segment = max(1, window - next_window)
            cook_activity = _planner_activity(
                "continue braise",
                (
                    f"Continue the covered braise for about {segment} minutes. "
                    f"Keep the liquid below a hard boil and check that {_join(names)} is progressing toward tenderness."
                ),
                minutes=segment, human_busy=False, stage="late",
                depends_on=[add_activity.activity_id], equipment=heat_equipment,
            )
            cook_activity.component = _join(names)
            cook_activity.activity_id = f"continue braise:{'-'.join(_clean(name).lower().replace(' ', '-') for name in names)}"
            activities.append(cook_activity)
            finish_dependency = cook_activity.activity_id

        if braise_device == "pressure cooker" and staged_vegetables:
            names = [name for name, _minutes in staged_vegetables]
            longest = max(minutes for _name, minutes in staged_vegetables)
            pressure_finish = _planner_activity(
                "finish vegetables after pressure",
                (
                    f"With the pressure released and the lid removed, add {_join(names)}. "
                    f"Use Sauté on low and simmer gently for about {longest} minutes, removing individual vegetables when tender."
                ),
                minutes=longest, human_busy=True, stage="late",
                depends_on=[finish_dependency], equipment="pressure cooker",
            )
            pressure_finish.component = _join(names)
            pressure_finish.activity_id = "finish vegetables after pressure:meal"
            activities.append(pressure_finish)
            finish_dependency = pressure_finish.activity_id

        finish_opening = (
            "With the pressure-cooker lid safely removed, check the sauce."
            if braise_device == "pressure cooker" else
            "Remove the slow-cooker lid."
            if braise_device == "slow cooker" else
            "Uncover the braise."
        )
        finish_text = (
            f"{finish_opening} If the sauce is thin, move the meat to a plate and simmer the liquid briefly; "
            "if it is already glossy and spoonable, leave it alone. Taste before adding more salt or heat."
        )
        if any(_clean(item).lower() == "hot sauce" for item in candidate.get("selected_extras") or []):
            finish_text += " Add Hot sauce a little at a time, tasting before adding more."
        if finish_components:
            finish_text += f" Take the vessel off the heat, then add {_join(finish_components)} juice or wedges to taste."
        activities.append(_planner_activity(
            "finish braise", finish_text, minutes=3, human_busy=True, stage="finish",
            depends_on=[finish_dependency], equipment="burner" if strategy == "braise" else "counter",
        ))
        supporting_names = [_clean(item.get("name")) for item in supporting if _clean(item.get("name"))]
        plated_components = [
            *[name for name in vegetables if name not in finish_components],
            foundation,
        ]
        plated_components = [name for name in plated_components if name]
        service_instruction = f"Slice or portion {protein}."
        if len(supporting_names) == 1:
            service_instruction += (
                f" Slice {supporting_names[0]} if desired and serve it with {protein}."
            )
        elif supporting_names:
            service_instruction += f" Portion {_join(supporting_names)} and serve them with {protein}."
        if plated_components:
            service_instruction += f" Add {_join(plated_components)} to the plates."
        service_instruction += " Spoon the braising sauce over everything."
        activities.append(_planner_activity(
            "finish and serve",
            service_instruction,
            minutes=3, human_busy=True, stage="finish",
            depends_on=["finish braise:meal"], equipment="counter",
        ))
        return activities

    if strategy == "soup":
        # Soup is shared-vessel orchestration. Ingredient KOs still own prep
        # knowledge, but their separate skillet/pot cooking activities must not
        # survive into a one-pot meal.
        state_change_activities = [
            activity for activity in ko_activities
            if activity.activity_type == "thaw"
        ]
        prep_activities = [
            activity for activity in ko_activities
            if activity.activity_type == "prep"
            and not (
                activity.component == protein
                and "cooked" in protein_state.lower()
            )
        ]
        finish_only_activities = [
            activity for activity in ko_activities
            if activity.activity_type == "assemble" or activity.stage == "finish"
        ]
        for activity in prep_activities:
            if activity.component in vegetables:
                activity.instruction = (
                    f"Prep {activity.component}: wash, peel if needed, and chop into bite-size pieces."
                )
                activity.minutes = 2
        activities = [activities[0], *state_change_activities, *prep_activities]
        prep_ids = [_activity_id(activity) for activity in prep_activities]
        protein_prep = [
            _activity_id(activity) for activity in prep_activities
            if activity.component == protein
        ]
        energy = _clean(candidate.get("user_energy")).lower()
        raw_protein = bool(protein) and "cooked" not in protein_state.lower()
        include_sear = raw_protein and energy not in {"very low", "barely breathing"}

        previous = prep_ids
        if include_sear:
            activities.append(_planner_activity(
                "optional sear",
                (
                    f"Optional but preferred: heat a little oil in the soup pot and brown {protein} "
                    "for 2–5 minutes. Leave it in the pot; skip this step when energy is limited."
                ),
                minutes=4,
                human_busy=True,
                stage="early",
                depends_on=protein_prep,
                equipment="burner",
            ))
            previous = ["optional sear:meal", *[item for item in prep_ids if item not in protein_prep]]

        finish_names = {activity.component for activity in finish_only_activities}
        early_vegetables = [name for name in vegetables if name not in finish_names]
        foundation_profile = get_ingredient_profile(foundation, "foundation") if foundation else None
        foundation_is_late = any(
            activity.component == foundation and activity.stage in {"late", "finish"}
            for activity in ko_activities
        )
        sturdy_components = _join([*early_vegetables, "" if foundation_is_late else foundation])
        soup_liquid = _clean(candidate.get("soup_liquid")) or "broth or water"
        soup_liquid_quantity = _clean(candidate.get("soup_liquid_quantity")) or "enough to cover the ingredients"
        soup_liquid_measure = soup_liquid_quantity.split(",", 1)[0]
        seasoning_names = _resolved_requirements_by_ko(
            candidate, family_codes=("dry_seasoning", "salt_seasoning")
        )
        seasoning_text = _join(seasoning_names) if seasoning_names else "the seasonings"
        if include_sear:
            opening = (
                f"Add {soup_liquid_measure} of {soup_liquid} to the same soup pot and "
                "scrape up the browned bits. "
            )
        else:
            opening = (
                f"Set the soup pot over medium heat and add {soup_liquid_measure} of {soup_liquid}. "
            )
        soup_build_extras = _extras_instruction(candidate, strategy, "build")
        activities.append(_planner_activity(
            "build soup",
            (
                opening
                + (f"Add {sturdy_components}. " if sturdy_components else "")
                + (
                    f"Add the cooked {protein}. "
                    if protein and not raw_protein
                    else (f"Keep {protein} in the pot. " if protein else "")
                )
                + f"Stir in {seasoning_text}. "
                + (f"{soup_build_extras} " if soup_build_extras else "")
                + "Bring everything to a gentle simmer."
            ),
            minutes=3,
            human_busy=True,
            stage="middle",
            depends_on=previous,
            equipment="burner",
        ))

        protein_profile = get_ingredient_profile(protein, "protein") if protein else None
        protein_traits = set(getattr(protein_profile, "behavior_traits", ()))
        protein_physical = set(getattr(protein_profile, "physical_traits", ()))
        protein_families = set(getattr(protein_profile, "behavior_family_codes", ()))
        if "long-lead" in protein_traits and "collagen-rich" in protein_physical:
            simmer_minutes = max(1, int(getattr(protein_profile, "cook_minutes", 0) or 0))
            tenderness_cue = (
                getattr(protein_profile, "desired_outcome", "")
                or "The meat is fork-tender and yields without springing back."
            )
            simmer_instruction = (
                f"Cover the pot and keep {_join([protein, *early_vegetables, '' if foundation_is_late else foundation]) or 'the soup ingredients'} "
                f"together in the same pot. Gently simmer for about {simmer_minutes} minutes, "
                f"then check for tenderness: {tenderness_cue} "
                "Crack the lid only if the soup needs to reduce."
            )
        elif raw_protein and "safety-critical" in protein_physical:
            simmer_minutes = 30
            simmer_instruction = (
                f"Cover the pot and gently simmer {protein or 'the soup ingredients'}, "
                f"{_join(vegetables)}, and {foundation or 'the remaining ingredients'} "
                "together until the protein is safe and tender and the vegetables are cooked through."
            )
        elif not raw_protein and "legume" in protein_families:
            simmer_minutes = 18
            simmer_instruction = (
                f"Partially cover the pot and gently simmer the cooked {protein or 'ingredients'} "
                f"and {_join(vegetables)} until the vegetables are tender and the beans are hot, "
                "about 15–20 minutes. Stir occasionally and add a little more broth or water if needed."
            )
        elif not raw_protein:
            simmer_minutes = 18
            simmer_instruction = (
                f"Partially cover the pot and gently simmer the cooked {protein or 'ingredients'} "
                f"and {_join(vegetables)} until the vegetables are tender and the {protein or 'cooked ingredients'} "
                "are steaming hot. Stir occasionally and add a little more broth or water if needed."
            )
        else:
            simmer_minutes = 25
            simmer_instruction = (
                f"Cover the pot and gently simmer {protein or 'the soup ingredients'}, "
                f"{_join(vegetables)}, and {foundation or 'the remaining ingredients'} "
                "together until the protein is safe and tender and the vegetables are cooked through."
            )
        activities.append(_planner_activity(
            "shared simmer",
            simmer_instruction,
            minutes=simmer_minutes,
            human_busy=False,
            stage="middle",
            depends_on=["build soup:meal"],
            equipment="burner",
        ))
        finish_dependency = "shared simmer:meal"
        late_names = [*([foundation] if foundation_is_late else []), *finish_names]
        cooking_late_names = [name for name in late_names if name not in finish_names]
        if cooking_late_names:
            activities.append(_planner_activity(
                "late soup additions",
                f"Stir in {_join(cooking_late_names)} and heat gently only until steaming hot so it keeps its texture.",
                minutes=4, human_busy=True, stage="finish",
                depends_on=[finish_dependency], equipment="burner",
            ))
            finish_dependency = "late soup additions:meal"
        if not raw_protein and "legume" in protein_families:
            energy_allows_blending = energy not in {"low", "very low", "barely breathing"}
            equipment = " ".join(candidate.get("available_equipment") or []).lower()
            can_blend = "immersion blender" in equipment or "blender" in equipment
            if energy_allows_blending and can_blend:
                texture_instruction = (
                    "For a smooth soup, blend until creamy. If using a countertop blender, work in small batches, "
                    "vent the lid, cover it with a towel, and keep hands clear of hot steam; return the soup to the pot."
                )
                texture_minutes = 5
            else:
                texture_instruction = (
                    f"For a naturally thicker rustic soup, mash about one-third of the {protein} against the side "
                    "of the pot with a fork or sturdy spoon, then stir the mashed beans back into the soup."
                )
                texture_minutes = 2
            activities.append(_planner_activity(
                "texture soup",
                texture_instruction,
                minutes=texture_minutes,
                human_busy=True,
                stage="finish",
                depends_on=[finish_dependency],
                equipment="burner",
            ))
            finish_dependency = "texture soup:meal"
        soup_extras = _extras_instruction(candidate, strategy)
        citrus_finish = " ".join(
            activity.instruction for activity in finish_only_activities
            if activity.component in finish_names
        )
        activities.append(_planner_activity(
            "finish soup",
            " ".join(filter(None, (
                "Taste the soup. Adjust salt and the other seasonings only as needed.",
                citrus_finish,
                soup_extras,
                "Serve from the pot.",
            ))),
            minutes=2,
            human_busy=True,
            stage="finish",
            depends_on=[finish_dependency],
            equipment="burner",
        ))
        stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
        return sorted(
            activities,
            key=lambda activity: (stage_order.get(activity.stage, 1), activity.source != "ko"),
        )

    if strategy == "casserole":
        state_change_activities = [
            activity for activity in ko_activities if activity.activity_type == "thaw"
        ]
        foundation_behavior = (
            resolve_behavior(
                foundation, "foundation", component_forms.get(foundation.lower(), ""),
                "casserole", DB_PATH,
            ) if foundation else None
        )
        foundation_pre_cook = [
            activity for activity in ko_activities
            if activity.component == foundation
            and activity.activity_type == "cook"
            and foundation_behavior
            and foundation_behavior.method
            and foundation_behavior.method.method in {"boil", "simmer"}
            and "dry" in _clean(component_forms.get(foundation.lower(), "")).lower()
        ]
        # A dry foundation's cook activity owns heating its water and draining
        # it. Publishing the KO's generic setup as meal prep would otherwise
        # start a pot boiling before an unrelated long thaw has even begun.
        prep_activities = [
            activity for activity in ko_activities
            if activity.activity_type in {"prep", "assemble"}
            and not (
                foundation_pre_cook
                and activity.component == foundation
            )
        ]
        if foundation_behavior and foundation_behavior.primary_family and foundation_pre_cook:
            family_code = foundation_behavior.primary_family.code
            for activity in foundation_pre_cook:
                if family_code == "pasta":
                    activity.instruction = (
                        f"Boil {foundation} in ample water for about 2 minutes less than the package's minimum time. "
                        "It should be flexible but still firmer than you would serve it. Drain it thoroughly; it will finish in the casserole."
                    )

        activities = [activities[0], *state_change_activities, *prep_activities]
        prep_ids = [_activity_id(activity) for activity in prep_activities]
        sauce_prep_instruction = _resolved_sauce_prep(candidate, sauce_profile)
        sauce_prep_id = "prepare casserole sauce:meal"
        if sauce_prep_instruction:
            activities.append(_planner_activity(
                "prepare casserole sauce", sauce_prep_instruction,
                minutes=max(2, int(sauce_profile.prep_minutes or 2)),
                human_busy=True, stage="early", depends_on=prep_ids,
                equipment="counter",
            ))
            for activity in foundation_pre_cook:
                activity.depends_on = [sauce_prep_id]
        activities.extend(foundation_pre_cook)

        moisture_sensitive = []
        for name in vegetables:
            traits = set(get_ingredient_profile(name, "vegetable").behavior_traits)
            if traits & {"protect-dry-browning", "dry-or-deliberately-wet"}:
                moisture_sensitive.append(name)
        moisture_id = ""
        if moisture_sensitive:
            selected_fat = next(iter(_resolved_requirements_by_ko(
                candidate, family_codes=("cooking_fat",)
            )), "")
            fat_instruction = (
                f"Lightly coat them with part of the measured {selected_fat}. "
                if selected_fat else ""
            )
            moisture_dependencies = [sauce_prep_id] if sauce_prep_instruction else prep_ids
            activities.append(_planner_activity(
                "reduce casserole moisture",
                (
                    f"Spread {_join(moisture_sensitive)} on a rimmed sheet pan. {fat_instruction}"
                    "Roast at 425°F for about 12 minutes, until excess surface moisture has evaporated but the pieces are not fully cooked. "
                    "Lower the oven to 375°F for the casserole."
                ),
                minutes=12, human_busy=False, stage="early",
                depends_on=moisture_dependencies, equipment="oven",
            ))
            moisture_id = "reduce casserole moisture:meal"

        casserole_extras = _extras_instruction(candidate, strategy)
        quantity_plan = candidate.get("quantity_plan") or {}
        produce_cups = sum(
            float((quantity_plan.get(name.lower()) or {}).get("planned") or 0)
            for name in vegetables
        )
        vessel_instruction = (
            "Use a deep 4-quart baking dish; if the ingredients would sit deeper than about 2 inches, divide them evenly between two dishes."
            if produce_cups > 6 or len(components) >= 8 else
            "Choose a baking dish that holds the ingredients in a layer no deeper than about 2 inches."
        )
        selected_fat = next(iter(_resolved_requirements_by_ko(
            candidate, family_codes=("cooking_fat",)
        )), "")
        grease_instruction = (
            f"Grease the baking dish lightly with part of the measured {selected_fat}."
            if selected_fat else
            "Lightly grease the baking dish unless the selected sauce already provides enough fat."
        )
        ready_proteins = [
            _clean(item.get("name")) for item in protein_specs
            if _clean(item.get("state")).lower() in {"cooked", "canned", "ready to eat"}
        ]
        initial_components = [
            item for item in components if item not in ready_proteins
        ]
        late_ready_proteins = ready_proteins if initial_components else []
        if not initial_components:
            initial_components = list(components)
        combine_dependencies = list(dict.fromkeys([
            *([sauce_prep_id] if sauce_prep_instruction else prep_ids),
            *[_activity_id(activity) for activity in foundation_pre_cook],
            *([moisture_id] if moisture_id else []),
        ]))
        activities.append(_planner_activity(
            "combine",
            " ".join(filter(None, (
                vessel_instruction,
                grease_instruction,
                f"Arrange {_join(initial_components)} evenly in the dish and coat them with the prepared {sauce}.",
                casserole_extras,
            ))),
            minutes=5,
            stage="middle",
            depends_on=combine_dependencies,
            equipment="counter",
        ))
        method_rules = []
        for item in protein_specs:
            resolved = resolve_behavior(
                _clean(item.get("name")), "protein", _clean(item.get("state")), "casserole", DB_PATH
            )
            if resolved.method:
                method_rules.append((_clean(item.get("name")), resolved.method, True))
        for name in vegetables:
            resolved = resolve_behavior(
                name, "vegetable", _clean(component_forms.get(name.lower())) or "Fresh", "casserole", DB_PATH
            )
            if resolved.method:
                method_rules.append((name, resolved.method, False))
        bake_minutes = max([rule.cook_minutes for _, rule, _ in method_rules] or [25])
        protein_cues = [
            f"{name}: {rule.doneness_cue}" for name, rule, is_protein
            in method_rules
            if is_protein and rule.verification_required and rule.doneness_cue
        ]
        if late_ready_proteins:
            first_bake_minutes = max(1, bake_minutes - 10)
            activities.append(_planner_activity(
                "bake casserole base",
                (
                    f"Bake at 375°F for about {first_bake_minutes} minutes, covering the dish if the surface browns too quickly. "
                    "This head start cooks the raw and slower components before the already-cooked protein joins."
                ),
                minutes=first_bake_minutes, human_busy=False, stage="middle",
                depends_on=["combine:meal"], equipment="oven",
            ))
            activities.append(_planner_activity(
                "add cooked protein",
                (
                    f"Fold {_join(late_ready_proteins)} into the casserole, distributing it evenly without breaking up the other components."
                ),
                minutes=2, human_busy=True, stage="late",
                depends_on=["bake casserole base:meal"], equipment="counter",
            ))
            activities.append(_planner_activity(
                "finish casserole bake",
                (
                    "Return the casserole to the oven for about 10 minutes, until the sauce bubbles at the edges, "
                    "the firmest vegetable pieces are tender, and the added cooked protein is steaming hot."
                ),
                minutes=10, human_busy=False, stage="late",
                depends_on=["add cooked protein:meal"], equipment="oven",
            ))
            finish_dependency = "finish casserole bake:meal"
        else:
            activities.append(_planner_activity(
                "bake",
                (
                    f"Bake at 375°F for about {bake_minutes} minutes, covering the dish if the surface browns before the center is ready. "
                    "The sauce should bubble at the edges and the firmest vegetable pieces should be tender."
                ),
                minutes=bake_minutes,
                human_busy=False,
                stage="middle",
                depends_on=["combine:meal"],
                equipment="oven",
            ))
            finish_dependency = "bake:meal"
        if protein_cues:
            activities.append(_planner_activity(
                "verify casserole",
                "Check the casserole before serving. " + " ".join(protein_cues),
                minutes=2, human_busy=True, stage="finish",
                depends_on=[finish_dependency], equipment="counter",
            ))
            finish_dependency = "verify casserole:meal"
        activities.append(_planner_activity(
            "serve casserole",
            "Let the casserole stand for 5 minutes so the sauce settles, then portion it and serve hot.",
            minutes=5, human_busy=False, stage="finish",
            depends_on=[finish_dependency], equipment="counter",
        ))
    elif strategy == "handheld":
        handheld_extras = _extras_instruction(candidate, strategy)
        wrapper = foundation or "the bread or wrap from My Kitchen"
        filling = _join([*protein_names, *vegetables]) or "the prepared filling"
        activities.append(_planner_activity(
            "assemble",
            " ".join(filter(None, (
                f"Divide {filling} evenly among {wrapper}.",
                handheld_extras,
                "Wrap, stack, or fold each serving so the filling is secure and easy to eat.",
            ))),
            minutes=5,
            stage="finish",
            depends_on=component_finishes,
            equipment="counter",
        ))
    elif strategy == "kid_adventure":
        activities.append(_planner_activity(
            "plate",
            f"Arrange the prepared components and serve {sauce} as a dip, moat, or drizzle.",
            minutes=3,
            stage="finish",
            depends_on=component_finishes,
            equipment="counter",
        ))
    else:
        protein_gate = next((
            _activity_id(activity)
            for activity in ko_activities
            if activity.component == protein and activity.activity_type == "verify"
        ), None) or next((
            _activity_id(activity)
            for activity in ko_activities
            if activity.component == protein and activity.activity_type in {"cook", "reheat"}
        ), None)
        sauce_dependencies = terminal_ids(vegetables)
        primary_is_ready = _ready_to_eat_state(protein_state)
        if protein_gate and not primary_is_ready and protein_gate not in sauce_dependencies:
            sauce_dependencies.append(protein_gate)
        if strategy == "grill":
            finish_instruction = (
                f"Prepare {sauce} separately as a finishing sauce or table accompaniment. "
                "Keep it off the grill's direct flame and taste before serving."
            )
        elif strategy == "oven_roast":
            finish_instruction = (
                f"Warm {sauce} separately over low heat and use it as a light finishing glaze or table sauce. "
                "Do not turn the dry-roasted main into a braise after it leaves the oven. Taste before serving."
            )
        else:
            finish_instruction = (
                _comfort_sauce_finish(candidate, sauce_profile.cook_instruction)
                if sauce_profile and sauce_profile.name == "simple comfort pan sauce"
                else _resolved_sauce_finish(candidate, sauce_profile) if sauce_profile
                else f"Taste, adjust seasoning, and finish {sauce}; use the browned cooking flavor when available."
            )
        finish_instruction = " ".join(filter(None, (
            finish_instruction,
            _extras_instruction(candidate, strategy),
        )))
        activities.append(_planner_activity(
            "finish sauce",
            finish_instruction,
            minutes=sauce_profile.finish_minutes if sauce_profile else 3,
            stage="finish",
            depends_on=sauce_dependencies,
            equipment="counter" if strategy == "grill" else "burner",
        ))
        primary_profile = get_ingredient_profile(protein, "protein") if protein else None
        one_pan_ground_meat = (
            strategy == "skillet"
            and "ground" in set(getattr(primary_profile, "physical_traits", ()))
            and bool(vegetables)
        )
        meal_structure = _clean(candidate.get("meal_structure")) or "integrated"
        plated_components = _join([foundation, *vegetables]) or "the cooked components"
        protein_label = _join(protein_names)
        protein_has_slice = any(
            activity.component in protein_names and activity.activity_type in {"slice", "rest"}
            for activity in ko_activities
        )
        if protein_has_slice:
            protein_service = (
                f"Slice any rested protein that needs slicing, add {protein_label} to the plates, and serve immediately."
            )
        elif protein_names:
            protein_service = f"Add {protein_label} to the plates and serve immediately."
        else:
            protein_service = "Serve immediately."
        if meal_structure == "layered_bowl":
            service_instruction = (
                f"Divide {foundation} among bowls, then arrange the finished vegetables, sauce, and {protein_label} over it. Serve immediately."
                if foundation else
                f"Spoon the finished vegetables and sauce into bowls, add {protein_label}, and serve immediately."
            )
        elif meal_structure == "integrated" and strategy == "skillet":
            foundation_is_separate = foundation and not any(
                    _clean(candidate.get("component_forms", {}).get(foundation)).lower() == value
                    for value in ("canned", "cooked", "ready to eat")
                )
            sliced_protein = (
                f"Slice the rested {protein_label}. " if protein_has_slice else ""
            )
            service_instruction = (
                f"{sliced_protein}Divide {foundation} among plates or shallow bowls, add {protein_label}, "
                "then spoon the vegetables and pan sauce over everything and serve immediately."
                if foundation_is_separate else
                "Spoon everything in the skillet onto plates or into shallow bowls and serve immediately."
                if one_pan_ground_meat or primary_is_ready else
                f"{sliced_protein}Add {protein_label} to the skillet, coat it with the vegetables and sauce, "
                "then serve immediately."
            )
        else:
            service_instruction = (
                f"Plate {plated_components} with the finished sauce. {protein_service}"
            )
        activities.append(_planner_activity(
            "finish and serve",
            service_instruction,
            minutes=2,
            stage="finish",
            depends_on=(
                terminal_ids([*vegetables, foundation, *protein_names])
                + ["finish sauce:meal"]
            ),
            equipment="counter",
        ))

    stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
    return sorted(
        activities,
        key=lambda activity: (stage_order.get(activity.stage, 1), activity.source != "ko"),
    )


def consolidate_kitchen_activities(
    activities: List[KitchenActivity],
    candidate: Optional[dict] = None,
) -> List[KitchenActivity]:
    """Translate ingredient activities into work a cook actually performs.

    Long-lead components receive a small launch-prep phase so they can begin
    before general ingredient prep. Remaining ingredient prep plus sauce/spice
    measuring becomes one calm meal-level prep phase while passive work runs.
    """

    prep_activities = [
        activity
        for activity in activities
        if activity.source == "ko"
        and activity.activity_type == "prep"
        and activity.human_busy
        and (activity.equipment or "counter").lower() == "counter"
        # A prep activity that follows an explicit state change (for example,
        # patting chicken dry after thawing) must remain visible and keep that
        # dependency instead of being folded into the general prep block.
        and not activity.depends_on
    ]
    if len(prep_activities) < 2:
        return activities

    prep_ids = {_activity_id(activity) for activity in prep_activities}
    by_id = {_activity_id(activity): activity for activity in activities}
    dependents: Dict[str, List[KitchenActivity]] = {}
    for activity in activities:
        for dependency in activity.depends_on:
            dependents.setdefault(dependency, []).append(activity)

    def launches_long_lead(prep_activity):
        pending = list(dependents.get(_activity_id(prep_activity), []))
        seen = set()
        while pending:
            activity = pending.pop(0)
            activity_id = _activity_id(activity)
            if activity_id in seen:
                continue
            seen.add(activity_id)
            if (
                (not activity.human_busy and int(activity.minutes or 0) >= 10)
                or ((activity.equipment or "").lower() == "oven" and int(activity.minutes or 0) >= 15)
            ):
                return True
            pending.extend(dependents.get(activity_id, []))
        return False

    launch_prep = [activity for activity in prep_activities if launches_long_lead(activity)]
    general_prep = [activity for activity in prep_activities if activity not in launch_prep]
    launch_ids = {_activity_id(activity) for activity in launch_prep}
    general_ids = {_activity_id(activity) for activity in general_prep}
    launch_starts = []
    for prep_activity in launch_prep:
        for dependent in dependents.get(_activity_id(prep_activity), []):
            dependent_id = _activity_id(dependent)
            if dependent_id not in launch_starts:
                launch_starts.append(dependent_id)

    def consolidated_prep(activity_type, selected, depends_on, extra_instruction="", extra_minutes=0):
        instructions = []
        for activity in selected:
            instructions.append(activity.instruction.rstrip("."))
        if extra_instruction:
            instructions.append(extra_instruction.rstrip("."))
        calculated_minutes = sum(max(0, int(activity.minutes or 0)) for activity in selected)
        if (
            activity_type == "prep"
            or (activity_type == "launch prep" and _strategy(candidate or {}) == "casserole")
        ) and candidate:
            vegetables = _split_joined_items(candidate.get("vegetable"))
            protein = _clean(candidate.get("protein"))

            # Prep timing rule:
            # 1 minute per vegetable + 1 minute per protein
            # + 1 additional minute for each ingredient that must be
            # sliced, chopped, or diced.
            calculated_minutes = len(vegetables) + (1 if protein else 0)

            timed_components = {item.lower() for item in vegetables}
            if protein:
                timed_components.add(protein.lower())

            needs_cutting_allowance = any(
                _clean(getattr(activity, "component", "")).lower() in timed_components
                and re.search(
                    r"\b(?:cut|cutting|slice|sliced|slicing|chop|chopped|chopping|dice|diced|dicing)\b",
                    _clean(getattr(activity, "instruction", "")).lower(),
                )
                for activity in selected
            )

            if needs_cutting_allowance:
                calculated_minutes += 1
            if protein and vegetables and _clean(candidate.get("foundation")):
                calculated_minutes = max(5, calculated_minutes)
        heading = "Prepare these first:" if activity_type == "launch prep" else "Ingredient Prep:"
        formatted_instructions = "\n\n".join(
            f"- {instruction}." for instruction in instructions
        )
        return KitchenActivity(
            component="meal",
            activity_type=activity_type,
            instruction=f"{heading}\n\n{formatted_instructions}",
            minutes=calculated_minutes + extra_minutes,
            human_busy=True,
            equipment="counter",
            depends_on=list(depends_on),
            stage="early",
            parallel_ok=False,
            source="consolidator",
            activity_id="prep:launch" if activity_type == "launch prep" else "prep:meal",
        )

    replacements = []
    if launch_prep:
        replacements.append(consolidated_prep("launch prep", launch_prep, ["gather:meal"]))
    sauce = _clean((candidate or {}).get("sauce"))
    strategy = _strategy(candidate)
    sauce_profile = get_sauce_profile(sauce)
    sauce_instruction = (
        "" if strategy in {"soup", "braise", "oven_braise", "handheld", "casserole"}
        else _comfort_sauce_prep(candidate or {}, sauce_profile.prep_instruction)
        if sauce_profile and sauce_profile.name == "simple comfort pan sauce"
        else _resolved_sauce_prep(candidate or {}, sauce_profile) if sauce_profile
        else (f"measure and mix {sauce}" if sauce else "")
    )
    if sauce_profile and sauce_profile.name == "BBQ Sauce":
        selected_broth = next((
            _clean(item) for item in (candidate or {}).get("selected_extras") or []
            if "broth_liquid" in set(get_ingredient_profile(_clean(item), "ingredient").behavior_family_codes)
        ), "")
        if selected_broth:
            sauce_instruction = sauce_instruction.replace("broth or water", selected_broth)
    if general_prep or sauce_instruction:
        external_prep_dependencies = [
            dependency
            for activity in general_prep
            for dependency in activity.depends_on
            if dependency not in general_ids and dependency not in launch_ids
        ]
        general_dependencies = list(dict.fromkeys([
            *(launch_starts or ["gather:meal"]),
            *external_prep_dependencies,
        ]))
        replacements.append(consolidated_prep(
            "prep", general_prep, general_dependencies,
            extra_instruction=sauce_instruction,
            extra_minutes=0,
        ))

    consolidated = []
    inserted = False
    for activity in activities:
        if activity in prep_activities:
            if not inserted:
                consolidated.extend(replacements)
                inserted = True
            continue

        if activity.depends_on:
            rewritten = []
            for dependency in activity.depends_on:
                if dependency in launch_ids:
                    dependency = "prep:launch"
                elif dependency in general_ids:
                    dependency = "prep:meal"
                if dependency not in rewritten:
                    rewritten.append(dependency)
            activity.depends_on = rewritten
        consolidated.append(activity)

    return consolidated


def consolidate_final_service(activities: List[KitchenActivity]) -> List[KitchenActivity]:
    """Fold a separately published protein slice into the meal's service pass.

    The ingredient KO still publishes slicing as required knowledge. At meal level,
    however, slicing, plating, saucing, and carrying the plates are one continuous
    service activity. The service pass inherits the slice activity's dependencies,
    so a required protein rest is never shortened or bypassed.
    """
    service = next(
        (activity for activity in activities if _activity_id(activity) == "finish and serve:meal"),
        None,
    )
    if service is None:
        return activities

    slice_activities = [
        activity for activity in activities
        if activity.source == "ko" and activity.activity_type == "slice"
    ]
    if not slice_activities:
        return activities

    slice_by_id = {_activity_id(activity): activity for activity in slice_activities}
    rewritten = []
    for dependency in service.depends_on:
        if dependency in slice_by_id:
            for inherited in slice_by_id[dependency].depends_on:
                if inherited not in rewritten:
                    rewritten.append(inherited)
        elif dependency not in rewritten:
            rewritten.append(dependency)
    service.depends_on = rewritten
    return [activity for activity in activities if activity not in slice_activities]


def consolidate_skillet_vegetables(
    activities: List[KitchenActivity],
    candidate: dict,
) -> List[KitchenActivity]:
    """Interlace compatible vegetables in the skillet instead of serializing them.

    Generic vegetable KOs may each publish a complete burner window. For a
    skillet meal, compatible vegetables belong in one pan with a short head
    start for the sturdier ingredient, not in consecutive isolated recipes.
    """
    if (
        _strategy(candidate) != "skillet"
        or _clean(candidate.get("meal_structure")) == "composed_plate"
    ):
        return activities

    vegetables = _split_joined_items(candidate.get("vegetable"))
    protein = _clean(candidate.get("protein"))
    protein_profile = get_ingredient_profile(protein, "protein") if protein else None
    ground_meat = "ground" in set(getattr(protein_profile, "physical_traits", ()))
    if not vegetables or (len(vegetables) < 2 and not ground_meat):
        return activities

    vegetable_activities = [
        activity for activity in activities
        if activity.source == "ko"
        and activity.component in vegetables
        and activity.activity_type in {"cook", "saute"}
        and (activity.equipment or "").lower() == "burner"
    ]
    if not vegetable_activities or (len(vegetable_activities) < 2 and not ground_meat):
        return activities

    if ground_meat:
        protein_cook = next((
            activity for activity in activities
            if activity.component == protein and activity.activity_type == "cook"
        ), None)
        if protein_cook is None:
            return activities

        protein_verify = next((
            activity for activity in activities
            if activity.component == protein and activity.activity_type == "verify"
        ), None)
        # The consolidated cook instruction already contains the explicit
        # endpoint and color warning. Absorb the separate verification node so
        # safety remains mandatory without charging the cook for the same check twice.
        old_activities = [protein_cook, *vegetable_activities, *([protein_verify] if protein_verify else [])]
        old_ids = {_activity_id(activity) for activity in old_activities}
        dependencies = []
        for activity in old_activities:
            for dependency in activity.depends_on:
                if dependency not in old_ids and dependency not in dependencies:
                    dependencies.append(dependency)

        vegetable_keys = {activity.component.lower() for activity in vegetable_activities}
        seasoning_names = [
            name for name in _resolved_requirements_by_ko(
                candidate, family_codes=("dry_seasoning", "salt_seasoning")
            ) if name.lower() not in vegetable_keys
        ]
        bloom_instruction = (
            f"Stir in {_join(seasoning_names)} and let the seasonings bloom in the hot fat for about 30 seconds. "
            if seasoning_names else ""
        )
        vegetable_profiles = {
            activity.component: get_ingredient_profile(activity.component, "vegetable")
            for activity in vegetable_activities
        }
        trait_sets = {
            name: set(profile.behavior_traits) | set(profile.physical_traits)
            for name, profile in vegetable_profiles.items()
        }
        sturdy = [
            name for name, profile in vegetable_profiles.items()
            if profile.cook_minutes >= 10
            or "long-lead-vegetable" in trait_sets[name]
            or "slow-softening" in trait_sets[name]
        ]
        aromatics = [
            name for name in vegetable_profiles
            if name not in sturdy
            and ({"early-entry", "joins-sauce-base"} & trait_sets[name])
        ]
        later = [
            name for name in vegetable_profiles
            if name not in sturdy and name not in aromatics
        ]
        texture_targets = [
            f"{name} reaches this outcome: {profile.desired_outcome.rstrip('.')}"
            for name, profile in vegetable_profiles.items()
        ]
        texture_text = "; and ".join(texture_targets) or "the vegetables are tender"
        protein_rule = resolve_behavior(
            protein, "protein", _clean(candidate.get("protein_state")), "skillet", DB_PATH
        ).method
        protein_endpoint = (
            protein_rule.doneness_cue.rstrip(".")
            if protein_rule and protein_rule.doneness_cue
            else "the center of the thickest clump reaches its verified safe temperature"
        )
        if sturdy:
            vegetable_opening = (
                f"Add {_join([*sturdy, *aromatics])} to the skillet with 2 tablespoons water. "
                "Cover and steam-soften for about 4 minutes, then uncover and let the water evaporate. "
            )
            beef_opening = (
                f"Add {protein} to the same skillet and break it into small crumbles. "
                "Cook for about 8 minutes, allowing brief contact with the pan for browning. "
            )
            later_text = (
                f"Add {_join(later)} during the final 5–7 minutes so it does not overcook. "
                if later else ""
            )
            total_cook_minutes = 16 + (2 if later else 0)
        else:
            vegetable_opening = (
                f"Heat the skillet, add {protein}, and break it into small crumbles. Cook for about 4 minutes. "
            )
            beef_opening = ""
            later_text = (
                f"Add {_join(later or aromatics)} to the same skillet and cook for about 5–7 minutes. "
            )
            total_cook_minutes = 11
        shared = _planner_activity(
            "cook skillet",
            (
                vegetable_opening
                + beef_opening
                + bloom_instruction
                + later_text
                + f"Continue until {texture_text}. Verify {protein}: {protein_endpoint}. "
                "Color alone is not the safety test. Break apart any large clumps and continue cooking if the "
                "center has not reached that endpoint. If there is more than about 1 tablespoon of fat, drain only the excess "
                "and leave a light coating in the skillet for the sauce."
            ),
            minutes=max(total_cook_minutes, int(protein_cook.minutes or 0)),
            human_busy=True,
            stage="middle",
            depends_on=dependencies,
            equipment="burner",
        )
        shared.attention_load = max(
            float(activity.attention_load or 0) for activity in old_activities
        )
        shared.activity_id = "cook skillet:meal"

        rewritten = []
        for activity in activities:
            if activity in old_activities:
                continue
            new_dependencies = []
            for dependency in activity.depends_on:
                dependency = "cook skillet:meal" if dependency in old_ids else dependency
                if dependency not in new_dependencies:
                    new_dependencies.append(dependency)
            activity.depends_on = new_dependencies
            rewritten.append(activity)
        rewritten.append(shared)
        return rewritten

    profiles = {
        activity.component: get_ingredient_profile(activity.component, "vegetable")
        for activity in vegetable_activities
    }

    def environment_priority(activity):
        profile = profiles[activity.component]
        traits = set(profile.behavior_traits)
        if "protect-dry-browning" in traits:
            return 0
        if "early-entry" in traits or "joins-sauce-base" in traits:
            return 1
        if "long-lead-vegetable" in traits or profile.cook_minutes >= 10:
            return 2
        if "late-entry" in traits or "last-entry" in traits or "party-cooked" in traits:
            return 4
        return 3
    vegetable_activities.sort(key=lambda activity: (
        environment_priority(activity), vegetables.index(activity.component),
    ))
    first, *later = vegetable_activities
    trait_sets = {
        component: set(profile.behavior_traits) | set(profile.physical_traits)
        for component, profile in profiles.items()
    }
    protected_first = "protect-dry-browning" in trait_sets[first.component]
    rustic_sauce = (
        any("party-cooked" in traits for traits in trait_sets.values())
        and any("joins-sauce-base" in traits for traits in trait_sets.values())
    )
    deliberate_wet_mucilage = (
        any("mucilage-rich" in traits for traits in trait_sets.values())
        and any("acidic" in traits for traits in trait_sets.values())
    )
    if protected_first:
        head_start, together_minutes = 6, 6
    elif rustic_sauce:
        head_start, together_minutes = 4, 8
    elif deliberate_wet_mucilage:
        head_start, together_minutes = 6, 4
    else:
        base_minutes = max(2, max(int(activity.minutes or 0) for activity in vegetable_activities))
        head_start = min(3, max(1, base_minutes // 3))
        together_minutes = max(2, base_minutes - head_start)
    total_minutes = head_start + together_minutes

    dependencies = []
    old_ids = {_activity_id(activity) for activity in vegetable_activities}
    for activity in vegetable_activities:
        for dependency in activity.depends_on:
            if dependency not in old_ids and dependency not in dependencies:
                dependencies.append(dependency)
    cooked_protein = _clean(candidate.get("protein_state")) in {"Cooked", "Canned"}
    protein_gate = next(
        (_activity_id(activity) for activity in activities
         if activity.component == _clean(candidate.get("protein"))
         and activity.activity_type == "verify"),
        None,
    ) or next(
        (_activity_id(activity) for activity in activities
         if activity.component == _clean(candidate.get("protein"))
         and activity.activity_type in {"cook", "reheat"}),
        None,
    )
    if protein_gate and not cooked_protein and protein_gate not in dependencies:
        dependencies.append(protein_gate)

    selected_fat = next((
        item for item in candidate.get("selected_extras") or []
        if "cooking_fat" in set(
            get_ingredient_profile(_clean(item), "ingredient").behavior_family_codes
        )
    ), "")
    heat_fat = f"Heat {_clean(selected_fat)} in the skillet. " if selected_fat else ""
    vessel_opening = "Add" if cooked_protein else "After moving the protein to a plate, add"
    if protected_first:
        opening = (
            heat_fat + f"{vessel_opening} {first.component} to the skillet in a single, uncrowded layer. "
            f"Let the moisture evaporate and the bottoms brown before turning, about {head_start} minutes. "
        )
    elif rustic_sauce:
        aromatics = [
            activity.component for activity in vegetable_activities
            if "joins-sauce-base" in trait_sets[activity.component]
        ]
        opening = (
            heat_fat + f"{vessel_opening} {_join(aromatics)} to the skillet and soften them for about {head_start} minutes. "
        )
        later = [activity for activity in vegetable_activities if activity.component not in aromatics]
    else:
        opening = heat_fat + f"{vessel_opening} {first.component} to the skillet and cook for {head_start} minutes. "
    outcome_parts = [
        f"{component} reaches this outcome: {profile.desired_outcome.rstrip('.')}"
        for component, profile in profiles.items()
    ]
    outcome = "; ".join(outcome_parts) or "the vegetables are tender and ready for the sauce"
    shared = _planner_activity(
        "cook vegetables",
        (
            opening
            + f"Add {_join([item.component for item in later])}, then "
            f"cook everything together for about {together_minutes} more minutes, stirring as needed, "
            f"until {outcome}."
        ),
        minutes=total_minutes,
        human_busy=True,
        stage="middle",
        depends_on=dependencies,
        equipment="burner",
    )
    shared.attention_load = max(
        float(activity.attention_load or 0) for activity in vegetable_activities
    )

    rewritten = []
    for activity in activities:
        if activity in vegetable_activities:
            continue
        new_dependencies = []
        for dependency in activity.depends_on:
            dependency = "cook vegetables:meal" if dependency in old_ids else dependency
            if dependency not in new_dependencies:
                new_dependencies.append(dependency)
        activity.depends_on = new_dependencies
        if _activity_id(activity) == "finish sauce:meal":
            activity.depends_on = ["cook vegetables:meal"]
        rewritten.append(activity)
    rewritten.append(shared)
    return rewritten


def consolidate_composed_plate_components(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Build natural shared components for a composed stovetop meal.

    Steam-friendly vegetables share one covered pot instead of taking serial
    trips through a skillet. Aromatics may join ground meat when that produces
    the intended sauce base without sacrificing a distinct vegetable side.
    """
    if (
        _strategy(candidate) != "skillet"
        or _clean(candidate.get("meal_structure")) != "composed_plate"
    ):
        return activities

    steam_names = _steam_side_vegetables(candidate)
    steam_activities = [
        activity for activity in activities
        if activity.component in steam_names
        and activity.activity_type in {"cook", "saute"}
        and (activity.equipment or "").lower() == "burner"
    ]
    replacements: List[KitchenActivity] = []
    removed: List[KitchenActivity] = []
    replacement_ids: Dict[str, str] = {}

    if len(steam_activities) >= 2:
        old_ids = {_activity_id(activity) for activity in steam_activities}
        dependencies = list(dict.fromkeys(
            dependency
            for activity in steam_activities
            for dependency in activity.depends_on
            if dependency not in old_ids
        ))
        extras = [_clean(item) for item in candidate.get("selected_extras") or []]
        cheese = next((
            item for item in extras
            if "melting_cheese" in set(
                get_ingredient_profile(item, "ingredient").behavior_family_codes
            )
        ), "")
        milk = next((
            item for item in extras
            if "milk_cream" in set(
                get_ingredient_profile(item, "ingredient").behavior_family_codes
            )
        ), "")
        cheese_finish = ""
        extra_minutes = 0
        if cheese and milk:
            cheese_finish = (
                f" Transfer the vegetables to a serving bowl. In a small saucepan, warm {milk} gently; "
                f"remove it from direct heat and whisk in {cheese} a little at a time until smooth. "
                "Spoon the cheese sauce over the vegetables."
            )
            extra_minutes = 4
        elif cheese:
            cheese_finish = (
                f" Transfer the vegetables to a serving bowl, sprinkle with {cheese}, "
                "and cover briefly so the residual heat melts it."
            )
        shared = _planner_activity(
            "steam vegetable side",
            (
                "Fit a steamer basket inside a 3-quart saucepan and add about 1 inch of water, "
                "keeping the water below the basket. If you do not have a basket, put the vegetables "
                "directly in the saucepan with 1/2 inch of water instead. Bring it to a boil. "
                f"Add {_join(steam_names)}, cover, and steam together for 6–8 minutes. "
                "Stop when a fork enters the thickest pieces with slight resistance and no raw crunch."
                + cheese_finish
            ),
            minutes=8 + extra_minutes,
            human_busy=True,
            stage="middle",
            depends_on=dependencies,
            equipment="burner",
        )
        shared.attention_load = .45
        shared.activity_id = "steam vegetable side:meal"
        replacements.append(shared)
        removed.extend(steam_activities)
        replacement_ids.update({old_id: shared.activity_id for old_id in old_ids})

    protein = _clean(candidate.get("protein"))
    protein_profile = get_ingredient_profile(protein, "protein") if protein else None
    is_ground = "ground" in set(getattr(protein_profile, "physical_traits", ()))
    aromatic_names = [
        name for name in _split_joined_items(candidate.get("vegetable"))
        if name not in steam_names
        and "joins-sauce-base" in set(
            get_ingredient_profile(name, "vegetable").behavior_traits
        )
    ]
    protein_cook = next((
        activity for activity in activities
        if activity.component == protein and activity.activity_type == "cook"
    ), None)
    aromatic_activities = [
        activity for activity in activities
        if activity.component in aromatic_names
        and activity.activity_type in {"cook", "saute"}
        and (activity.equipment or "").lower() == "burner"
    ]
    if is_ground and protein_cook and aromatic_activities:
        grouped = [protein_cook, *aromatic_activities]
        old_ids = {_activity_id(activity) for activity in grouped}
        dependencies = list(dict.fromkeys(
            dependency for activity in grouped for dependency in activity.depends_on
            if dependency not in old_ids
        ))
        endpoint = resolve_behavior(
            protein, "protein", _clean(candidate.get("protein_state")), "skillet", DB_PATH
        ).method
        doneness = endpoint.doneness_cue.rstrip(".") if endpoint else "the meat reaches its verified safe temperature"
        shared = _planner_activity(
            "cook meat and aromatics",
            (
                f"Heat a 12-inch skillet over medium-high heat. Add {protein} and break it into small crumbles. "
                f"After about 3 minutes, add {_join(aromatic_names)} and continue cooking until softened and {doneness}. "
                "Color alone is not the safety test. Drain only excess fat, leaving a light coating for the sauce."
            ),
            minutes=max(10, int(protein_cook.minutes or 0)),
            human_busy=True,
            stage="middle",
            depends_on=dependencies,
            equipment="burner",
        )
        shared.attention_load = max(float(item.attention_load or 0) for item in grouped)
        shared.activity_id = "cook meat and aromatics:meal"
        replacements.append(shared)
        removed.extend(grouped)
        replacement_ids.update({old_id: shared.activity_id for old_id in old_ids})

    if not removed:
        return activities
    rewritten = []
    for activity in activities:
        if activity in removed:
            continue
        activity.depends_on = list(dict.fromkeys(
            replacement_ids.get(dependency, dependency)
            for dependency in activity.depends_on
        ))
        rewritten.append(activity)
    rewritten.extend(replacements)
    return rewritten


def apply_meal_coherence_gate(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Make public instructions honor the claimed dish identity and component roles."""
    dish_family = _clean(candidate.get("dish_family")).lower()
    title = _clean(candidate.get("title")).lower()
    is_hash = dish_family == "hash" or " hash" in title
    foundation = _clean(candidate.get("foundation"))
    foundation_codes = set(
        get_ingredient_profile(foundation, "foundation").behavior_family_codes
    ) if foundation else set()
    bread_side = component_by_archetype(candidate, "warmed_bread_side")

    for activity in activities:
        if is_hash and activity.activity_type in {"prep", "launch prep"}:
            for vegetable in _split_joined_items(candidate.get("vegetable")):
                if "steam-friendly" not in set(
                    get_ingredient_profile(vegetable, "vegetable").physical_traits
                ):
                    continue
                pattern = rf"Trim {re.escape(vegetable)} and cut it into evenly sized florets, wedges, or halves; include tender stems"
                activity.instruction = re.sub(
                    pattern,
                    f"Chop {vegetable} into even 1/2-inch pieces so it cooks as part of the hash",
                    activity.instruction,
                )
        if _clean(candidate.get("protein")).lower() == "ground beef":
            activity.instruction = activity.instruction.replace(
                "Beef reaches 160°F; poultry reaches 165°F in the center of the thickest clump",
                "Ground beef reaches 160°F in the center of several thick clumps",
            )
        if (
            foundation
            and "bread_wrap" in foundation_codes
            and activity.activity_type == "finish and serve"
        ):
            activity.instruction = (
                f"Spoon the finished hash onto plates. Serve {foundation} warm alongside it, "
                "with the pan sauce spooned over the hash rather than the bread."
            )
        if (
            bread_side
            and activity.component == foundation
            and activity.activity_type in {"cook", "warm", "reheat"}
        ):
            activity.instruction = (
                f"Place {foundation} on a small sheet pan and warm it in a 350°F oven until heated through, "
                "then cover loosely with a clean towel until serving."
            )
            activity.equipment = "oven"
        if foundation and "bread_wrap" in foundation_codes and activity.activity_type in {"prep", "launch prep"}:
            form = _clean((candidate.get("component_forms") or {}).get(foundation)).lower()
            if "frozen" not in form:
                activity.instruction = re.sub(
                    rf"Separate the amount of {re.escape(foundation)} needed and thaw it first when frozen",
                    f"Set aside the amount of {foundation} needed for serving",
                    activity.instruction,
                )
    return activities


def apply_component_plan_activities(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Compile recognized component archetypes into executable activities."""
    for component_plan in (candidate.get("component_plan") or {}).get("components") or []:
        if (
            component_plan.get("role") != "side"
            or component_plan.get("archetype") == "macaroni_and_cheese"
            or component_plan.get("knowledge_source") != "round_1_side_batch"
        ):
            continue
        names = [_clean(item.get("name")) for item in component_plan.get("ingredients") or [] if _clean(item.get("name"))]
        component_uses = {
            _clean(item.get("name")): item
            for item in component_plan.get("ingredients") or []
            if _clean(item.get("name"))
        }
        related = [
            activity for activity in activities
            if activity.component in names
            and activity.activity_type in {"cook", "saute", "warm", "reheat", "steam vegetable side"}
        ]
        instruction = side_activity_instruction(component_plan.get("archetype"), names)
        minutes = {
            "cold_assemble": 5, "warm": 4, "brief_heat": 6, "saute": 9,
            "steam": 8, "simmer": 8, "absorption_or_appliance": 25,
            "roast": 30, "bake": 35, "package_method": 30,
        }.get(component_plan.get("method"), 10)
        dependencies = list(dict.fromkeys(
            dependency for activity in related for dependency in activity.depends_on
        ))
        prep_lines = []
        prep_minutes = 0
        for name in names:
            use = component_uses.get(name) or {}
            job = _clean(use.get("job"))
            if job in {"seasoning", "acid", "fat", "sauce_fat", "sauce_liquid", "cheese"}:
                continue
            role = "foundation" if job in {"side_base", "pasta", "bread_side"} else "vegetable"
            form = _clean((candidate.get("component_forms") or {}).get(name))
            behavior = resolve_behavior(
                name, role, form, component_plan.get("method"), DB_PATH
            )
            if behavior.method and behavior.method.handling_template:
                prep_lines.append(behavior.method.handling_template.format(name=name))
                prep_minutes += int(behavior.method.prep_minutes or 0)
            elif "canned" in form.lower():
                prep_lines.append(f"Drain and rinse {name}.")
                prep_minutes += 1
        prep_id = ""
        if prep_lines:
            prep_activity = _planner_activity(
                "prep side",
                "Prepare the side ingredients:\n\n- " + "\n\n- ".join(prep_lines),
                minutes=max(1, prep_minutes), human_busy=True, stage="early",
                depends_on=["gather:meal"], equipment="counter",
            )
            prep_activity.component = component_plan.get("name") or "Side"
            prep_activity.activity_id = f"prep side:{component_plan.get('archetype')}"
            activities.append(prep_activity)
            prep_id = prep_activity.activity_id
        side_activity = _planner_activity(
            "prepare side", instruction, minutes=minutes,
            human_busy=component_plan.get("method") not in {"bake", "roast", "absorption_or_appliance"},
            stage="middle", depends_on=([prep_id] if prep_id else dependencies) or (["prep:meal"] if any(
                _activity_id(item) == "prep:meal" for item in activities
            ) else []),
            equipment="oven" if component_plan.get("method") in {"bake", "roast", "package_method"} else "burner",
        )
        side_activity.component = component_plan.get("name") or "Side"
        side_activity.activity_id = f"prepare side:{component_plan.get('archetype')}"
        replaced_ids = {_activity_id(item) for item in related}
        activities = [item for item in activities if item not in related]
        for activity in activities:
            activity.depends_on = list(dict.fromkeys(
                side_activity.activity_id if dependency in replaced_ids else dependency
                for dependency in activity.depends_on
            ))
            if activity.activity_type == "finish and serve":
                if side_activity.activity_id not in activity.depends_on:
                    activity.depends_on.append(side_activity.activity_id)
                activity.instruction = (
                    f"{activity.instruction.rstrip()} Serve {component_plan.get('name')} alongside."
                )
        activities.append(side_activity)

    component = component_by_archetype(candidate, "macaroni_and_cheese")
    if not component:
        return activities
    uses = {item.get("job"): item for item in component.get("ingredients") or []}
    pasta = _clean((uses.get("pasta") or {}).get("name"))
    cheese = _clean((uses.get("cheese") or {}).get("name"))
    milk = _clean((uses.get("sauce_liquid") or {}).get("name"))
    butter = _clean((uses.get("sauce_fat") or {}).get("name"))
    pasta_cook = next((
        activity for activity in activities
        if activity.component == pasta and activity.activity_type in {"cook", "reheat", "warm"}
    ), None)
    if not pasta_cook or not cheese:
        return activities

    pasta_cook.instruction = (
        f"Boil {pasta} in a large pot of salted water, stirring early. "
        "Before draining, reserve 1/2 cup pasta water. Drain when tender with no hard center."
    )
    pasta_cook.equipment = "burner"
    pasta_cook_id = _activity_id(pasta_cook)
    if milk:
        sauce_instruction = (
            f"Return the drained {pasta} to its pot over low heat. Add {butter + ' and ' if butter else ''}{milk}; "
            f"stir until warm, then remove the pot from direct heat and add {cheese} gradually. "
            "Stir until smooth, adding reserved pasta water a tablespoon at a time if the sauce is too thick. "
            "Stop before the sauce boils or the cheese becomes grainy."
        )
    else:
        sauce_instruction = (
            f"Return the drained {pasta} to its pot over low heat and melt {butter}. "
            f"Remove the pot from direct heat, add {cheese} gradually, and stir in reserved pasta water "
            "a tablespoon at a time until the pasta is smoothly coated."
        )
    finish = _planner_activity(
        "finish side",
        sauce_instruction,
        minutes=5,
        human_busy=True,
        stage="finish",
        depends_on=[pasta_cook_id],
        equipment="burner",
    )
    finish.component = component.get("name") or "Macaroni and cheese"
    finish.activity_id = "finish side:macaroni_and_cheese"

    for activity in activities:
        if activity is finish:
            continue
        activity.depends_on = list(dict.fromkeys(
            finish.activity_id if dependency == pasta_cook_id else dependency
            for dependency in activity.depends_on
        ))
        if activity.activity_type == "finish and serve":
            activity.instruction = (
                f"Plate the finished main component and serve {component.get('name')} alongside it. "
                "Keep any protein sauce with the protein rather than stirring it into the macaroni and cheese."
            )
            if finish.activity_id not in activity.depends_on:
                activity.depends_on.append(finish.activity_id)
    # The side itself must depend on the pasta cook, not on its own replacement.
    finish.depends_on = [pasta_cook_id]
    return [*activities, finish]


def apply_vegetable_relationship_intelligence(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Apply KO relationship/outcome rules before shared-vessel consolidation."""
    if _strategy(candidate) != "skillet":
        return activities
    structure = _clean(candidate.get("meal_structure")) or "integrated"
    vegetables = _split_joined_items(candidate.get("vegetable"))
    for activity in activities:
        if activity.component not in vegetables or activity.activity_type not in {"cook", "saute"}:
            continue
        rules = ingredient_relationships(activity.component)
        if not rules:
            continue
        traits = set(rules.get("behavior_traits") or ())
        if (
            {"party-cooked", "late-when-distinct"}.issubset(traits)
            and structure in {"layered_bowl", "composed_plate"}
        ):
            profile = get_ingredient_profile(activity.component, "vegetable")
            activity.activity_type = "finish produce"
            activity.instruction = (
                f"Keep {activity.component} distinct. {profile.handling_note} "
                "Serve it fresh, or briefly heat it only if a warm component is intended; "
                "stop before its pieces collapse into a sauce."
            )
            activity.minutes = max(2, profile.prep_minutes)
            activity.human_busy = True
            activity.attention_load = 1.0
            activity.stage = "finish"
            activity.equipment = "counter"
    return activities


def apply_protein_role_intelligence(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Turn extra proteins into accents/supports instead of duplicate entrées."""
    specs = [item for item in candidate.get("proteins") or [] if isinstance(item, dict)]
    if len(specs) < 2:
        return activities
    primary = _clean(specs[0].get("name"))
    primary_start = next((
        activity for activity in activities
        if activity.component == primary and activity.activity_type in {"cook", "saute", "reheat"}
    ), None)
    for spec in specs[1:]:
        name = _clean(spec.get("name"))
        role = _clean(spec.get("role")).lower() or "supporting"
        state = _clean(spec.get("state")).lower()
        protein_work = [
            activity for activity in activities
            if activity.component == name and activity.activity_type in {"cook", "saute", "reheat"}
        ]
        for activity in protein_work:
            profile = get_ingredient_profile(name, "protein")
            physical = set(profile.physical_traits)
            if role == "accent":
                fat_instruction = (
                    "leave only a light coating of the flavorful fat in the skillet"
                    if "fat-rendering" in physical else
                    "leave the skillet ready for the main protein"
                )
                activity.instruction = (
                    f"Cook {name} first until browned and safely cooked. Transfer it to a plate, {fat_instruction}, "
                    "and reserve it to fold into the meal near the end."
                )
                activity.minutes = max(6, int(activity.minutes or 0))
                activity.stage = "early"
                activity.attention_load = 0.65
                if primary_start and _activity_id(activity) not in primary_start.depends_on:
                    primary_start.depends_on.append(_activity_id(activity))
            elif state in {"cooked", "canned", "ready to eat"}:
                activity.activity_type = "reheat"
                activity.instruction = (
                    f"Fold in {name} near the end and heat it gently until hot; it is a {role} protein, so do not recook it."
                )
                activity.minutes = 4
                activity.stage = "late"
                activity.attention_load = 0.5
    return activities


def stage_ready_protein_after_sauce(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Warm canned/cooked protein only after the skillet sauce is ready.

    A ready-to-eat protein does not create fond and should not sit in the pan
    while a sauce is subsequently reduced.  Reversing that dependency keeps
    its final heat exposure short and makes "do not recook" operational rather
    than contradictory prose.
    """
    if _strategy(candidate) != "skillet":
        return activities
    sauce = next((
        activity for activity in activities
        if _activity_id(activity) == "finish sauce:meal"
    ), None)
    if sauce is None:
        return activities

    specs = [
        item for item in candidate.get("proteins") or []
        if isinstance(item, dict) and _clean(item.get("name"))
    ] or [{
        "name": _clean(candidate.get("protein")),
        "state": _clean(candidate.get("protein_state")),
    }]
    ready_names = {
        _clean(item.get("name")) for item in specs
        if _ready_to_eat_state(item.get("state"))
    }
    for activity in activities:
        if activity.component not in ready_names or activity.activity_type != "reheat":
            continue
        activity_id = _activity_id(activity)
        sauce.depends_on = [
            dependency for dependency in sauce.depends_on
            if dependency != activity_id
        ]
        if "finish sauce:meal" not in activity.depends_on:
            activity.depends_on.append("finish sauce:meal")
        activity.stage = "finish"
        activity.instruction = (
            f"Fold {activity.component} into the finished sauce and heat gently only until "
            "steaming hot. Do not continue simmering after it is hot."
        )
        activity.minutes = min(4, max(2, int(activity.minutes or 0)))
        activity.attention_load = min(.5, float(activity.attention_load or .5))
    return activities


def clarify_composed_skillet_transfers(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """State when a composed component leaves the shared skillet."""
    if (
        _strategy(candidate) != "skillet"
        or _clean(candidate.get("meal_structure")) != "composed_plate"
    ):
        return activities
    vegetables = set(_split_joined_items(candidate.get("vegetable")))
    for activity in activities:
        if (
            activity.component in vegetables
            and activity.activity_type in {"cook", "saute"}
            and (activity.equipment or "").lower() == "burner"
        ):
            activity.instruction = (
                activity.instruction.rstrip()
                + f" Transfer {activity.component} to a plate and keep it warm before reusing the skillet."
            )
    return activities


def consolidate_integrated_skillet_reheating(
    activities: List[KitchenActivity],
    candidate: dict,
) -> List[KitchenActivity]:
    """Bring ready-to-eat components into one skillet after browning/softening."""
    if (
        _strategy(candidate) != "skillet"
        or _clean(candidate.get("meal_structure")) == "composed_plate"
    ):
        return activities
    selected = {
        _clean(candidate.get("protein")),
        _clean(candidate.get("foundation")),
        *_split_joined_items(candidate.get("vegetable")),
    }
    reheats = [
        activity for activity in activities
        if activity.component in selected
        and activity.activity_type == "reheat"
        and (activity.equipment or "").lower() == "burner"
    ]
    if not reheats:
        return activities

    old_ids = {_activity_id(activity) for activity in reheats}
    dependencies = []
    for activity in reheats:
        for dependency in activity.depends_on:
            if dependency not in old_ids and dependency not in dependencies:
                dependencies.append(dependency)
    vegetable_gate = next((
        _activity_id(activity) for activity in activities
        if activity.activity_type in {"cook vegetables", "cook skillet"}
    ), None) or next((
        _activity_id(activity) for activity in activities
        if activity.component in _split_joined_items(candidate.get("vegetable"))
        and (activity.equipment or "").lower() == "burner"
        and activity.activity_type not in {"prep", "reheat"}
    ), None)
    if vegetable_gate and vegetable_gate not in dependencies:
        dependencies.append(vegetable_gate)

    foundation = _clean(candidate.get("foundation"))
    protein = _clean(candidate.get("protein"))
    instructions = []
    if any(activity.component == foundation for activity in reheats):
        foundation_profile = get_ingredient_profile(foundation, "foundation")
        foundation_functions = set(getattr(foundation_profile, "culinary_functions", ()))
        if "thickens" in foundation_functions:
            instructions.append(
                f"Stir in {foundation}; mash or purée some if desired, and heat it through."
            )
        else:
            instructions.append(f"Add {foundation} and heat it through.")
    if any(activity.component == protein for activity in reheats):
        instructions.append((
            f"Fold {protein} into the finished sauce and heat gently only until steaming hot. "
            "Do not continue simmering after it is hot."
            if "finish sauce:meal" in dependencies else
            f"Fold in {protein} near the end and heat it gently until hot; do not recook it."
        ))
    for activity in reheats:
        if activity.component not in {foundation, protein}:
            instructions.append(activity.instruction)

    shared = _planner_activity(
        "gentle reheat",
        " ".join(instructions),
        minutes=max(4, max(int(activity.minutes or 0) for activity in reheats) + (2 if len(reheats) > 1 else 0)),
        human_busy=True,
        stage="finish" if "finish sauce:meal" in dependencies else "late",
        depends_on=dependencies, equipment="burner",
    )
    shared.attention_load = max(float(activity.attention_load or 0) for activity in reheats)

    rewritten = []
    for activity in activities:
        if activity in reheats:
            continue
        activity.depends_on = list(dict.fromkeys(
            "gentle reheat:meal" if dependency in old_ids else dependency
            for dependency in activity.depends_on
        ))
        rewritten.append(activity)
    rewritten.append(shared)
    return rewritten


def constrain_single_skillet_environment(
    activities: List[KitchenActivity], candidate: dict,
) -> List[KitchenActivity]:
    """Serialize incompatible operations that require the meal's one skillet.

    Compatible ingredients have already been consolidated into shared
    activities. This pass protects those cooking environments from unrelated
    burner work while still allowing a separate foundation pot or appliance.
    """
    if _strategy(candidate) != "skillet":
        return activities
    foundation = _clean(candidate.get("foundation"))
    skillet_work = [
        activity for activity in activities
        if (activity.equipment or "").lower() == "burner"
        and activity.component != foundation
    ]
    stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
    position = {id(activity): index for index, activity in enumerate(activities)}
    vegetables = set(_split_joined_items(candidate.get("vegetable")))

    def work_order(activity):
        finish_order = (
            0 if activity.activity_type == "finish sauce"
            else 1 if activity.activity_type in {"reheat", "gentle reheat"}
            else 0
        )
        composed_long_first = (
            -int(activity.minutes or 0)
            if _clean(candidate.get("meal_structure")) == "composed_plate"
            and activity.component in vegetables
            and activity.activity_type in {"cook", "saute"}
            else 0
        )
        return (
            stage_order.get(activity.stage, 1), finish_order,
            composed_long_first, position[id(activity)],
        )

    # Respect culinary dependencies while serializing the physical skillet.
    # Sorting alone could put a ready protein before its sauce and then create
    # a dependency cycle when the skillet chain was added.
    pending = list(skillet_work)
    skillet_work = []
    while pending:
        pending_ids = {_activity_id(activity) for activity in pending}
        ready = [
            activity for activity in pending
            if not any(dependency in pending_ids for dependency in activity.depends_on)
        ]
        if not ready:
            # The graph validator will report the pre-existing cycle with its
            # exact activity IDs; do not invent another ordering here.
            skillet_work.extend(sorted(pending, key=work_order))
            break
        selected = min(ready, key=work_order)
        skillet_work.append(selected)
        pending.remove(selected)
    previous_id = None
    protein = _clean(candidate.get("protein"))
    protein_verify = next((
        _activity_id(activity) for activity in activities
        if activity.component == protein and activity.activity_type == "verify"
    ), None)
    for activity in skillet_work:
        activity.equipment = "skillet"
        activity_id = _activity_id(activity)
        dependency = (
            protein_verify
            if previous_id == f"cook:{protein}" and protein_verify
            else previous_id
        )
        if dependency and dependency not in activity.depends_on:
            activity.depends_on.append(dependency)
        previous_id = activity_id
    return activities



@dataclass
class ScheduledActivity:
    activity: KitchenActivity
    lane: str
    start_minute: int
    end_minute: int
    attention_minutes: int = 0


def _energy_attention_multiplier(candidate: dict) -> float:
    """Scale human work conservatively when the cook has less energy."""
    energy = _clean(candidate.get("user_energy") or candidate.get("energy")).lower()
    if "barely" in energy:
        return 2.0
    if "very low" in energy:
        return 1.6
    if "low" in energy:
        return 1.25
    return 1.0


def _activity_id(activity: KitchenActivity) -> str:
    return activity.activity_id or f"{activity.activity_type}:{activity.component}"


def assign_available_equipment(activities: List[KitchenActivity], candidate: dict) -> List[KitchenActivity]:
    """Route supported activities to household equipment before scheduling."""
    value = candidate.get("available_equipment") or []
    if isinstance(value, str):
        value = [item.strip() for item in value.split(",")]
    available = {_clean(item).lower() for item in value if _clean(item)}

    for activity in activities:
        if activity.activity_type != "thaw":
            continue
        activity.depends_on = ["gather:meal"]
        component = activity.component
        if (activity.equipment or "").lower() not in available:
            activity.equipment = "sink"
            activity.minutes = 30
            activity.human_busy = True
            activity.attention_load = 0.1
            activity.instruction = (
                f"Keep {component} in a leak-proof bag and submerge it in cold tap water. "
                "Allow about 30 minutes per pound, changing the water every 30 minutes; thicker packages "
                f"may need longer. Cook {component} immediately after thawing."
            )

    foundation_name = _clean(candidate.get("foundation"))
    rice_device = choose_rice_equipment(available)
    foundation_profile = get_ingredient_profile(foundation_name, "foundation") if foundation_name else None
    rice_capable = bool(
        set(getattr(foundation_profile, "behavior_family_codes", ()))
        & {"white_rice", "brown_rice"}
    )
    candidate["selected_rice_equipment"] = rice_device if rice_capable else ""
    if rice_capable and rice_device != "stovetop":
        removed = [activity for activity in activities if activity.component == foundation_name]
        removed_ids = {_activity_id(activity) for activity in removed}
        referenced = {
            dependency for activity in removed for dependency in activity.depends_on
            if dependency in removed_ids
        }
        terminals = [activity_id for activity_id in removed_ids if activity_id not in referenced]
        activities = [activity for activity in activities if activity.component != foundation_name]
        replacements = build_rice_equipment_activities(foundation_name, rice_device)
        activities.extend(replacements)
        replacement_ids = {_activity_id(activity) for activity in replacements}
        replacement_referenced = {
            dependency for activity in replacements for dependency in activity.depends_on
            if dependency in replacement_ids
        }
        new_terminal = next(
            (activity_id for activity_id in replacement_ids if activity_id not in replacement_referenced),
            "",
        )
        for activity in activities:
            if activity in replacements:
                continue
            activity.depends_on = [
                new_terminal if dependency in terminals else dependency
                for dependency in activity.depends_on
            ]
    return activities


def build_activity_graph(candidate: dict) -> Dict[str, KitchenActivity]:
    """Return the dependency graph keyed by stable activity identifiers."""
    graph: Dict[str, KitchenActivity] = {}
    activities = build_cooking_activities(candidate)
    activities = assign_available_equipment(activities, candidate)
    activities = consolidate_kitchen_activities(activities, candidate)
    if _strategy(candidate) == "skillet":
        prep_id = "prep:meal"
        if any(_activity_id(activity) == prep_id for activity in activities):
            for activity in activities:
                if (
                    activity.component == _clean(candidate.get("protein"))
                    and activity.activity_type in {"cook", "reheat"}
                    and prep_id not in activity.depends_on
                ):
                    activity.depends_on.append(prep_id)
    activities = apply_protein_role_intelligence(activities, candidate)
    activities = apply_vegetable_relationship_intelligence(activities, candidate)
    activities = stage_ready_protein_after_sauce(activities, candidate)
    activities = consolidate_composed_plate_components(activities, candidate)
    activities = clarify_composed_skillet_transfers(activities, candidate)
    activities = consolidate_skillet_vegetables(activities, candidate)
    activities = consolidate_integrated_skillet_reheating(activities, candidate)
    activities = apply_component_plan_activities(activities, candidate)
    activities = constrain_single_skillet_environment(activities, candidate)
    activities = consolidate_final_service(activities)
    activities = apply_meal_coherence_gate(activities, candidate)
    for activity in activities:
        activity.activity_id = _activity_id(activity)
        if activity.activity_id in graph:
            raise ValueError(f"Duplicate activity id: {activity.activity_id}")
        graph[activity.activity_id] = activity

    missing = {
        dependency
        for activity in graph.values()
        for dependency in activity.depends_on
        if dependency not in graph
    }
    if missing:
        raise ValueError(f"Unknown activity dependencies: {sorted(missing)}")
    return graph


def _just_in_time_starts(
    graph: Dict[str, KitchenActivity],
    candidate: Optional[dict] = None,
) -> Dict[str, int]:
    """Return target starts that make independent branches converge at service.

    Foundations and other slow, mostly passive work establish the meal's earliest
    finish. Shorter branches are held back so vegetables, proteins, and sauces do
    not spend their usable quality window sitting around before the meal is ready.
    Equipment and human-attention constraints remain authoritative when the real
    schedule is placed.
    """
    service_id = next((
        activity_id for activity_id, activity in graph.items()
        if activity.activity_type == "finish and serve"
    ), None)
    if not service_id:
        service_id = next((
            activity_id for activity_id, activity in reversed(list(graph.items()))
            if activity.stage == "finish"
            and activity.activity_type in {"serve casserole", "assemble", "plate"}
        ), None)
    if not service_id:
        return {}

    ancestors = {service_id}
    pending = [service_id]
    while pending:
        activity_id = pending.pop()
        for dependency in graph[activity_id].depends_on:
            if dependency not in ancestors:
                ancestors.add(dependency)
                pending.append(dependency)

    children = {activity_id: [] for activity_id in ancestors}
    for child_id in ancestors:
        for dependency in graph[child_id].depends_on:
            if dependency in ancestors:
                children[dependency].append(child_id)

    remaining_cache: Dict[str, int] = {}

    def remaining_minutes(activity_id: str) -> int:
        if activity_id not in remaining_cache:
            downstream = max(
                (remaining_minutes(child_id) for child_id in children[activity_id]),
                default=0,
            )
            remaining_cache[activity_id] = max(0, int(graph[activity_id].minutes or 0)) + downstream
        return remaining_cache[activity_id]

    roots = [
        activity_id for activity_id in ancestors
        if not any(dependency in ancestors for dependency in graph[activity_id].depends_on)
    ]
    meal_duration = max((remaining_minutes(activity_id) for activity_id in roots), default=0)
    targets = {
        activity_id: max(0, meal_duration - remaining_minutes(activity_id))
        for activity_id in ancestors
    }

    # A component cannot pause between continuous state transitions merely to
    # make the branches look symmetrical. Verification follows cooking, rest
    # follows removal from heat, and pressure release follows pressure cooking.
    for activity_id in ancestors:
        activity = graph[activity_id]
        if activity.activity_type not in {"verify", "rest", "natural release"}:
            continue
        same_component_dependencies = [
            dependency for dependency in activity.depends_on
            if graph[dependency].component == activity.component
        ]
        if same_component_dependencies:
            dependency = same_component_dependencies[-1]
            continuous_start = targets[dependency] + max(0, int(graph[dependency].minutes or 0))
            targets[activity_id] = min(targets[activity_id], continuous_start)

    # A low-attention state change such as microwave defrosting owns its
    # appliance for the full duration but does not own the cook. Pull general
    # prep into that released-attention window instead of placing it afterward.
    prep_id = "prep:meal"
    if prep_id in targets:
        attention_multiplier = _energy_attention_multiplier(candidate or {})
        hidden_pressure_cycles = [
            (activity_id, activity)
            for activity_id, activity in graph.items()
            if activity.activity_type == "pressure cycle"
            and not activity.show_in_plan
            and activity_id in targets
        ]
        if hidden_pressure_cycles:
            # Once the cook presses Start, the long appliance window becomes
            # the relaxed prep window for everything that cooks afterward.
            targets[prep_id] = min(
                targets[prep_id],
                min(targets[activity_id] for activity_id, _ in hidden_pressure_cycles),
            )
        for activity_id, activity in graph.items():
            duration = max(0, int(activity.minutes or 0))
            if (
                activity.activity_type == "thaw"
                and activity.human_busy
                and duration
                and 0 < float(activity.attention_load or 0) < 1
                and activity_id in targets
            ):
                attention = min(
                    duration,
                    max(1, ceil(duration * float(activity.attention_load) * attention_multiplier)),
                )
                targets[prep_id] = min(
                    targets[prep_id],
                    targets[activity_id] + attention,
                )
    return targets


def build_kitchen_lane_schedule(
    candidate: dict,
    burner_count: int = 2,
    human_attention_lanes: int = 1,
) -> List[ScheduledActivity]:
    """Create a conservative developer schedule constrained by equipment and attention.

    Each equipment unit is a lane. Human-busy work also reserves a human lane.
    This is the first feasibility scheduler, not the final optimizer.
    """
    graph = build_activity_graph(candidate)
    burner_count = max(1, int(burner_count or 1))
    human_attention_lanes = max(1, int(human_attention_lanes or 1))
    attention_multiplier = _energy_attention_multiplier(candidate)
    ideal_starts = _just_in_time_starts(graph, candidate)

    def place_schedule(start_targets: Dict[str, int]) -> List[ScheduledActivity]:
        lane_free = {f"Burner {i}": 0 for i in range(1, burner_count + 1)}
        lane_free.update({"Oven": 0, "Counter": 0})
        for graph_activity in graph.values():
            equipment = (graph_activity.equipment or "counter").lower()
            if equipment not in {"burner", "oven", "counter"}:
                lane_free.setdefault(equipment.title(), 0)
        human_free = [0] * human_attention_lanes
        completed: Dict[str, ScheduledActivity] = {}
        unscheduled = dict(graph)
        scheduled: List[ScheduledActivity] = []

        while unscheduled:
            ready = [
                activity for activity in unscheduled.values()
                if all(dep in completed for dep in activity.depends_on)
            ]
            if not ready:
                raise ValueError("Activity graph contains a cycle or unresolved dependency.")

            def placement_for(activity):
                dependency_end = max(
                    (completed[d].end_minute for d in activity.depends_on),
                    default=0,
                )

                equipment = (activity.equipment or "counter").lower()
                if equipment == "burner":
                    dependency_lanes = [
                        completed[dependency].lane
                        for dependency in activity.depends_on
                        if completed[dependency].lane.startswith("Burner ")
                        and completed[dependency].activity.component == activity.component
                    ]
                    lane = dependency_lanes[0] if dependency_lanes else min(
                        (name for name in lane_free if name.startswith("Burner ")),
                        key=lambda name: lane_free[name],
                    )
                elif equipment == "oven":
                    lane = "Oven"
                elif equipment not in {"counter", ""}:
                    lane = equipment.title()
                elif not activity.human_busy:
                    lane = f"Holding ({activity.component})"
                else:
                    lane = "Counter"

                lane_free.setdefault(lane, 0)
                start = max(
                    dependency_end,
                    lane_free[lane],
                    start_targets.get(_activity_id(activity), 0),
                )
                human_index = None
                if activity.human_busy:
                    human_index = min(
                        range(len(human_free)),
                        key=lambda i: human_free[i],
                    )
                    start = max(start, human_free[human_index])

                continues_component = any(
                    completed[dependency].activity.component == activity.component
                    for dependency in activity.depends_on
                )
                return start, lane, human_index, continues_component

            stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
            placements = [(*placement_for(activity), activity) for activity in ready]
            start, lane, human_index, continues_component, activity = min(
                placements,
                key=lambda item: (
                    item[0],
                    ideal_starts.get(_activity_id(item[4]), 0),
                    not (
                        item[4].activity_type == "thaw"
                        and (item[4].equipment or "").lower() == "sink"
                    ),
                    not item[3],
                    stage_order.get(item[4].stage, 1),
                    _activity_id(item[4]),
                ),
            )

            duration = max(0, int(activity.minutes or 0))
            attention_minutes = 0
            if activity.human_busy and duration:
                attention_minutes = min(
                    duration,
                    max(1, ceil(duration * float(activity.attention_load or 0) * attention_multiplier)),
                )
            end = start + duration
            item = ScheduledActivity(
                activity=activity, lane=lane, start_minute=start, end_minute=end,
                attention_minutes=attention_minutes,
            )
            scheduled.append(item)
            completed[_activity_id(activity)] = item
            lane_free[lane] = end
            if human_index is not None:
                human_free[human_index] = start + attention_minutes
            del unscheduled[_activity_id(activity)]

        return sorted(scheduled, key=lambda item: (item.start_minute, item.lane, item.end_minute))

    earliest_schedule = place_schedule({})
    earliest_finish = max((item.end_minute for item in earliest_schedule), default=0)
    if not ideal_starts:
        return earliest_schedule

    adjusted_targets = ideal_starts
    aligned_schedule = place_schedule(adjusted_targets)
    while max((item.end_minute for item in aligned_schedule), default=0) > earliest_finish:
        overrun = max(item.end_minute for item in aligned_schedule) - earliest_finish
        next_targets = {
            activity_id: max(0, start - overrun)
            for activity_id, start in adjusted_targets.items()
        }
        if next_targets == adjusted_targets:
            return earliest_schedule
        adjusted_targets = next_targets
        aligned_schedule = place_schedule(adjusted_targets)
    return aligned_schedule


def summarize_kitchen_lanes(candidate: dict, burner_count: int = 2, human_attention_lanes: int = 1) -> List[str]:
    """Return a compact developer view of resource-lane assignment."""
    schedule = build_kitchen_lane_schedule(candidate, burner_count, human_attention_lanes)
    lines = []
    for item in schedule:
        activity = item.activity
        attention = (
            f" + human {item.attention_minutes}m/{item.end_minute - item.start_minute}m"
            if activity.human_busy and item.end_minute > item.start_minute else ""
        )
        lines.append(
            f"{item.start_minute:>3}-{item.end_minute:<3} · {item.lane}{attention} · "
            f"{activity.activity_type}: {activity.component}"
        )
    return lines


def assess_time_feasibility(candidate: dict, available_minutes: int) -> dict:
    """Compare the meal's scheduled lead time with the available dinner window."""
    schedule = build_kitchen_lane_schedule(candidate)
    required = max((item.end_minute for item in schedule), default=0)
    available = max(0, int(available_minutes or 0))
    shortfall = max(0, required - available)
    return {
        "required_lead_minutes": required,
        "available_minutes": available,
        "time_feasible": shortfall == 0,
        "time_shortfall_minutes": shortfall,
    }


def calculate_effort_score(candidate: dict, schedule=None) -> int:
    """Calculate meal-level effort from the work in the finished schedule."""
    schedule = schedule if schedule is not None else build_kitchen_lane_schedule(candidate)
    hands_on_minutes = sum(item.attention_minutes for item in schedule)
    hands_on_tasks = sum(1 for item in schedule if item.attention_minutes > 0)
    equipment_lanes = {
        item.lane for item in schedule
        if item.attention_minutes > 0 and item.lane != "Counter"
    }
    raw_score = (
        hands_on_minutes / 4.0
        + hands_on_tasks / 6.0
        + max(0, len(equipment_lanes) - 1) * 0.5
    )
    return max(1, min(10, round(raw_score)))

def summarize_cooking_activities(candidate: dict) -> List[str]:
    """Return developer-readable evidence of activity ownership and semantics."""

    summaries = []
    for activity in build_cooking_activities(candidate):
        busy_note = "busy" if activity.human_busy else "passive"
        time_note = f"{activity.minutes} min" if activity.minutes else "no time"
        summaries.append(
            f"{activity.activity_type}: {activity.component} · {time_note} · "
            f"{busy_note} · {activity.stage} · {activity.source}"
        )
    return summaries

def build_cooking_plan(candidate: dict) -> List[CookingStep]:
    """
    Build a cooking timeline from a selected recipe candidate.

    Expected candidate keys may include:
    protein, vegetable, foundation, cuisine, sauce, strategy, label, minutes, servings.
    Missing fields are handled safely.
    """

    protein = _clean(candidate.get("protein"))
    vegetable = _clean(candidate.get("vegetable"))
    foundation = _clean(candidate.get("foundation"))
    sauce = _clean(candidate.get("sauce")) or "simple sauce"
    cuisine = _clean(candidate.get("cuisine")) or "Comfort Food"
    strategy = _strategy(candidate)
    protein_state = _clean(candidate.get("protein_state")) or "Fresh Raw"

    components = _join([protein, vegetable, foundation])
    steps: List[CookingStep] = []

    steps.append(CookingStep(
        order=10,
        phase="prep",
        instruction=f"Gather ingredients and prep {components} before turning on the heat.",
        minutes=10,
        parallel_ok=False,
    ))

    foundation_step = _foundation_step(foundation, strategy)
    if foundation_step:
        steps.append(foundation_step)

    if strategy == "soup":
        if vegetable:
            steps.append(CookingStep(
                order=30,
                phase="vegetable",
                instruction=f"Start {vegetable} in the pot and cook until it begins to soften.",
                minutes=8,
                parallel_ok=False,
            ))
        if protein:
            steps.append(CookingStep(
                order=40,
                phase="protein",
                instruction=f"Add {protein} and cook until it is safe and ready.",
                minutes=12,
                parallel_ok=False,
            ))
        steps.append(CookingStep(
            order=50,
            phase="simmer",
            instruction=f"Add liquid as needed, season toward {cuisine}, and use {sauce} as the flavor direction.",
            minutes=10,
            parallel_ok=False,
        ))
        steps.append(CookingStep(
            order=60,
            phase="finish",
            instruction="Simmer until everything is hot, cohesive, and spoon-tender.",
            minutes=5,
            parallel_ok=False,
        ))

    elif strategy == "skillet":
        protein_step = _protein_guidance_step(protein, strategy, protein_state)
        if protein_step:
            steps.append(protein_step)
        if vegetable:
            steps.extend(_vegetable_guidance_steps(vegetable, strategy))
        if foundation:
            steps.append(CookingStep(
                order=50,
                phase="combine",
                instruction=f"Add prepared {foundation} and heat through.",
                minutes=5,
                parallel_ok=False,
            ))
        steps.append(CookingStep(
            order=60,
            phase="finish",
            instruction=f"Stir in or season toward {sauce}; simmer briefly until hot and cohesive.",
            minutes=5,
            parallel_ok=False,
        ))

    elif strategy == "casserole":
        if protein:
            steps.append(CookingStep(
                order=30,
                phase="protein",
                instruction=f"Cook {protein} until safe.",
                minutes=12,
                parallel_ok=False,
            ))
        if vegetable:
            steps.append(CookingStep(
                order=40,
                phase="vegetable",
                instruction=f"Cook {vegetable} until softened.",
                minutes=8,
                parallel_ok=True,
            ))
        steps.append(CookingStep(
            order=50,
            phase="combine",
            instruction=f"Combine {_join([protein, vegetable, foundation])} with {sauce}.",
            minutes=5,
            parallel_ok=False,
        ))
        steps.append(CookingStep(
            order=60,
            phase="bake",
            instruction="Bake or heat until hot, cohesive, and ready to serve.",
            minutes=15,
            parallel_ok=False,
        ))

    elif strategy == "handheld":
        if protein:
            steps.append(CookingStep(
                order=30,
                phase="protein",
                instruction=f"Prepare {protein} as the main filling.",
                minutes=12,
                parallel_ok=False,
            ))
        if vegetable:
            steps.append(CookingStep(
                order=40,
                phase="vegetable",
                instruction=f"Prepare {vegetable} for texture and balance.",
                minutes=5,
                parallel_ok=True,
            ))
        steps.append(CookingStep(
            order=50,
            phase="assemble",
            instruction=f"Add {sauce}, then wrap, stack, or fold as a handheld meal.",
            minutes=5,
            parallel_ok=False,
        ))

    elif strategy == "kid_adventure":
        if protein:
            steps.append(CookingStep(
                order=30,
                phase="protein",
                instruction=f"Heat {protein} until hot and ready.",
                minutes=10,
                parallel_ok=False,
            ))
        if vegetable:
            steps.append(CookingStep(
                order=40,
                phase="vegetable",
                instruction=f"Prepare {vegetable} as the adventure side.",
                minutes=5,
                parallel_ok=True,
            ))
        steps.append(CookingStep(
            order=50,
            phase="plate",
            instruction=f"Serve {sauce} as the dip, lava pool, moat, or drizzle.",
            minutes=3,
            parallel_ok=False,
        ))
        steps.append(CookingStep(
            order=60,
            phase="fun_fact",
            instruction="Fun fact: real pterosaurs are extinct and were not dinosaurs, so DinoBites-style chicken is the near-enough dinner approximation.",
            minutes=None,
            parallel_ok=False,
        ))

    else:
        if protein:
            steps.append(CookingStep(
                order=30,
                phase="protein",
                instruction=f"Cook {protein} until safe and ready.",
                minutes=12,
                parallel_ok=False,
            ))
        if vegetable:
            steps.append(CookingStep(
                order=40,
                phase="vegetable",
                instruction=f"Cook or warm {vegetable} until it reaches the texture you like.",
                minutes=8,
                parallel_ok=True,
            ))
        steps.append(CookingStep(
            order=50,
            phase="finish",
            instruction=f"Season toward {cuisine} using {sauce}, then combine and serve.",
            minutes=5,
            parallel_ok=False,
        ))

    return sorted(steps, key=lambda step: step.order)


def _format_action_substeps(message: str) -> str:
    """Preserve authored breaks and separate sentence-sized cooking actions."""
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", message) if block.strip()]
    substeps = []
    for block in blocks:
        substeps.extend(
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", block)
            if part.strip()
        )
    return "\n\n".join(substeps)


def _planned_wait_after_prep(schedule: List[ScheduledActivity]):
    """Explain a conspicuous just-in-time pause after visible prep.

    Small gaps are normal kitchen breathing room. A gap longer than all visible
    prep plus three minutes is noticeable enough that the cook deserves to
    know it is deliberate rather than a missing instruction.
    """
    prep_items = [
        item for item in schedule
        if item.activity.activity_type in {"prep", "launch prep"}
        and item.activity.human_busy
        and item.activity.show_in_plan
        and item.end_minute > item.start_minute
    ]
    if not prep_items:
        return None, ""

    last_prep = max(prep_items, key=lambda item: item.end_minute)
    prep_end = last_prep.end_minute
    total_prep = sum(item.end_minute - item.start_minute for item in prep_items)
    next_action = next((
        item for item in schedule
        if item.start_minute >= prep_end
        and item.activity.human_busy
        and item.activity.show_in_plan
        and item.activity.activity_type not in {"gather", "prep", "launch prep"}
        and item.activity.instruction
    ), None)
    if not next_action:
        return None, ""

    wait_minutes = next_action.start_minute - prep_end
    if wait_minutes <= total_prep + 3:
        return None, ""

    blocker = next((
        item for item in schedule
        if not item.activity.human_busy
        and item.start_minute <= prep_end
        and item.end_minute >= next_action.start_minute
    ), None)
    if blocker:
        component = _clean(blocker.activity.component)
        reason = (
            f"{component} is still cooking, so starting the next component sooner would make it finish too early."
            if component and component.lower().replace("-", " ") != "meal"
            else "The current cooking step is still underway, so starting the next component sooner would make it finish too early."
        )
    else:
        reason = "The timing is intentional so the remaining components finish closer to serving time."
    return last_prep, (
        f"After prep, you’ll have about {wait_minutes} minutes before the next cooking step. {reason}"
    )


def generate_human_plan_items(candidate: dict) -> List[dict]:
    """Render interleaved information and actions for the public cooking plan."""

    schedule = build_kitchen_lane_schedule(candidate)
    wait_after_prep, wait_note = _planned_wait_after_prep(schedule)
    items = [
        {"kind": "info", "text": meal_introduction(candidate)},
    ]
    if _clean(candidate.get("quantity_note")):
        items.append({"kind": "info", "text": _clean(candidate.get("quantity_note"))})

    protein_components = [
        item.get("name") for item in candidate.get("proteins") or []
        if isinstance(item, dict)
    ] or [candidate.get("protein")]
    components = _join([
        *protein_components,
        *_split_joined_items(candidate.get("vegetable")),
        candidate.get("foundation"),
    ])
    if components:
        items.append({
            "kind": "info",
            "text": f"Before you begin, gather the ingredients and equipment for {components}.",
        })

    frozen_proteins = [
        _clean(item.get("name")) for item in candidate.get("proteins") or []
        if isinstance(item, dict) and _clean(item.get("state")).lower().replace("-", " ") == "frozen raw"
    ]
    if not frozen_proteins and _clean(candidate.get("protein_state")).lower().replace("-", " ") == "frozen raw":
        frozen_proteins = [_clean(candidate.get("protein"))]
    frozen_proteins = [name for name in frozen_proteins if name]
    if frozen_proteins:
        items.append({
            "kind": "info",
            "text": (
                f"Before Step 1, fully thaw {_join(frozen_proteins)}. "
                "The timed cooking plan assumes it is thawed and ready to cook."
            ),
        })

    previous_activity = None
    middle_cooking_end = max(
        (item.end_minute for item in schedule if item.activity.stage == "middle"),
        default=0,
    )
    previous_action_end = None
    for item in schedule:
        activity = item.activity
        if (
            activity.activity_type == "gather"
            or not activity.show_in_plan
            or not activity.instruction
            or item.end_minute <= item.start_minute
        ):
            continue

        transition = transition_message(previous_activity, activity)

        display_end_minute = item.end_minute
        if activity.activity_type == "prep":
            next_visible_action = next((
                other for other in schedule
                if other.start_minute >= item.end_minute
                and other.activity.human_busy
                and other.activity.show_in_plan
                and other.activity.activity_type != "gather"
            ), None)
            if next_visible_action and next_visible_action.start_minute > item.end_minute:
                hidden_appliance_window = any(
                    not other.activity.show_in_plan
                    and not other.activity.human_busy
                    and other.start_minute <= item.end_minute
                    and other.end_minute >= next_visible_action.start_minute
                    for other in schedule
                )
                if hidden_appliance_window and item is not wait_after_prep:
                    display_end_minute = next_visible_action.start_minute

        if (
            activity.activity_type == "shared simmer"
            and "60–90 minutes" in activity.instruction
        ):
            time_window = "About 60–90 minutes"
        else:
            time_window = f"Minutes {item.start_minute}–{display_end_minute}"

        message = activity_message(
            activity,
            duration=item.end_minute - item.start_minute,
            attention_minutes=item.attention_minutes,
        )
        overlapping_thaw = next((
            other for other in schedule
            if other is not item
            and other.activity.activity_type == "thaw"
            and other.start_minute < item.start_minute < other.end_minute
        ), None)
        if activity.activity_type == "prep" and overlapping_thaw:
            component = _clean(overlapping_thaw.activity.component).lower()
            message = message.replace(
                "Ingredient Prep:",
                f"While the microwave finishes defrosting the {component}, finish the remaining prep:",
                1,
            )
        if transition:
            if activity.stage == "middle":
                message = f"{transition} {message}"
            else:
                message = f"{message} {transition}"
        items.append({
            "kind": "action" if activity.human_busy else "info",
            "text": f"{time_window}: {(_format_action_substeps(message) if activity.human_busy else ' '.join(message.split()))}",
        })
        if item is wait_after_prep and wait_note:
            items.append({"kind": "info", "text": wait_note})
        if activity.human_busy:
            previous_action_end = max(previous_action_end or 0, display_end_minute)
        previous_activity = activity

    items.append({"kind": "info", "text": completion_message(candidate)})
    return items


def generate_equipment_list(candidate: dict) -> List[str]:
    """Consolidate activity requirements into concrete customer-facing tools."""
    schedule = build_kitchen_lane_schedule(candidate)
    instructions = " ".join(item.activity.instruction for item in schedule).lower()
    activity_types = {item.activity.activity_type for item in schedule}
    servings = max(1, int(candidate.get("servings") or 4))
    equipment: List[str] = []

    def add(item: str):
        normalized = _clean(item).lower()
        existing = {_clean(value).lower() for value in equipment}
        if normalized == "wooden spoon or heat-safe spatula" and existing & {"wooden spoon", "heat-safe spatula"}:
            return
        if item and normalized not in existing:
            equipment.append(item)

    for component in (candidate.get("component_plan") or {}).get("components") or []:
        for item in component.get("equipment") or []:
            add(_clean(item))

    rice_device = _clean(candidate.get("selected_rice_equipment"))
    if rice_device == "pressure cooker":
        add("Electric pressure cooker with locking lid and pressure valve")
    elif rice_device == "rice cooker":
        add("Rice cooker with inner pot and lid")
    elif rice_device == "microwave":
        add("Large microwave-safe bowl with vented cover")

    if "steam vegetable side" in activity_types:
        pot_size = "3-quart" if servings <= 4 else "4- to 5-quart"
        add(f"{pot_size} saucepan or pot with a tight-fitting lid")
        add("Steamer basket that fits inside the saucepan or pot (preferred, but optional)")
    if "skillet" in instructions or any(
        value in activity_types for value in {"cook skillet", "cook meat and aromatics"}
    ):
        skillet_size = "12-inch" if servings <= 4 else "large 14-inch or deep"
        add(f"{skillet_size} skillet")
        add("Wooden spoon or heat-safe spatula")
    if "small saucepan" in instructions:
        add("1- to 2-quart saucepan")
        if "whisk" in instructions:
            add("Whisk")
    if any((item.activity.equipment or "").lower() == "oven" for item in schedule):
        add("Oven")
    if any(
        _clean(item.get("state")).lower().replace("-", " ") in {"fresh raw", "frozen raw"}
        for item in candidate.get("proteins") or [] if isinstance(item, dict)
    ) or _clean(candidate.get("protein_state")).lower().replace("-", " ") in {"fresh raw", "frozen raw"}:
        add("Instant-read food thermometer")
    if "ingredient prep:" in instructions or re.search(r"\b(?:cut|slice|chop|dice|trim)\b", instructions):
        add("Cutting board and chef’s knife")
    if "measure" in instructions:
        add("Measuring cups and spoons")
    return equipment


def generate_human_instruction_steps(candidate: dict) -> List[str]:
    """Return all public plan statements as plain text for compatibility."""
    return [item["text"] for item in generate_human_plan_items(candidate)]

def generate_human_instructions(candidate: dict) -> str:
    """Return recipe steps as plain text for exports and diagnostics."""
    return "\n".join(generate_human_instruction_steps(candidate))
