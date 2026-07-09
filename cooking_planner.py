"""
Cooking Timeline Engine for Stock & Stir / SNS.

This module turns a selected recipe candidate into ordered cooking steps.
It is intentionally practical and conservative: first make the engine work,
then deepen the cooking intelligence as more CKB fields become available.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CookingStep:
    order: int
    phase: str
    instruction: str
    minutes: Optional[int] = None
    parallel_ok: bool = False


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
        if protein:
            steps.append(CookingStep(
                order=30,
                phase="protein",
                instruction=f"Cook {protein} in a skillet until safe and browned where appropriate.",
                minutes=12,
                parallel_ok=False,
            ))
        if vegetable:
            steps.append(CookingStep(
                order=40,
                phase="vegetable",
                instruction=f"Add {vegetable} and cook until it reaches the texture you like.",
                minutes=8,
                parallel_ok=False,
            ))
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
    Convert the cooking plan into readable recipe instructions.
    """

    steps = build_cooking_plan(candidate)
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

    for index, step in enumerate(steps, start=1):
        time_note = f" ({step.minutes} min)" if step.minutes else ""
        parallel_note = " This can happen while another component cooks." if step.parallel_ok else ""
        lines.append(f"{index}. {step.instruction}{time_note}{parallel_note}")

    return "\n".join(lines)
