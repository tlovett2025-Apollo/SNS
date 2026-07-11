"""
Ingredient Knowledge Objects for Stock & Stir / SNS.

Knowledge Objects own ingredient-specific cooking knowledge and publish kitchen
activities. The planner consumes and orchestrates those activities; it does not
infer how an ingredient should be cooked.
"""

from dataclasses import dataclass, field
from typing import List, Optional


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


@dataclass
class KitchenActivity:
    """A unit of kitchen work published by a Knowledge Object."""

    component: str
    activity_type: str
    instruction: str
    minutes: Optional[int] = None
    human_busy: bool = True
    equipment: str = ""
    depends_on: List[str] = field(default_factory=list)
    stage: str = "middle"  # early, middle, late, finish
    parallel_ok: bool = True
    source: str = "ko"
    activity_id: str = ""


@dataclass
class IngredientState:
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
    default_state: str = ""
    states: dict = field(default_factory=dict)
    prep_minutes: int = 5
    cook_minutes: int = 8
    active_minutes: int = 0
    passive_minutes: int = 0
    attention_score: int = 5
    rest_minutes: int = 0
    add_stage: str = "middle"
    holdability: str = "fair"
    preferred_method: str = "cook"
    desired_outcome: str = ""
    failure_mode: str = ""
    recovery_hint: str = ""
    teaching_note: str = ""
    parallel_ok: bool = True
    start_first: bool = False
    timing_note: str = ""
    handling_note: str = ""
    work_score: int = 5
    cleanup_score: int = 5
    mental_load_score: int = 5

    @property
    def total_active_minutes(self):
        return self.prep_minutes + (self.active_minutes or self.cook_minutes)

    @property
    def total_passive_minutes(self):
        return self.passive_minutes + self.rest_minutes

    def available_states(self):
        return list(self.states.keys())

    def get_state(self, state_name=""):
        state_name = _clean(state_name) or self.default_state
        return self.states.get(state_name)

    def effort_score(self):
        return round(
            (self.attention_score + self.work_score + self.cleanup_score + self.mental_load_score) / 4
        )

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

    def publish_activities(self, strategy="", state_name="") -> List[KitchenActivity]:
        """Publish ingredient-owned activities for the planner to orchestrate."""

        if not self.name:
            return []

        state = self.get_state(state_name)
        prep_minutes = state.prep_minutes if state else self.prep_minutes
        cook_minutes = state.cook_minutes if state else self.cook_minutes
        handling_note = state.handling_note if state and state.handling_note else self.handling_note
        stage = "early" if self.start_first else self.add_stage
        activities: List[KitchenActivity] = []

        if prep_minutes > 0:
            instruction = (
                f"Prep {self.name}: {handling_note}"
                if handling_note
                else f"Prep {self.name}."
            )
            activities.append(KitchenActivity(
                component=self.name,
                activity_type="prep",
                instruction=instruction,
                minutes=prep_minutes,
                human_busy=True,
                stage=stage,
                parallel_ok=True,
                equipment="counter",
                activity_id=f"prep:{self.name}",
            ))

        activities.append(KitchenActivity(
            component=self.name,
            activity_type=self.preferred_method or "cook",
            instruction=self.cook_instruction(strategy),
            minutes=cook_minutes or None,
            human_busy=(self.active_minutes or cook_minutes) > 0,
            stage=stage,
            parallel_ok=self.parallel_ok,
            depends_on=[f"prep:{self.name}"] if prep_minutes > 0 else [],
            equipment="burner",
            activity_id=f"{self.preferred_method or 'cook'}:{self.name}",
        ))

        if self.passive_minutes > 0:
            activities.append(KitchenActivity(
                component=self.name,
                activity_type="wait",
                instruction=f"Let {self.name} continue cooking without constant attention.",
                minutes=self.passive_minutes,
                human_busy=False,
                stage=stage,
                parallel_ok=True,
                equipment="burner",
                activity_id=f"wait:{self.name}",
                depends_on=[f"{self.preferred_method or 'cook'}:{self.name}"],
            ))

        if self.rest_minutes > 0:
            activities.append(KitchenActivity(
                component=self.name,
                activity_type="rest",
                instruction=f"Rest {self.name} before finishing or serving.",
                minutes=self.rest_minutes,
                human_busy=False,
                stage="finish",
                parallel_ok=True,
                depends_on=[f"wait:{self.name}"] if self.passive_minutes > 0 else [f"{self.preferred_method}:{self.name}"],
                equipment="counter",
                activity_id=f"rest:{self.name}",
            ))

        return activities


SWISS_CHARD = IngredientProfile(
    name="Swiss chard",
    role="vegetable",
    prep_minutes=5,
    cook_minutes=4,
    add_stage="late",
    holdability="poor",
    preferred_method="saute",
    desired_outcome="bright, tender greens that are wilted but not slimy.",
    failure_mode="Swiss chard becomes limp, watery, and unpleasant if overcooked or held too long.",
    recovery_hint="If it gets watery, drain excess liquid and season again before serving.",
    teaching_note="Swiss chard cooks fast because the leaves collapse quickly under heat.",
    parallel_ok=False,
    handling_note="wash well, trim tough stems, and chop leaves separately from stems if needed.",
    timing_note="Swiss chard wilts quickly and does not hold well, so cook it near the end.",
    work_score=4,
    cleanup_score=3,
    mental_load_score=3,
)


BLACK_OLIVES = IngredientProfile(
    name="Black olives",
    role="vegetable",
    prep_minutes=1,
    cook_minutes=0,
    active_minutes=1,
    add_stage="late",
    holdability="excellent",
    preferred_method="fold in",
    desired_outcome="warm olives distributed through the finished dish without being overcooked.",
    failure_mode="Olives can become harsh or rubbery when cooked too long.",
    recovery_hint="Add a fresh spoonful at serving if the olive flavor has faded.",
    teaching_note="Canned olives are already ready to eat and usually need only draining and folding in.",
    parallel_ok=True,
    handling_note="drain well; slice only if the meal shape needs smaller pieces.",
    timing_note="Fold black olives in near the end so they warm without becoming tough.",
    work_score=1,
    cleanup_score=1,
    mental_load_score=1,
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
    desired_outcome="safe, juicy chicken that is cooked through without drying out.",
    failure_mode="Chicken breast becomes dry and tough when overcooked.",
    recovery_hint="If it seems dry, slice it thinly and serve with sauce or gravy.",
    teaching_note="Resting helps the juices settle before slicing.",
    parallel_ok=False,
    handling_note="pat dry, season before cooking, and avoid overcooking.",
    timing_note="Chicken breast needs active attention while cooking and benefits from a short rest before slicing.",
    attention_score=6,
    work_score=6,
    cleanup_score=5,
    mental_load_score=5,
    default_state="Fresh Raw",
    states={
        "Fresh Raw": IngredientState(
            name="Fresh Raw", prep_minutes=3, cook_minutes=12, active_minutes=10,
            passive_minutes=5, attention_score=6, holdability="fair",
            handling_note="pat dry, season before cooking, and avoid overcooking.",
            timing_note="Fresh raw chicken breast cooks quickly but needs attention.",
        ),
        "Frozen Raw": IngredientState(
            name="Frozen Raw", prep_minutes=2, cook_minutes=20, active_minutes=8,
            passive_minutes=15, attention_score=5, holdability="fair",
            handling_note="cook from frozen only with a covered or moist method, or thaw first when possible.",
            timing_note="Frozen raw chicken breast needs extra passive time.",
        ),
        "Cooked": IngredientState(
            name="Cooked", prep_minutes=2, cook_minutes=5, active_minutes=5,
            passive_minutes=0, attention_score=3, holdability="good",
            handling_note="slice, shred, or dice before reheating.",
            timing_note="Cooked chicken breast is mostly reheating and assembly.",
        ),
    },
)


RICE = IngredientProfile(
    name="Rice",
    role="foundation",
    prep_minutes=2,
    cook_minutes=20,
    active_minutes=2,
    passive_minutes=18,
    rest_minutes=5,
    add_stage="early",
    holdability="good",
    preferred_method="simmer",
    desired_outcome="tender grains that are fully cooked without becoming mushy.",
    failure_mode="Rice can scorch, remain hard, or become gummy when liquid and heat are poorly controlled.",
    recovery_hint="If rice is still firm, add a small amount of hot liquid, cover, and continue gently.",
    teaching_note="Rice should start early because most of its cook time is passive and can overlap with other work.",
    parallel_ok=True,
    start_first=True,
    handling_note="measure rice and liquid before heating.",
    timing_note="Start rice early, then let it cook mostly unattended while the other components are prepared.",
    attention_score=2,
    work_score=2,
    cleanup_score=2,
    mental_load_score=2,
)

MUSHROOMS = IngredientProfile(
    name="Mushrooms",
    role="vegetable",
    prep_minutes=4,
    cook_minutes=8,
    active_minutes=8,
    add_stage="middle",
    holdability="good",
    preferred_method="saute",
    desired_outcome="deeply browned mushrooms with concentrated savory flavor.",
    failure_mode="Crowded mushrooms steam and become pale instead of browning.",
    recovery_hint="Increase the heat and let excess moisture evaporate before seasoning again.",
    teaching_note="Mushrooms benefit from browning before liquid is added.",
    parallel_ok=False,
    handling_note="wipe or rinse briefly, dry well, and slice evenly.",
    timing_note="Brown mushrooms before adding liquid so they contribute fond and concentrated flavor.",
    attention_score=6,
    work_score=4,
    cleanup_score=3,
    mental_load_score=4,
)

ASPARAGUS = IngredientProfile(
    name="Asparagus",
    role="vegetable",
    prep_minutes=3,
    cook_minutes=6,
    active_minutes=6,
    add_stage="middle",
    holdability="fair",
    preferred_method="saute",
    desired_outcome="bright green, tender-crisp asparagus.",
    failure_mode="Asparagus becomes limp and dull when overcooked.",
    recovery_hint="Serve promptly and add a bright finishing seasoning if it has softened too far.",
    teaching_note="Evenly sized pieces help asparagus cook at the same rate.",
    parallel_ok=False,
    handling_note="trim woody ends and cut into even pieces if needed.",
    timing_note="Cook asparagus after sturdy components but before quick-wilting greens.",
    attention_score=5,
    work_score=3,
    cleanup_score=3,
    mental_load_score=3,
)


def _rice_activities(self, strategy="", state_name=""):
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction="Measure the rice and cooking liquid.",
            minutes=2, human_busy=True, stage="early", parallel_ok=True,
            equipment="counter", activity_id="prep:Rice",
        ),
        KitchenActivity(
            component=self.name, activity_type="start",
            instruction="Bring the rice and liquid to a simmer, then cover and reduce the heat.",
            minutes=2, human_busy=True, stage="early", parallel_ok=False,
            depends_on=["prep:Rice"], equipment="burner",
            activity_id="start:Rice",
        ),
        KitchenActivity(
            component=self.name, activity_type="simmer",
            instruction="Let the rice simmer covered without constant attention.",
            minutes=18, human_busy=False, stage="early", parallel_ok=True,
            depends_on=["start:Rice"], equipment="burner",
            activity_id="simmer:Rice",
        ),
        KitchenActivity(
            component=self.name, activity_type="rest",
            instruction="Remove the rice from heat and let it rest covered before fluffing.",
            minutes=5, human_busy=False, stage="finish", parallel_ok=True,
            depends_on=["simmer:Rice"], equipment="counter",
            activity_id="rest:Rice",
        ),
    ]


def _chicken_activities(self, strategy="", state_name=""):
    """Publish a state-specific chicken activity graph."""

    state_name = _clean(state_name) or self.default_state

    if state_name == "Cooked":
        return [
            KitchenActivity(
                component=self.name, activity_type="prep",
                instruction="Slice, shred, or dice the cooked chicken breast as needed.",
                minutes=2, human_busy=True, stage="middle", parallel_ok=True,
                equipment="counter", activity_id="prep:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="reheat",
                instruction="Reheat the cooked chicken breast gently until hot; avoid drying it out.",
                minutes=5, human_busy=True, stage="late", parallel_ok=True,
                depends_on=["prep:Chicken breast"], equipment="burner",
                activity_id="reheat:Chicken breast",
            ),
        ]

    if state_name == "Frozen Raw":
        return [
            KitchenActivity(
                component=self.name, activity_type="prep",
                instruction="Remove packaging and season the frozen chicken breast. Use a covered or moist method unless thawed first.",
                minutes=2, human_busy=True, stage="early", parallel_ok=True,
                equipment="counter", activity_id="prep:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="cook",
                instruction="Begin cooking the frozen chicken breast with a covered or moist method.",
                minutes=8, human_busy=True, stage="early", parallel_ok=False,
                depends_on=["prep:Chicken breast"], equipment="burner",
                activity_id="cook:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="wait",
                instruction="Let the frozen chicken continue cooking through without constant attention.",
                minutes=15, human_busy=False, stage="middle", parallel_ok=True,
                depends_on=["cook:Chicken breast"], equipment="burner",
                activity_id="wait:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="verify",
                instruction="Verify that the thickest part of the chicken breast is safely cooked through.",
                minutes=2, human_busy=True, stage="finish", parallel_ok=False,
                depends_on=["wait:Chicken breast"], equipment="counter",
                activity_id="verify:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="rest",
                instruction="Rest the chicken breast before slicing.",
                minutes=5, human_busy=False, stage="finish", parallel_ok=True,
                depends_on=["verify:Chicken breast"], equipment="counter",
                activity_id="rest:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="slice",
                instruction="Slice the chicken breast after resting, if the meal shape needs sliced chicken.",
                minutes=2, human_busy=True, stage="finish", parallel_ok=False,
                depends_on=["rest:Chicken breast"], equipment="counter",
                activity_id="slice:Chicken breast",
            ),
        ]

    activities = IngredientProfile.publish_activities(self, strategy, "Fresh Raw")
    activities.append(KitchenActivity(
        component=self.name,
        activity_type="slice",
        instruction="Slice chicken breast after resting, if the meal shape needs sliced chicken.",
        minutes=2,
        human_busy=True,
        stage="finish",
        parallel_ok=False,
        depends_on=["rest:Chicken breast"],
        equipment="counter",
        activity_id="slice:Chicken breast",
    ))
    return activities

def _chard_activities(self, strategy="", state_name=""):
    activities = IngredientProfile.publish_activities(self, strategy, state_name)
    activities.append(KitchenActivity(
        component=self.name,
        activity_type="serve",
        instruction="Serve Swiss chard promptly; it does not hold well after cooking.",
        minutes=None,
        human_busy=True,
        stage="finish",
        parallel_ok=False,
        depends_on=["saute:Swiss chard"],
        equipment="counter",
        activity_id="serve:Swiss chard",
    ))
    return activities



def _olive_activities(self, strategy="", state_name=""):
    return [
        KitchenActivity(
            component=self.name,
            activity_type="drain",
            instruction="Drain black olives well.",
            minutes=1,
            human_busy=True,
            stage="late",
            parallel_ok=True,
            equipment="counter",
            activity_id="drain:Black olives",
        ),
        KitchenActivity(
            component=self.name,
            activity_type="fold in",
            instruction="Fold black olives into the dish near the end, just long enough to warm them.",
            minutes=1,
            human_busy=True,
            stage="late",
            parallel_ok=True,
            depends_on=["drain:Black olives"],
            equipment="counter",
            activity_id="fold in:Black olives",
        ),
    ]

# Prototype per-KO overrides. These will eventually be supplied by CKB activity data.
CHICKEN_BREAST.publish_activities = _chicken_activities.__get__(CHICKEN_BREAST, IngredientProfile)
SWISS_CHARD.publish_activities = _chard_activities.__get__(SWISS_CHARD, IngredientProfile)
BLACK_OLIVES.publish_activities = _olive_activities.__get__(BLACK_OLIVES, IngredientProfile)
RICE.publish_activities = _rice_activities.__get__(RICE, IngredientProfile)


def get_ingredient_profile(name, role="ingredient"):
    """Return a smart profile or a safe generic fallback profile."""

    cleaned_name = _clean(name)
    k = _key(cleaned_name)
    if not cleaned_name:
        return IngredientProfile(name=cleaned_name, role=role)
    if k == "swiss chard":
        return SWISS_CHARD
    if k == "chicken breast":
        return CHICKEN_BREAST
    if k == "black olives":
        return BLACK_OLIVES
    if k == "rice":
        return RICE
    if k == "mushrooms":
        return MUSHROOMS
    if k == "asparagus":
        return ASPARAGUS
    return IngredientProfile(name=cleaned_name, role=role)
