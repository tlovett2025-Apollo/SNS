"""
Ingredient Profiles for Stock & Stir / SNS.

This is the first "python baby" layer.

The database still stores ingredients as data, but this file lets the planner
ask an ingredient what it knows about cooking itself.

First living baby: Swiss chard.
"""

from dataclasses import dataclass


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


@dataclass
class IngredientProfile:
    name: str
    role: str = "ingredient"
    prep_minutes: int = 5
    cook_minutes: int = 8
    rest_minutes: int = 0
    add_stage: str = "middle"  # early, middle, late
    holdability: str = "fair"  # poor, fair, good, excellent
    preferred_method: str = "cook"
    parallel_ok: bool = True
    start_first: bool = False
    timing_note: str = ""
    handling_note: str = ""

    @property
    def total_active_minutes(self):
        return self.prep_minutes + self.cook_minutes + self.rest_minutes

    def prep_instruction(self):
        if self.handling_note:
            return f"Prep {self.name}: {self.handling_note}"
        return f"Prep {self.name}."

    def cook_instruction(self, strategy=""):
        strategy = _key(strategy)

        if self.add_stage == "late":
            return f"Add {self.name} near the end and {self.preferred_method} just until ready."

        if self.add_stage == "early":
            return f"Start {self.name} early and {self.preferred_method} until tender."

        if "skillet" in strategy:
            return f"Add {self.name} to the skillet and {self.preferred_method} until ready."

        return f"Cook {self.name} using {self.preferred_method} until ready."

    def finish_note(self):
        if self.timing_note:
            return self.timing_note
        if self.holdability == "poor":
            return f"{self.name} is best cooked close to serving time."
        if self.holdability == "excellent":
            return f"{self.name} can be made early and held warm."
        return ""


# First living Python baby.
SWISS_CHARD = IngredientProfile(
    name="Swiss chard",
    role="vegetable",
    prep_minutes=5,
    cook_minutes=4,
    rest_minutes=0,
    add_stage="late",
    holdability="poor",
    preferred_method="saute",
    parallel_ok=False,
    start_first=False,
    handling_note="wash well, trim tough stems, and chop leaves separately from stems if needed.",
    timing_note="Swiss chard wilts quickly and does not hold well, so cook it near the end.",
)


def get_ingredient_profile(name, role="ingredient"):
    """
    Return a smart ingredient profile when we have one.
    Otherwise return a safe generic profile so the planner keeps working.
    """

    cleaned_name = _clean(name)
    k = _key(cleaned_name)

    if not cleaned_name:
        return None

    if k == "swiss chard":
        return SWISS_CHARD

    return IngredientProfile(name=cleaned_name, role=role)
