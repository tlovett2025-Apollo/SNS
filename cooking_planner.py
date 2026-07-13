"""
Cooking Timeline Engine for Stock & Stir / SNS.

This module turns a selected recipe candidate into ordered cooking steps.
It is intentionally practical and conservative: first make the engine work,
then deepen the cooking intelligence as more CKB fields become available.
"""

from dataclasses import dataclass, field
from math import ceil
from typing import Dict, List, Optional
from ingredient_profiles import KitchenActivity, get_ingredient_profile
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
    vegetables = _split_joined_items(candidate.get("vegetable"))
    foundation = _clean(candidate.get("foundation"))
    strategy = _clean(candidate.get("strategy")) or "plate"
    protein_state = _clean(candidate.get("protein_state")) or "Fresh Raw"
    sauce = _clean(candidate.get("sauce")) or "simple sauce"
    sauce_profile = get_sauce_profile(sauce)
    components = [item for item in [protein, *vegetables, foundation] if item]

    activities: List[KitchenActivity] = [
        _planner_activity(
            "gather",
            f"Gather the ingredients and equipment for {_join(components)}.",
            minutes=2,
            human_busy=True,
            stage="early",
            equipment="counter",
        )
    ]

    if foundation:
        activities.extend(
            get_ingredient_profile(foundation, "foundation").publish_activities(strategy)
        )
    if protein:
        activities.extend(
            get_ingredient_profile(protein, "protein").publish_activities(strategy, protein_state)
        )
    for vegetable in vegetables:
        activities.extend(
            get_ingredient_profile(vegetable, "vegetable").publish_activities(strategy)
        )

    component_finishes = [
        f"{activity.activity_type}:{activity.component}"
        for activity in activities
        if activity.source == "ko" and activity.stage in {"middle", "late", "finish"}
    ]

    ko_activities = [activity for activity in activities if activity.source == "ko"]
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
        prep_activities = [
            activity for activity in ko_activities
            if activity.activity_type == "prep"
        ]
        activities = [activities[0], *prep_activities]
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
        activities.append(_planner_activity(
            "build soup",
            (
                "In the same soup pot, add broth or water and scrape up any browned bits. "
                + (f"Add {sturdy_components}. " if sturdy_components else "")
                + (f"Keep {protein} in the pot. " if protein else "")
                + "Bring everything to a gentle simmer."
            ),
            minutes=3,
            human_busy=True,
            stage="middle",
            depends_on=previous,
            equipment="burner",
        ))

        protein_key = protein.lower()
        if any(word in protein_key for word in ["stew meat", "chuck", "brisket", "shoulder"]):
            simmer_minutes = 75
        elif raw_protein and any(word in protein_key for word in ["chicken", "turkey", "pork"]):
            simmer_minutes = 30
        else:
            simmer_minutes = 25
        activities.append(_planner_activity(
            "shared simmer",
            (
                f"Cover partially and gently simmer {protein or 'the soup ingredients'}, "
                f"{_join(vegetables)}, and {foundation or 'the remaining ingredients'} together in the same pot "
                "until the protein is safe and tender and the vegetables are cooked through."
            ),
            minutes=simmer_minutes,
            human_busy=False,
            stage="middle",
            depends_on=["build soup:meal"],
            equipment="burner",
        ))
        activities.append(_planner_activity(
            "finish soup",
            "Taste the soup. Adjust salt, pepper, richness, and acidity, then serve from the pot.",
            minutes=2,
            human_busy=True,
            stage="finish",
            depends_on=["shared simmer:meal"],
            equipment="burner",
        ))
        stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
        return sorted(
            activities,
            key=lambda activity: (stage_order.get(activity.stage, 1), activity.source != "ko"),
        )

    if strategy == "casserole":
        activities.append(_planner_activity(
            "combine",
            f"Combine {_join(components)} with {sauce}.",
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
        activities.append(_planner_activity(
            "assemble",
            f"Add {sauce}, then wrap, stack, or fold the prepared components.",
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
        mushroom_finish = terminal_ids(["Mushrooms"])
        chicken_cook = [
            _activity_id(activity)
            for activity in ko_activities
            if activity.component == protein and activity.activity_type in {"cook", "reheat"}
        ]
        activities.append(_planner_activity(
            "finish sauce",
            sauce_profile.cook_instruction if sauce_profile else f"Taste, adjust seasoning, and finish {sauce}; use the browned pan flavor when available.",
            minutes=sauce_profile.finish_minutes if sauce_profile else 3,
            stage="finish",
            depends_on=mushroom_finish or chicken_cook,
            equipment="burner",
        ))
        activities.append(_planner_activity(
            "finish and serve",
            (
                f"Plate {foundation or 'the foundation'} and {_join(vegetables)} with the finished sauce. "
                f"Slice {protein or 'the protein'} after its full rest, add it to the plates, and serve immediately."
            ),
            minutes=2,
            stage="finish",
            depends_on=(
                terminal_ids([*vegetables, foundation, protein])
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
        instructions = [activity.instruction.rstrip(".") for activity in selected]
        if extra_instruction:
            instructions.append(extra_instruction.rstrip("."))
        calculated_minutes = sum(max(0, int(activity.minutes or 0)) for activity in selected)
        if activity_type == "prep" and candidate:
            vegetables = _split_joined_items(candidate.get("vegetable"))
            calculated_minutes = len(vegetables)
            if vegetables:
                calculated_minutes += 1  # one shared slicing/dicing/modification allowance
            if _clean(candidate.get("protein")):
                calculated_minutes += 1
        heading = (
            "Start these first:"
            if activity_type == "launch prep"
            else "Ingredient Prep:"
        )
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
            stage="early" if activity_type == "launch prep" else "middle",
            parallel_ok=False,
            source="consolidator",
            activity_id="prep:launch" if activity_type == "launch prep" else "prep:meal",
        )

    replacements = []
    if launch_prep:
        replacements.append(consolidated_prep("launch prep", launch_prep, ["gather:meal"]))
    sauce = _clean((candidate or {}).get("sauce"))
    strategy = _clean((candidate or {}).get("strategy"))
    sauce_profile = get_sauce_profile(sauce)
    sauce_instruction = (
        "" if strategy == "soup"
        else sauce_profile.prep_instruction if sauce_profile
        else (f"measure and mix {sauce}" if sauce else "")
    )
    if general_prep or sauce_instruction:
        general_dependencies = launch_starts or ["gather:meal"]
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
    foundation_name = _clean(candidate.get("foundation"))
    rice_device = choose_rice_equipment(available)
    candidate["selected_rice_equipment"] = rice_device
    if "rice" in foundation_name.lower() and rice_device != "stovetop":
        activities = [activity for activity in activities if activity.component != foundation_name]
        activities.extend(build_rice_equipment_activities(foundation_name, rice_device))
        if rice_device == "pressure cooker":
            old_terminal = f"rest:{foundation_name}"
            new_terminal = f"natural release:{foundation_name}"
            for activity in activities:
                activity.depends_on = [
                    new_terminal if dependency == old_terminal else dependency
                    for dependency in activity.depends_on
                ]
    return activities


def build_activity_graph(candidate: dict) -> Dict[str, KitchenActivity]:
    """Return the dependency graph keyed by stable activity identifiers."""
    graph: Dict[str, KitchenActivity] = {}
    activities = build_cooking_activities(candidate)
    activities = assign_available_equipment(activities, candidate)
    activities = consolidate_kitchen_activities(activities, candidate)
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

    lane_free = {f"Burner {i}": 0 for i in range(1, burner_count + 1)}
    lane_free.update({"Oven": 0, "Counter": 0})
    for activity in graph.values():
        equipment = (activity.equipment or "counter").lower()
        if equipment not in {"burner", "oven", "counter"}:
            lane_free.setdefault(equipment.title(), 0)
    human_free = [0] * human_attention_lanes
    completed: Dict[str, ScheduledActivity] = {}
    unscheduled = dict(graph)
    scheduled: List[ScheduledActivity] = []
    attention_multiplier = _energy_attention_multiplier(candidate)

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

            start = max(dependency_end, lane_free[lane])
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
        placements = [
            (*placement_for(activity), activity)
            for activity in ready
        ]
        start, lane, human_index, continues_component, activity = min(
            placements,
            key=lambda item: (
                item[0],
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
    strategy = _clean(candidate.get("strategy")) or "plate"
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


def generate_human_instruction_steps(candidate: dict) -> List[str]:
    """Render the scheduled activity graph in the Stock & Stir kitchen voice."""

    schedule = build_kitchen_lane_schedule(candidate)
    lines = [meal_introduction(candidate)]

    summary = time_summary(
        candidate.get("minutes"),
        candidate.get("active_minutes"),
        candidate.get("passive_minutes"),
    )
    if summary:
        lines.append(summary)

    previous_activity = None
    for item in schedule:
        activity = item.activity
        if not activity.instruction or item.end_minute <= item.start_minute:
            continue

        transition = transition_message(previous_activity, activity)
        if transition:
            lines.append(transition)

        time_window = f"Minutes {item.start_minute}–{item.end_minute}"
        message = activity_message(
            activity,
            duration=item.end_minute - item.start_minute,
            attention_minutes=item.attention_minutes,
        )
        lines.append(f"{time_window}: {message}")
        previous_activity = activity

    lines.append(completion_message(candidate))
    return lines

def generate_human_instructions(candidate: dict) -> str:
    """Return recipe steps as plain text for exports and diagnostics."""
    return "\n".join(generate_human_instruction_steps(candidate))
