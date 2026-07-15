"""Deterministic trusted-advisor language for Stock & Stir.

This module owns how planner facts are expressed. It never changes cooking
logic, timing, dependencies, safety rules, or resource assignments.
"""

from typing import Optional


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def _component_name(activity) -> str:
    component = _clean(getattr(activity, "component", ""))
    if not component or component == "meal":
        return "the meal"
    return component


def meal_introduction(candidate: dict) -> str:
    """Introduce the selected meal in calm, practical language."""
    title = _clean(candidate.get("title") or candidate.get("name") or "this meal")
    energy = _clean(candidate.get("energy") or candidate.get("user_energy"))
    minutes = candidate.get("minutes")

    details = []
    if minutes is not None:
        details.append(f"about {minutes} minutes")
    if energy:
        details.append(f"{energy.lower()} energy")

    if details:
        return (
            f"Tonight we are making {title}. It is planned for "
            f"{' and '.join(details)}. We will take it one stage at a time."
        )
    return f"Tonight we are making {title}. We will take it one stage at a time."


def time_summary(total_minutes, active_minutes, passive_minutes) -> Optional[str]:
    """Describe the time commitment without sounding mechanical."""
    if total_minutes is None:
        return None

    active = int(active_minutes or 0)
    passive = int(passive_minutes or 0)
    return (
        f"Plan on about {total_minutes} minutes total: {active} minutes need your "
        f"attention, and about {passive} minutes are mostly waiting time. Some work "
        "can overlap, so the time windows are guidance rather than a rigid sequence."
    )


def _friendly_closing(activity_type: str) -> str:
    closings = {
        "gather": "Now everything is within reach.",
        "launch prep": "Now it is ready to start.",
        "optional sear": "This step is optional.",
        "build soup": "Good. The soup is built.",
        "shared simmer": "Everything can cook together now.",
        "combine": "Now the components are working as one meal.",
        "assemble": "Everything is ready to assemble.",
        "plate": "You are ready to plate.",
        "finish sauce": "The sauce is ready.",
        "finish soup": "The soup is nearly ready.",
        "finish and serve": "You are at the finish.",
        "bake": "The oven can take over for a while.",
        "rest": "Let it rest.",
        "natural release": "Let the pressure release naturally.",
    }
    return closings.get(activity_type, "")


def _passive_reassurance(activity, duration: int) -> str:
    if bool(getattr(activity, "human_busy", True)) or duration < 3:
        return ""

    activity_type = _clean(getattr(activity, "activity_type", "")).lower()
    if activity_type in {"rest", "natural release", "bake", "shared simmer"}:
        return " Nothing needs your full attention during this window."
    return " You do not need to work continuously during this window."


def activity_message(activity, duration: int, attention_minutes: int = 0) -> str:
    """Turn one scheduled activity into trusted-advisor language."""
    instruction = _clean(getattr(activity, "instruction", ""))
    activity_type = _clean(getattr(activity, "activity_type", "")).lower()
    closing = _friendly_closing(activity_type)

    message = instruction or f"Continue with {_component_name(activity)}."
    message += _passive_reassurance(activity, duration)

    if 0 < attention_minutes < duration:
        message += (
            f" You will need about {attention_minutes} minutes of attention "
            "during this window."
        )

    if closing:
        message += f" {closing}"

    # Keep explicit substep breaks published by Knowledge Objects and the
    # consolidator. Collapse incidental whitespace within each line only.
    lines = [" ".join(line.split()) for line in message.splitlines()]
    return "\n".join(lines).strip()


def transition_message(previous_activity, next_activity) -> Optional[str]:
    """Return a brief transition only when it adds useful orientation."""
    if previous_activity is None or next_activity is None:
        return None

    previous_stage = _clean(getattr(previous_activity, "stage", ""))
    next_stage = _clean(getattr(next_activity, "stage", ""))
    if previous_stage == next_stage:
        return None

    if next_stage == "finish":
        return "Good. The main cooking is done, and we are moving into the finish."
    if next_stage == "late":
        return "Looking good. We are in the final cooking stage now."
    if previous_stage == "early" and next_stage == "middle":
        return "Prep is complete. Now the cooking begins."
    return None


def completion_message(candidate: dict) -> str:
    """Confirm completion without asking for work after the meal is plated."""
    return "Nicely done. Dinner is ready."
