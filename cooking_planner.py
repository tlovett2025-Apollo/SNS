"""
Cooking Timeline Engine for Stock & Stir / SNS.

This module turns a selected recipe candidate into ordered cooking steps.
It is intentionally practical and conservative: first make the engine work,
then deepen the cooking intelligence as more CKB fields become available.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ingredient_profiles import KitchenActivity, get_ingredient_profile


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
    elif strategy == "soup":
        activities.append(_planner_activity(
            "simmer",
            f"Bring the prepared components together with liquid and season toward {sauce}.",
            minutes=10,
            human_busy=False,
            stage="finish",
            depends_on=component_finishes,
            equipment="burner",
        ))
    else:
        activities.append(_planner_activity(
            "finish",
            f"Bring the prepared components together and season toward {sauce}.",
            minutes=5,
            stage="finish",
            depends_on=component_finishes,
            equipment="burner",
        ))

    stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
    return sorted(
        activities,
        key=lambda activity: (stage_order.get(activity.stage, 1), activity.source != "ko"),
    )



@dataclass
class ScheduledActivity:
    activity: KitchenActivity
    lane: str
    start_minute: int
    end_minute: int


def _activity_id(activity: KitchenActivity) -> str:
    return activity.activity_id or f"{activity.activity_type}:{activity.component}"


def build_activity_graph(candidate: dict) -> Dict[str, KitchenActivity]:
    """Return the dependency graph keyed by stable activity identifiers."""
    graph: Dict[str, KitchenActivity] = {}
    for activity in build_cooking_activities(candidate):
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
                lane = min(
                    (name for name in lane_free if name.startswith("Burner ")),
                    key=lambda name: lane_free[name],
                )
            elif equipment == "oven":
                lane = "Oven"
            else:
                lane = "Counter"

            start = max(dependency_end, lane_free[lane])
            human_index = None
            if activity.human_busy:
                human_index = min(
                    range(len(human_free)),
                    key=lambda i: human_free[i],
                )
                start = max(start, human_free[human_index])

            return start, lane, human_index

        stage_order = {"early": 0, "middle": 1, "late": 2, "finish": 3}
        placements = [
            (*placement_for(activity), activity)
            for activity in ready
        ]
        start, lane, human_index, activity = min(
            placements,
            key=lambda item: (
                item[0],
                stage_order.get(item[3].stage, 1),
                _activity_id(item[3]),
            ),
        )

        duration = max(0, int(activity.minutes or 0))
        end = start + duration
        item = ScheduledActivity(activity=activity, lane=lane, start_minute=start, end_minute=end)
        scheduled.append(item)
        completed[_activity_id(activity)] = item
        lane_free[lane] = end
        if human_index is not None:
            human_free[human_index] = end
        del unscheduled[_activity_id(activity)]

    return sorted(scheduled, key=lambda item: (item.start_minute, item.lane, item.end_minute))


def summarize_kitchen_lanes(candidate: dict, burner_count: int = 2, human_attention_lanes: int = 1) -> List[str]:
    """Return a compact developer view of resource-lane assignment."""
    schedule = build_kitchen_lane_schedule(candidate, burner_count, human_attention_lanes)
    lines = []
    for item in schedule:
        activity = item.activity
        attention = " + human" if activity.human_busy else ""
        lines.append(
            f"{item.start_minute:>3}-{item.end_minute:<3} · {item.lane}{attention} · "
            f"{activity.activity_type}: {activity.component}"
        )
    return lines

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


def generate_human_instructions(candidate: dict) -> str:
    """
    Convert the cooking plan into readable timeline instructions.
    """

    steps = build_cooking_plan(candidate)
    blocks = build_timeline_blocks(steps)
    lines = []

    total_minutes = candidate.get("minutes")
    active_minutes = candidate.get("active_minutes")
    passive_minutes = candidate.get("passive_minutes")

    if total_minutes is not None:
        lines.append(
            f"Estimated meal time: {total_minutes} minutes "
            f"({active_minutes or 0} active, {passive_minutes or 0} passive). "
            "Some steps may overlap, so step times are guidance rather than a strict sequence."
        )

    for block in blocks:
        if len(block.steps) == 1:
            step = block.steps[0]
            time_note = f" ({step.minutes} min)" if step.minutes else ""
            lines.append(f"Stage {block.stage}: {step.instruction}{time_note}")
        else:
            lines.append(f"Stage {block.stage}: Work on these components in parallel:")
            for step in block.steps:
                time_note = f" ({step.minutes} min)" if step.minutes else ""
                lines.append(f"  - {step.instruction}{time_note}")

    return "\n".join(lines)
