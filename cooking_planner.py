"""
Cooking Timeline Engine for Stock & Stir / SNS.

V5 fixes:
- no embedded step numbers
- chicken drumsticks use real bone-in timing
- mushrooms behave like mushrooms
- active/passive/attention/down-day metrics are calculated
- multiple vegetables supported by the planner backend
"""

from dataclasses import dataclass
from typing import Dict, List

from ingredient_profiles import get_ingredient_profile, get_ingredient_profiles


def _clean(value):
    return "" if value is None else str(value).strip()


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value if _clean(v)]
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in text.replace(" & ", ",").split(",") if part.strip()]


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
    if len(cleaned) == 2:
        return " & ".join(cleaned)
    return ", ".join(cleaned[:-1]) + f" & {cleaned[-1]}"


def _strip_number_prefix(text: str) -> str:
    """Defensive cleanup in case older instruction text gets routed through here."""
    text = _clean(text)
    while True:
        parts = text.split(". ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            text = parts[1].strip()
        else:
            return text


def _technique_for_strategy(strategy: str, role: str) -> str:
    strategy = _clean(strategy).lower()
    if role == "foundation":
        if strategy == "casserole":
            return "bake"
        if strategy == "soup":
            return "simmer"
        return "reheat"
    if strategy == "soup":
        return "simmer"
    if strategy == "casserole":
        return "bake"
    # quick_bowl is not necessarily reheat; raw proteins still need real cooking.
    return "skillet"


def _foundation_technique(profile, strategy: str) -> str:
    """Ask the foundation baby how it should be handled in this meal shape.

    Bread-like foundations, such as biscuits, should not be described as simmered
    or stirred into the pan. Rice/beans/potatoes can usually be started or warmed.
    """
    if not profile:
        return "reheat"
    strategy = _clean(strategy).lower()
    category = _clean(getattr(profile, "category", "")).lower()
    name = _clean(getattr(profile, "name", "")).lower()

    if strategy == "casserole" and "bake" in profile.experiences:
        return "bake"
    if strategy == "soup" and "simmer" in profile.experiences:
        return "simmer"
    if category in {"bread", "tortilla"} or any(word in name for word in ["biscuit", "roll", "bread", "toast"]):
        return "reheat"
    if "simmer" in profile.experiences and category in {"rice", "beans", "grain"}:
        return "simmer"
    if "reheat" in profile.experiences:
        return "reheat"
    return _technique_for_strategy(strategy, "foundation")


@dataclass
class CookingStep:
    order: int
    phase: str
    instruction: str
    total_minutes: int = 0
    active_minutes: int = 0
    passive_minutes: int = 0
    attention_score: int = 0
    cleanup_score: int = 0
    forgiveness_score: int = 0
    parallel_ok: bool = False
    note: str = ""

    @property
    def minutes(self):
        return self.total_minutes


@dataclass
class CookingPlan:
    steps: List[CookingStep]
    total_minutes: int
    active_minutes: int
    passive_minutes: int
    attention_score: int
    cleanup_score: int
    forgiveness_score: int
    down_day_score: int
    energy_fit: str

    def summary_line(self) -> str:
        return (
            f"Total {self.total_minutes} min · Active {self.active_minutes} min · "
            f"Passive {self.passive_minutes} min · Attention {self.attention_score}/10 · "
            f"Down-day fit: {self.energy_fit}"
        )


def _make_step(order: int, phase: str, profile, technique: str) -> CookingStep:
    exp = profile.experience_for(technique)
    instruction = exp.instruction or f"Cook {profile.name} until ready."
    if exp.note:
        instruction = f"{instruction} {exp.note}"
    return CookingStep(
        order=order,
        phase=phase,
        instruction=_strip_number_prefix(instruction),
        total_minutes=exp.total_minutes,
        active_minutes=exp.active_minutes,
        passive_minutes=exp.passive_minutes,
        attention_score=exp.attention_score,
        cleanup_score=exp.cleanup_score,
        forgiveness_score=exp.forgiveness_score,
        parallel_ok=exp.parallel_ok,
        note=exp.note,
    )


def _component_profiles(candidate: dict):
    protein = _clean(candidate.get("protein"))
    foundation = _clean(candidate.get("foundation"))

    vegetable_names = candidate.get("vegetables")
    if vegetable_names is None:
        vegetable_names = candidate.get("vegetable")

    protein_profile = get_ingredient_profile(protein, "protein") if protein else None
    foundation_profile = get_ingredient_profile(foundation, "foundation") if foundation else None
    vegetable_profiles = get_ingredient_profiles(_as_list(vegetable_names), "vegetable")
    return protein_profile, vegetable_profiles, foundation_profile


def _prep_step(component_names, protein_profile, vegetable_profiles, foundation_profile) -> CookingStep:
    profiles = [p for p in [protein_profile, foundation_profile] if p] + list(vegetable_profiles)
    prep_minutes = sum(max(0, p.prep_minutes) for p in profiles)
    prep_minutes = max(5, min(prep_minutes, 20)) if profiles else 5
    return CookingStep(
        order=10,
        phase="prep",
        instruction=f"Gather ingredients and prep {_join(component_names)} before turning on the heat.",
        total_minutes=prep_minutes,
        active_minutes=prep_minutes,
        passive_minutes=0,
        attention_score=3,
        cleanup_score=1,
        forgiveness_score=8,
        parallel_ok=False,
    )


def _summarize_timing(steps: List[CookingStep]):
    # Active minutes are mostly additive. Passive minutes overlap, so use the largest
    # passive block plus a small allowance for passive pieces that cannot overlap.
    active_minutes = sum(max(0, s.active_minutes) for s in steps)
    largest_passive = max([s.passive_minutes for s in steps] + [0])
    extra_passive = sum(s.passive_minutes for s in steps if s.passive_minutes and not s.parallel_ok)
    passive_minutes = max(largest_passive, extra_passive)
    total_minutes = active_minutes + passive_minutes
    attention_score = max([s.attention_score for s in steps] + [0])
    cleanup_score = max([s.cleanup_score for s in steps] + [0])
    forgiveness_values = [s.forgiveness_score for s in steps if s.forgiveness_score]
    forgiveness_score = round(sum(forgiveness_values) / len(forgiveness_values)) if forgiveness_values else 5
    down_day_score = max(1, active_minutes + attention_score + cleanup_score - forgiveness_score)

    if active_minutes <= 12 and attention_score <= 4:
        energy_fit = "Good"
    elif active_minutes <= 22 and attention_score <= 6:
        energy_fit = "Okay"
    else:
        energy_fit = "Hard"

    return total_minutes, active_minutes, passive_minutes, attention_score, cleanup_score, forgiveness_score, down_day_score, energy_fit


def build_cooking_plan(candidate: dict) -> CookingPlan:
    strategy = _clean(candidate.get("strategy")) or "plate"
    sauce = _clean(candidate.get("sauce")) or "simple sauce"
    cuisine = _clean(candidate.get("cuisine")) or "Comfort Food"

    protein_profile, vegetable_profiles, foundation_profile = _component_profiles(candidate)
    component_names = []
    if protein_profile:
        component_names.append(protein_profile.name)
    component_names.extend([v.name for v in vegetable_profiles])
    if foundation_profile:
        component_names.append(foundation_profile.name)

    steps: List[CookingStep] = [_prep_step(component_names, protein_profile, vegetable_profiles, foundation_profile)]

    # Foundations usually start first because they hold better than proteins/vegetables.
    if foundation_profile:
        foundation_technique = _foundation_technique(foundation_profile, strategy)
        steps.append(_make_step(20, "foundation", foundation_profile, foundation_technique))

    stage_order = {"early": 35, "middle": 45, "late": 55}
    vegetables_by_stage = sorted(vegetable_profiles, key=lambda v: stage_order.get(v.add_stage, 45))

    if strategy == "soup":
        for veg in vegetables_by_stage:
            steps.append(_make_step(stage_order.get(veg.add_stage, 45), "vegetable", veg, "simmer"))
        if protein_profile:
            steps.append(_make_step(40, "protein", protein_profile, "simmer"))
        steps.append(CookingStep(
            order=70,
            phase="finish",
            instruction=f"Add liquid as needed, season toward {cuisine}, and use {sauce} as the flavor direction. Simmer until cohesive and spoon-tender.",
            total_minutes=5,
            active_minutes=2,
            passive_minutes=3,
            attention_score=2,
            cleanup_score=1,
            forgiveness_score=8,
            parallel_ok=False,
        ))
    elif strategy == "casserole":
        if protein_profile:
            # Many proteins still need browning before casserole assembly.
            steps.append(_make_step(30, "protein", protein_profile, "skillet"))
        for veg in vegetables_by_stage:
            steps.append(_make_step(stage_order.get(veg.add_stage, 45), "vegetable", veg, "skillet"))
        steps.append(CookingStep(
            order=70,
            phase="combine",
            instruction=f"Combine {_join(component_names)} with {sauce}, then bake or heat until hot and cohesive.",
            total_minutes=15,
            active_minutes=5,
            passive_minutes=10,
            attention_score=2,
            cleanup_score=3,
            forgiveness_score=7,
            parallel_ok=False,
        ))
    else:
        # quick_bowl, skillet, plate, handheld, kid_adventure all need real component behavior.
        if protein_profile:
            steps.append(_make_step(30, "protein", protein_profile, "skillet"))
        for veg in vegetables_by_stage:
            steps.append(_make_step(stage_order.get(veg.add_stage, 45), "vegetable", veg, "skillet"))
        if foundation_profile and strategy in {"skillet", "handheld", "plate", "quick_bowl", "kid_adventure"}:
            foundation_category = _clean(getattr(foundation_profile, "category", "")).lower()
            foundation_name = foundation_profile.name
            if foundation_category in {"bread", "tortilla"} or any(word in foundation_name.lower() for word in ["biscuit", "roll", "bread", "toast"]):
                combine_instruction = f"Serve {foundation_name} on the side or use it as the bread component; do not stir it into the skillet."
                active = 1
                passive = 0
            else:
                combine_instruction = f"Serve or combine the prepared {foundation_name} with the protein and vegetables."
                active = 3
                passive = 2
            steps.append(CookingStep(
                order=65,
                phase="combine",
                instruction=combine_instruction,
                total_minutes=active + passive,
                active_minutes=active,
                passive_minutes=passive,
                attention_score=2,
                cleanup_score=1,
                forgiveness_score=8,
                parallel_ok=False,
            ))
        steps.append(CookingStep(
            order=70,
            phase="finish",
            instruction=f"Season toward {cuisine} using {sauce}; taste, adjust, and serve.",
            total_minutes=5,
            active_minutes=5,
            passive_minutes=0,
            attention_score=3,
            cleanup_score=1,
            forgiveness_score=8,
            parallel_ok=False,
        ))

    steps = sorted(steps, key=lambda s: s.order)
    timing = _summarize_timing(steps)
    return CookingPlan(steps=steps, total_minutes=timing[0], active_minutes=timing[1], passive_minutes=timing[2], attention_score=timing[3], cleanup_score=timing[4], forgiveness_score=timing[5], down_day_score=timing[6], energy_fit=timing[7])


def generate_human_instructions(candidate: dict) -> str:
    """Convert the cooking plan into readable instructions. No embedded numbering."""
    plan = build_cooking_plan(candidate)
    lines = []
    for step in plan.steps:
        instruction = _strip_number_prefix(step.instruction)
        time_note = f" ({step.total_minutes} min: {step.active_minutes} active"
        if step.passive_minutes:
            time_note += f", {step.passive_minutes} passive"
        time_note += ")"
        parallel_note = " This can happen while another component cooks." if step.parallel_ok else ""
        lines.append(f"{instruction}{time_note}{parallel_note}")
    return "\n".join(lines)


def build_plan_summary(candidate: dict) -> Dict[str, int | str]:
    plan = build_cooking_plan(candidate)
    return {
        "total_minutes": plan.total_minutes,
        "active_minutes": plan.active_minutes,
        "passive_minutes": plan.passive_minutes,
        "attention_score": plan.attention_score,
        "cleanup_score": plan.cleanup_score,
        "forgiveness_score": plan.forgiveness_score,
        "down_day_score": plan.down_day_score,
        "energy_fit": plan.energy_fit,
        "summary_line": plan.summary_line(),
    }
