"""Declarative whole-meal coordination contracts for SNS."""

from dataclasses import asdict, dataclass


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


@dataclass(frozen=True)
class MealShapeContract:
    code: str
    label: str
    service_pattern: str
    component_rule: str
    source: str = "sns_orchestration_round_4"


MEAL_SHAPES = {
    "integrated": MealShapeContract(
        "integrated", "Cooked Together", "one hot finished vessel",
        "Components join in trained stages and finish in the same vessel.",
    ),
    "composed_plate": MealShapeContract(
        "composed_plate", "Main + Sides", "plate together",
        "Main and sides keep distinct methods and converge at service.",
    ),
    "layered_bowl": MealShapeContract(
        "layered_bowl", "Layered Bowl", "assemble in layers",
        "Foundation, toppings, sauce, and main remain texturally distinct.",
    ),
    "soup": MealShapeContract(
        "soup", "Soup or Stew", "ladle from one vessel",
        "Ingredients join according to tenderness and reheating tolerance.",
    ),
    "casserole": MealShapeContract(
        "casserole", "Casserole / One Dish", "rest then portion",
        "Components are made bake-ready before final assembly.",
    ),
    "handheld": MealShapeContract(
        "handheld", "Handheld", "assemble immediately before serving",
        "Wet, crisp, and bread components stay separate until assembly.",
    ),
    "cold_meal": MealShapeContract(
        "cold_meal", "Cold Meal", "chill or assemble cold",
        "Ready components remain food-safe and are dressed near service.",
    ),
    "oven_roast": MealShapeContract(
        "oven_roast", "Roasted Main + Sides", "rest main, then plate",
        "The main roasts while separately trained sides use available lanes.",
    ),
}


def shape_contract(candidate) -> MealShapeContract:
    structure = _clean(candidate.get("meal_structure"))
    method = _clean(candidate.get("cooking_method") or candidate.get("strategy"))
    if structure in {"composed_plate", "layered_bowl"}:
        return MEAL_SHAPES[structure]
    return MEAL_SHAPES.get(method, MEAL_SHAPES["integrated"])


def attention_mode(activity) -> str:
    if not getattr(activity, "human_busy", False):
        return "passive"
    load = float(getattr(activity, "attention_load", 0) or 0)
    if load >= .75:
        return "continuous"
    if load > .15:
        return "intermittent"
    return "launch_and_check"


def build_orchestration_report(candidate, schedule) -> dict:
    """Describe resource use, legal interlacing, holding, and service convergence."""
    contract = shape_contract(candidate)
    service_items = [
        item for item in schedule
        if _clean(getattr(item.activity, "activity_type", ""))
        in {"finish and serve", "serve casserole", "assemble", "plate"}
    ]
    final_service_items = [
        item for item in service_items
        if _clean(getattr(item.activity, "activity_type", ""))
        in {"finish and serve", "serve casserole", "plate"}
    ] or service_items
    service_minute = min(
        (item.start_minute for item in final_service_items),
        default=max((item.end_minute for item in schedule), default=0),
    )
    lanes = sorted({item.lane for item in schedule})
    attention_windows = []
    for item in schedule:
        if not item.attention_minutes:
            continue
        attention_windows.append({
            "activity_id": getattr(item.activity, "activity_id", ""),
            "component": _clean(getattr(item.activity, "component", "")),
            "mode": attention_mode(item.activity),
            "start_minute": item.start_minute,
            "attention_end_minute": item.start_minute + item.attention_minutes,
            "process_end_minute": item.end_minute,
            "interlace_after_launch": (
                attention_mode(item.activity) == "intermittent"
                and item.attention_minutes < item.end_minute - item.start_minute
            ),
        })

    concurrent_windows = []
    for index, left in enumerate(schedule):
        for right in schedule[index + 1:]:
            start = max(left.start_minute, right.start_minute)
            end = min(left.end_minute, right.end_minute)
            if start < end and left.lane != right.lane:
                concurrent_windows.append({
                    "start_minute": start,
                    "end_minute": end,
                    "lanes": sorted({left.lane, right.lane}),
                })

    # The scheduler reserves a single cook's attention at the beginning of
    # each busy activity. Verify that those reservations never overlap.
    conflicts = []
    for index, left in enumerate(attention_windows):
        for right in attention_windows[index + 1:]:
            if max(left["start_minute"], right["start_minute"]) < min(
                left["attention_end_minute"], right["attention_end_minute"]
            ):
                conflicts.append([left["activity_id"], right["activity_id"]])

    component_finishes = {}
    for item in schedule:
        component = _clean(getattr(item.activity, "component", ""))
        activity_type = _clean(getattr(item.activity, "activity_type", ""))
        if not component or component.lower() == "meal" or item in service_items:
            continue
        if activity_type in {"gather", "prep", "launch prep", "thaw"}:
            continue
        component_finishes[component] = max(
            component_finishes.get(component, 0), item.end_minute
        )
    hold_windows = [
        {
            "component": component,
            "ready_minute": ready,
            "service_minute": service_minute,
            "hold_minutes": max(0, service_minute - ready),
            "quality_risk": "review" if service_minute - ready > 15 else "normal",
        }
        for component, ready in sorted(component_finishes.items())
        if ready <= service_minute
    ]

    return {
        "shape": asdict(contract),
        "service_minute": service_minute,
        "lanes": lanes,
        "attention_windows": attention_windows,
        "concurrent_windows": concurrent_windows,
        "hold_windows": hold_windows,
        "attention_conflicts": conflicts,
        "single_cook_feasible": not conflicts,
    }
