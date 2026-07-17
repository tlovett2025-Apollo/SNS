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
from equipment_profiles import build_rice_equipment_activities, choose_rice_equipment
from sauce_profiles import get_sauce_profile
from planner_voice import (
    activity_message,
    completion_message,
    meal_introduction,
    time_summary,
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


def _extras_instruction(candidate: dict, strategy: str, phase: str = "finish") -> str:
    """Give every user-selected pantry/fridge extra an explicit job."""
    sauce_profile = get_sauce_profile(_clean(candidate.get("sauce")))
    sauce_keys = {
        _clean(item.name).lower() for item in (sauce_profile.ingredients if sauce_profile else [])
    }
    extras = [
        _clean(item) for item in candidate.get("selected_extras") or [] if _clean(item)
        and _clean(item).lower() not in sauce_keys
        and _clean(item).lower() != _clean(candidate.get("soup_liquid")).lower()
    ]
    if not extras:
        return ""
    family_codes = {
        item: set(get_ingredient_profile(item, "ingredient").behavior_family_codes)
        for item in extras
    }
    table_families = (
        {"cultured_creamy"}
        if strategy == "soup"
        else {"prepared_condiment", "cultured_creamy"}
    )
    table = [item for item in extras if family_codes[item] & table_families]
    cooking = [
        item for item in extras
        if item not in table
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


def _comfort_sauce_finish(candidate: dict, fallback: str) -> str:
    """Finish the sauce without instructing the cook to use rejected items."""
    if not candidate.get("inventory_requirements"):
        return fallback

    broth = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("broth_liquid",))), "")
    milk = next(iter(_resolved_requirements_by_ko(candidate, family_codes=("milk_cream",))), "")
    liquids = _join([broth, milk])
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
        activities.extend(get_ingredient_profile(name, "protein").publish_activities(strategy, state))
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

        sturdy_components = _join([*vegetables, foundation])
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
                f"Cover the pot and keep {protein or 'the soup ingredients'}, "
                f"{_join(vegetables)}, and {foundation or 'the remaining ingredients'} "
                f"together in the same pot. Gently simmer for about {simmer_minutes} minutes, "
                f"then check the KO tenderness cue: {tenderness_cue} "
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
        activities.append(_planner_activity(
            "finish soup",
            " ".join(filter(None, (
                "Taste the soup. Adjust salt and the other seasonings only as needed.",
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
        casserole_extras = _extras_instruction(candidate, strategy)
        activities.append(_planner_activity(
            "combine",
            " ".join(filter(None, (f"Combine {_join(components)} with {sauce}.", casserole_extras))),
            minutes=5,
            stage="finish",
            depends_on=component_finishes,
            equipment="counter",
        ))
        activities.append(_planner_activity(
            "bake",
            "Bake or heat until hot, cohesive, and ready to serve.",
            minutes=15,
            human_busy=False,
            stage="finish",
            depends_on=["combine:meal"],
            equipment="oven",
        ))
    elif strategy == "handheld":
        handheld_extras = _extras_instruction(candidate, strategy)
        activities.append(_planner_activity(
            "assemble",
            " ".join(filter(None, (
                f"Add {sauce}, then wrap, stack, or fold the prepared components.",
                handheld_extras,
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
        if protein_gate and protein_gate not in sauce_dependencies:
            sauce_dependencies.append(protein_gate)
        if strategy == "grill":
            finish_instruction = (
                f"Prepare {sauce} separately as a finishing sauce or table accompaniment. "
                "Keep it off the grill's direct flame and taste before serving."
            )
        else:
            finish_instruction = (
                _comfort_sauce_finish(candidate, sauce_profile.cook_instruction)
                if sauce_profile and sauce_profile.name == "simple comfort pan sauce"
                else sauce_profile.cook_instruction if sauce_profile
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
            activity.component in protein_names and activity.activity_type == "slice"
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
            service_instruction = (
                f"Divide {foundation} among plates or shallow bowls, then spoon everything in the skillet over it and serve immediately."
                if foundation and not any(
                    _clean(candidate.get("component_forms", {}).get(foundation)).lower() == value
                    for value in ("canned", "cooked", "ready to eat")
                ) else
                "Spoon everything in the skillet onto plates or into shallow bowls and serve immediately."
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
        if activity_type == "prep" and candidate:
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
                    r"\b(?:slice|sliced|slicing|chop|chopped|chopping|dice|diced|dicing)\b",
                    _clean(getattr(activity, "instruction", "")).lower(),
                )
                for activity in selected
            )

            if needs_cutting_allowance:
                calculated_minutes += 1
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
        "" if strategy == "soup"
        else _comfort_sauce_prep(candidate or {}, sauce_profile.prep_instruction)
        if sauce_profile and sauce_profile.name == "simple comfort pan sauce"
        else sauce_profile.prep_instruction if sauce_profile
        else (f"measure and mix {sauce}" if sauce else "")
    )
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

        old_activities = [protein_cook, *vegetable_activities]
        old_ids = {_activity_id(activity) for activity in old_activities}
        dependencies = []
        for activity in old_activities:
            for dependency in activity.depends_on:
                if dependency not in old_ids and dependency not in dependencies:
                    dependencies.append(dependency)

        vegetable_names = _join([activity.component for activity in vegetable_activities])
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
        has_sturdy_vegetable = any(
            profile.cook_minutes >= 8 or "long-lead-vegetable" in set(profile.behavior_traits)
            for profile in vegetable_profiles.values()
        )
        vegetable_minutes = "8–10" if has_sturdy_vegetable else "5–7"
        texture_targets = [
            f"{name} reaches this outcome: {profile.desired_outcome.rstrip('.')}"
            for name, profile in vegetable_profiles.items()
        ]
        texture_text = "; and ".join(texture_targets) or "the vegetables are tender"
        shared = _planner_activity(
            "cook skillet",
            (
                f"Heat the skillet, add {protein}, and break it into small crumbles. Cook for about 4 minutes. "
                + bloom_instruction
                + f"Add {vegetable_names} to the same skillet and cook for about {vegetable_minutes} minutes, "
                "stirring often enough to cook evenly but allowing brief contact with the pan for flavor. "
                f"Continue until {texture_text}, no pink "
                "ground meat remains, and every crumble is steaming hot. Keep stirring for about 30 seconds after "
                "the last pink disappears. If there is more than about 1 tablespoon of fat, drain only the excess "
                "and leave a light coating in the skillet for the sauce."
            ),
            minutes=max(14 if has_sturdy_vegetable else 11, int(protein_cook.minutes or 0)),
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
        instructions.append(
            f"Fold in {protein} near the end and heat it gently until hot; do not recook it."
        )
    for activity in reheats:
        if activity.component not in {foundation, protein}:
            instructions.append(activity.instruction)

    shared = _planner_activity(
        "gentle reheat",
        " ".join(instructions),
        minutes=max(4, max(int(activity.minutes or 0) for activity in reheats) + (2 if len(reheats) > 1 else 0)),
        human_busy=True, stage="late", depends_on=dependencies, equipment="burner",
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
    skillet_work.sort(key=lambda activity: (
        stage_order.get(activity.stage, 1), position[id(activity)]
    ))
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
                f"Keep the {component.lower()} in a leak-proof bag and submerge it in cold tap water. "
                "Allow about 30 minutes per pound, changing the water every 30 minutes; thicker packages "
                "may need longer. Cook it immediately after thawing."
            )

    foundation_name = _clean(candidate.get("foundation"))
    rice_device = choose_rice_equipment(available)
    candidate["selected_rice_equipment"] = rice_device
    foundation_profile = get_ingredient_profile(foundation_name, "foundation") if foundation_name else None
    rice_capable = bool(
        set(getattr(foundation_profile, "behavior_family_codes", ()))
        & {"white_rice", "brown_rice"}
    )
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
    activities = consolidate_skillet_vegetables(activities, candidate)
    activities = consolidate_integrated_skillet_reheating(activities, candidate)
    activities = constrain_single_skillet_environment(activities, candidate)
    activities = consolidate_final_service(activities)
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


def _wait_explanation(
    schedule: List[ScheduledActivity],
    start_minute: int,
    end_minute: int,
    next_activity: KitchenActivity,
) -> str:
    """Explain deliberate slack instead of presenting it as unexplained idleness."""
    ongoing = [
        item for item in schedule
        if not item.activity.human_busy
        and item.start_minute < end_minute
        and item.end_minute > start_minute
    ]
    progress = ""
    if ongoing:
        phases = {_clean(item.activity.activity_type).lower() for item in ongoing}
        current = ongoing[-1].activity
        component = _clean(current.component)
        activity_type = _clean(current.activity_type).lower()
        if len(phases & {"pressurize", "pressure cook", "natural release"}) > 1:
            progress = f"The {component.lower()} is in its longest unattended pressure-cooker window. "
        elif activity_type == "pressurize":
            progress = f"The {component.lower()} is coming to pressure. "
        elif activity_type == "pressure cook":
            progress = f"The {component.lower()} is pressure-cooking. "
        elif activity_type == "natural release":
            progress = f"The {component.lower()} is completing its natural pressure release. "
        elif component and component != "meal":
            progress = f"The {component.lower()} continues cooking without your attention. "

    if next_activity.activity_type == "thaw":
        component = _clean(next_activity.component).lower() or "protein"
        reason = (
            f"We are timing the defrosting so the {component} can move directly from thawing "
            "into prep and cooking instead of sitting while the other components catch up."
        )
    else:
        reason = (
            "This pause keeps the next component from finishing too early while the rest of "
            "the meal catches up."
        )
    return (
        f"Minutes {start_minute}–{end_minute}: {progress}{reason} "
        f"Begin the next step at minute {end_minute}."
    )


def generate_human_plan_items(candidate: dict) -> List[dict]:
    """Render interleaved information and actions for the public cooking plan."""

    schedule = build_kitchen_lane_schedule(candidate)
    items = [
        {"kind": "info", "text": meal_introduction(candidate)},
    ]
    summary = time_summary(
        candidate.get("minutes"),
        candidate.get("active_minutes"),
        candidate.get("passive_minutes"),
    )
    if summary:
        items.append({"kind": "info", "text": summary})
    if _clean(candidate.get("quantity_note")):
        items.append({"kind": "info", "text": _clean(candidate.get("quantity_note"))})

    components = _join([
        candidate.get("protein"),
        *_split_joined_items(candidate.get("vegetable")),
        candidate.get("foundation"),
    ])
    if components:
        items.append({
            "kind": "info",
            "text": f"Before you begin, gather the ingredients and equipment for {components}.",
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
                if hidden_appliance_window:
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
        if (
            activity.human_busy
            and previous_action_end is not None
            and item.start_minute > previous_action_end
        ):
            items.append({
                "kind": "info",
                "text": _wait_explanation(
                    schedule, previous_action_end, item.start_minute, activity
                ),
            })
        items.append({
            "kind": "action" if activity.human_busy else "info",
            "text": f"{time_window}: {(_format_action_substeps(message) if activity.human_busy else ' '.join(message.split()))}",
        })
        if activity.human_busy:
            previous_action_end = max(previous_action_end or 0, display_end_minute)
        previous_activity = activity

    items.append({"kind": "info", "text": completion_message(candidate)})
    return items


def generate_human_instruction_steps(candidate: dict) -> List[str]:
    """Return all public plan statements as plain text for compatibility."""
    return [item["text"] for item in generate_human_plan_items(candidate)]

def generate_human_instructions(candidate: dict) -> str:
    """Return recipe steps as plain text for exports and diagnostics."""
    return "\n".join(generate_human_instruction_steps(candidate))
