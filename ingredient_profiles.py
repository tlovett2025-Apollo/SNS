"""
Ingredient Profiles for Stock & Stir / SNS.

This is the first "python baby" layer.

The database still stores ingredients as data, but this file lets the planner
ask an ingredient what it knows about cooking itself.

First living baby: Swiss chard.
"""

from dataclasses import dataclass, field


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")

@dataclass
class IngredientForm:
    name: str
    prep_minutes: int = 0
    cook_minutes: int = 0
    active_minutes: int = 0
    passive_minutes: int = 0
    attention_score: int = 0
    holdability: str = ""
    timing_note: str = ""
    handling_note: str = ""


@dataclass
class IngredientProfile:
    name: str
    role: str = "ingredient"
    default_form: str = ""
    forms: dict = field(default_factory=dict)
    prep_minutes: int = 5
    cook_minutes: int = 8
    active_minutes: int = 0
    passive_minutes: int = 0
    attention_score: int = 5
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
        return self.prep_minutes + (self.active_minutes or self.cook_minutes)

    @property
    def total_passive_minutes(self):
        return self.passive_minutes + self.rest_minutes
        
    def available_forms(self):
        return list(self.forms.keys())

    def get_form(self, form_name=""):
        form_name = _clean(form_name) or self.default_form
        return self.forms.get(form_name)
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

CHICKEN_BREAST = IngredientProfile(
    name="Chicken breast",
    role="protein",
    prep_minutes=3,
    cook_minutes=12,
    active_minutes=10,
    passive_minutes=5,
    rest_minutes=5,
    add_stage="middle",
    holdability="fair",
    preferred_method="cook",
    parallel_ok=False,
    start_first=False,
    handling_note="pat dry, season before cooking, and avoid overcooking.",
    timing_note="Chicken breast needs active attention while cooking and benefits from a short rest before slicing.",
    attention_score=6,

    default_form="Fresh Raw",
    forms={
        "Fresh Raw": IngredientForm(
            name="Fresh Raw",
            prep_minutes=3,
            cook_minutes=12,
            active_minutes=10,
            passive_minutes=5,
            attention_score=6,
            holdability="fair",
            handling_note="pat dry, season before cooking, and avoid overcooking.",
            timing_note="Fresh raw chicken breast cooks quickly but needs attention."
        ),
        "Frozen Raw": IngredientForm(
            name="Frozen Raw",
            prep_minutes=2,
            cook_minutes=20,
            active_minutes=8,
            passive_minutes=15,
            attention_score=5,
            holdability="fair",
            handling_note="cook from frozen only with a covered or moist method, or thaw first when possible.",
            timing_note="Frozen raw chicken breast needs extra passive time."
        ),
        "Cooked": IngredientForm(
            name="Cooked",
            prep_minutes=2,
            cook_minutes=5,
            active_minutes=5,
            passive_minutes=0,
            attention_score=3,
            holdability="good",
            handling_note="slice, shred, or dice before reheating.",
            timing_note="Cooked chicken breast is mostly reheating and assembly."
        ),
    },
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
    
    if k == "chicken breast":
        return CHICKEN_BREAST

    return IngredientProfile(name=cleaned_name, role=role)
