"""
Ingredient Knowledge Objects for Stock & Stir / SNS.

Knowledge Objects own ingredient-specific cooking knowledge and publish kitchen
activities. The planner consumes and orchestrates those activities; it does not
infer how an ingredient should be cooked.
"""

from contextlib import closing
from dataclasses import dataclass, field, replace
from pathlib import Path
import sqlite3
from typing import List, Optional

from ko_behavior import resolve_behavior

try:
    from config import DB_PATH
except Exception:
    DB_PATH = Path("data") / "ckb_seed_001.db"


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def _ckb_profile(name, role):
    """Load a verified KO from the CKB, returning None for a safe Python fallback."""
    try:
        # sqlite3.Connection's own context manager commits or rolls back, but it
        # does not close the connection. closing(...) guarantees Windows releases
        # the database file handle on every return and exception path.
        with closing(sqlite3.connect(DB_PATH)) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                """SELECT * FROM ko_profiles
                   WHERE lower(component_name)=lower(?) AND role=? AND verified=1""",
                (_clean(name), _clean(role).lower()),
            ).fetchone()
            if not row:
                return None

            profile = IngredientProfile(
                name=row["component_name"], role=row["role"],
                default_state=row["default_state"] or "",
                prep_minutes=row["prep_minutes"] or 0, cook_minutes=row["cook_minutes"] or 0,
                active_minutes=row["active_minutes"] or 0, passive_minutes=row["passive_minutes"] or 0,
                attention_score=row["attention_score"] or 0, rest_minutes=row["rest_minutes"] or 0,
                add_stage=row["add_stage"] or "middle", holdability=row["holdability"] or "fair",
                preferred_method=row["preferred_method"] or "cook",
                desired_outcome=row["desired_outcome"] or "", failure_mode=row["failure_mode"] or "",
                recovery_hint=row["recovery_hint"] or "", teaching_note=row["teaching_note"] or "",
                parallel_ok=bool(row["parallel_ok"]), start_first=bool(row["start_first"]),
                timing_note=row["timing_note"] or "", handling_note=row["handling_note"] or "",
                cooking_note=row["cooking_note"] or "", work_score=row["work_score"] or 0,
                cleanup_score=row["cleanup_score"] or 0, mental_load_score=row["mental_load_score"] or 0,
            )

            if row["ingredient_id"] is not None:
                state_rows = con.execute(
                    "SELECT * FROM ingredient_states WHERE ingredient_id=? AND verified=1",
                    (row["ingredient_id"],),
                ).fetchall()
                profile.states = {
                    state["state_name"]: IngredientState(
                        name=state["state_name"], prep_minutes=state["typical_prep_minutes"] or 0,
                        cook_minutes=state["typical_cook_minutes"] or 0,
                        active_minutes=state["active_minutes"] or 0,
                        passive_minutes=state["passive_minutes"] or 0,
                        attention_score=state["attention_score"] or 0,
                        holdability=state["holdability"] or "",
                        handling_note=state["handling_note"] or "",
                        timing_note=state["timing_note"] or "",
                        cooking_note=state["cooking_note"] or "",
                    ) for state in state_rows
                }

            # Fetch all activity data before the connection closes. sqlite3.Row
            # values remain usable after fetchall() because the data is materialized.
            activity_rows = con.execute(
                """SELECT * FROM ko_activities
                   WHERE lower(component_name)=lower(?) AND role=? AND verified=1
                   ORDER BY state_name, sequence""",
                (row["component_name"], row["role"]),
            ).fetchall()

        def publish_from_ckb(self, strategy="", state_name=""):
            selected_state = _clean(state_name) or self.default_state
            exact = [activity for activity in activity_rows if activity["state_name"] == selected_state]
            selected = exact or [activity for activity in activity_rows if not activity["state_name"]]
            ids = {
                activity["sequence"]: f"{activity['activity_type']}:{self.name}"
                for activity in selected
            }
            return [
                KitchenActivity(
                    component=self.name, activity_type=activity["activity_type"],
                    instruction=activity["instruction"], minutes=activity["minutes"],
                    human_busy=bool(activity["human_busy"]),
                    attention_load=float(activity["attention_load"] or 0),
                    equipment=activity["equipment_name"] or "counter",
                    depends_on=[ids[activity["depends_on_sequence"]]] if activity["depends_on_sequence"] else [],
                    stage=activity["stage"] or "middle", parallel_ok=bool(activity["parallel_ok"]),
                    source="ko", activity_id=ids[activity["sequence"]],
                ) for activity in selected
            ]

        if activity_rows:
            profile.publish_activities = publish_from_ckb.__get__(profile, IngredientProfile)
        return profile
    except (sqlite3.Error, OSError, KeyError):
        return None


@dataclass
class KitchenActivity:
    """A unit of kitchen work published by a Knowledge Object."""

    component: str
    activity_type: str
    instruction: str
    minutes: Optional[int] = None
    human_busy: bool = True
    attention_load: float = 1.0  # fraction of the window needing human attention
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
    cooking_note: str = ""


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
    cooking_note: str = ""
    work_score: int = 5
    cleanup_score: int = 5
    mental_load_score: int = 5
    # Relationship rules describe what the ingredient needs from the meal,
    # rather than pretending every vegetable is an isolated burner task.
    solo_methods: tuple = ()
    companion_methods: tuple = ()
    preferred_companions: tuple = ()
    avoid_solo_methods: tuple = ()
    structure_outcomes: dict = field(default_factory=dict)

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
        if self.cooking_note:
            return self.cooking_note
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

        selected_state_name = _clean(state_name) or self.default_state
        state_key = _key(selected_state_name)
        if self.role == "protein" and state_key in {"cooked", "canned", "ready to eat"}:
            canned = state_key == "canned" or _key(self.name).startswith("canned ")
            prep_instruction = (
                f"Drain {self.name} and break it into serving-size pieces."
                if canned else
                f"Remove any bones or skin as desired, then slice or shred {self.name}."
            )
            return [
                KitchenActivity(
                    component=self.name, activity_type="prep",
                    instruction=prep_instruction, minutes=2, human_busy=True,
                    stage="middle", parallel_ok=True, equipment="counter",
                    activity_id=f"prep:{self.name}",
                ),
                KitchenActivity(
                    component=self.name, activity_type="reheat",
                    instruction=f"Fold in {self.name} near the end and heat it gently until hot.",
                    minutes=4, human_busy=True, attention_load=0.5,
                    stage="late", parallel_ok=False, depends_on=[f"prep:{self.name}"],
                    equipment="burner", activity_id=f"reheat:{self.name}",
                ),
            ]
        if state_key == "canned" and self.role in {"foundation", "vegetable"}:
            bean = "bean" in _key(self.name)
            return [
                KitchenActivity(
                    component=self.name, activity_type="prep",
                    instruction=(
                        f"Drain and rinse {self.name}. Leave them whole, or mash some for a creamier texture."
                        if bean else f"Drain {self.name} well."
                    ),
                    minutes=2, human_busy=True, stage="middle", parallel_ok=True,
                    equipment="counter", activity_id=f"prep:{self.name}",
                ),
                KitchenActivity(
                    component=self.name, activity_type="reheat",
                    instruction=(
                        f"Stir in {self.name}, mash or purée further if desired, and heat until steaming."
                        if bean else f"Add {self.name} and heat through gently."
                    ),
                    minutes=4, human_busy=True, attention_load=0.5,
                    stage="late", parallel_ok=False, depends_on=[f"prep:{self.name}"],
                    equipment="burner", activity_id=f"reheat:{self.name}",
                ),
            ]
        if self.role == "protein" and _key(self.name) == "ground beef" and selected_state_name != "Cooked":
            thaw_id = f"thaw:{self.name}"
            prep_id = f"prep:{self.name}"
            cook_id = f"cook:{self.name}"
            activities = []
            if selected_state_name == "Frozen Raw":
                activities.append(KitchenActivity(
                    component=self.name,
                    activity_type="thaw",
                    instruction="Thaw the ground beef safely before skillet cooking.",
                    minutes=30,
                    human_busy=True,
                    attention_load=0.1,
                    stage="early",
                    parallel_ok=True,
                    equipment="counter",
                    activity_id=thaw_id,
                ))
            activities.extend([
                KitchenActivity(
                    component=self.name,
                    activity_type="prep",
                    instruction=(
                        "Transfer the thawed ground beef to a clean plate and keep it separate from ready-to-eat foods."
                    ),
                    minutes=2,
                    human_busy=True,
                    stage="early",
                    parallel_ok=True,
                    depends_on=[thaw_id] if selected_state_name == "Frozen Raw" else [],
                    equipment="counter",
                    activity_id=prep_id,
                ),
                KitchenActivity(
                    component=self.name,
                    activity_type="cook",
                    instruction=(
                        "Add the ground beef to the hot skillet and break it into small crumbles as it cooks."
                    ),
                    minutes=8,
                    human_busy=True,
                    attention_load=0.65,
                    stage="middle",
                    parallel_ok=False,
                    depends_on=[prep_id],
                    equipment="burner",
                    activity_id=cook_id,
                ),
            ])
            return activities

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
            attention_load=max(0.1, min(1.0, self.attention_score / 10)),
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
    prep_minutes=2,
    cook_minutes=6,
    add_stage="late",
    holdability="poor",
    preferred_method="saute",
    desired_outcome="bright, tender greens that are wilted but not slimy.",
    failure_mode="Swiss chard becomes limp, watery, and unpleasant if overcooked or held too long.",
    recovery_hint="If it gets watery, drain excess liquid and season again before serving.",
    teaching_note="Swiss chard cooks fast because the leaves collapse quickly under heat.",
    parallel_ok=False,
    handling_note="rinse the leaves and stems thoroughly. Cut the stems away from the leaves and slice the edible stems into small pieces. Leave the leaves in large pieces or tear them into manageable sections.",
    cooking_note="Heat a small amount of oil in a skillet. Add the sliced Swiss chard stems first and cook 3–5 minutes, until they begin to soften. Add the leaves with a small splash of water or broth and toss 2–3 minutes, until wilted and tender. Season with salt and a bright finish such as lemon juice or vinegar.",
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
    passive_minutes=0,
    rest_minutes=5,
    add_stage="middle",
    holdability="fair",
    preferred_method="cook",
    desired_outcome="safe, juicy chicken that is cooked through without drying out.",
    failure_mode="Chicken breast becomes dry and tough when overcooked.",
    recovery_hint="If it seems dry, slice it thinly and serve with sauce or gravy.",
    teaching_note="Resting helps the juices settle before slicing.",
    parallel_ok=False,
    handling_note="remove loose membrane and as much visible fat as desired. Do not rinse raw chicken. Pat dry, make the thickness even if needed, and season both sides.",
    cooking_note="Heat a lightly oiled skillet over medium to medium-high heat. Add the chicken breast and let the first side brown before turning. Turn and continue cooking, checking it periodically rather than watching it continuously.",
    timing_note="Chicken breast needs active attention while cooking and benefits from a short rest before slicing.",
    attention_score=6,
    work_score=6,
    cleanup_score=5,
    mental_load_score=5,
    default_state="Fresh Raw",
    states={
        "Fresh Raw": IngredientState(
            name="Fresh Raw", prep_minutes=3, cook_minutes=12, active_minutes=10,
            passive_minutes=0, attention_score=6, holdability="fair",
            handling_note="remove loose membrane and as much visible fat as desired. Do not rinse raw chicken. Pat dry, make the thickness even if needed, and season both sides.",
            timing_note="Fresh raw chicken breast cooks quickly but needs attention.",
        ),
        "Frozen Raw": IngredientState(
            name="Frozen Raw", prep_minutes=3, cook_minutes=12, active_minutes=10,
            passive_minutes=0, attention_score=5, holdability="fair",
            handling_note="thaw safely, pat dry without rinsing, and season both sides before skillet cooking.",
            timing_note="Frozen raw chicken breast must be thawed before this skillet method.",
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
    prep_minutes=2,
    cook_minutes=6,
    active_minutes=6,
    add_stage="early",
    holdability="good",
    preferred_method="saute",
    desired_outcome="deeply browned mushrooms with concentrated savory flavor.",
    failure_mode="Crowded mushrooms steam and become pale instead of browning.",
    recovery_hint="Increase the heat and let excess moisture evaporate before seasoning again.",
    teaching_note="Mushrooms benefit from browning before liquid is added.",
    parallel_ok=False,
    handling_note="quickly rinse off attached dirt or wipe with a damp towel; do not soak. Trim and discard only the dry end of each stem. Slice approximately 1/4 inch (6 mm) thick.",
    cooking_note="Heat a skillet over medium-high heat. Add the mushrooms in a single, uncrowded layer and leave them undisturbed while they release moisture. When the moisture evaporates and the bottoms brown, stir or turn them and cook about 2 minutes longer. Season after browning.",
    timing_note="Brown mushrooms before adding liquid so they contribute fond and concentrated flavor.",
    attention_score=2,
    work_score=4,
    cleanup_score=3,
    mental_load_score=4,
)

ASPARAGUS = IngredientProfile(
    name="Asparagus",
    role="vegetable",
    prep_minutes=2,
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
    handling_note="wash the asparagus and trim or snap off the woody ends. Leave the spears whole or cut them into bite-size pieces.",
    cooking_note="Heat a small amount of oil or butter in a skillet. Add the asparagus and sauté 2–3 minutes. For thick or firm stalks, add 1–2 tablespoons of water and cover briefly to steam. Uncover and continue cooking until bright green and crisp-tender, then season and serve promptly.",
    timing_note="Cook asparagus after sturdy components but before quick-wilting greens.",
    attention_score=5,
    work_score=3,
    cleanup_score=3,
    mental_load_score=3,
)

TOMATO_RELATIONSHIPS = {
    "solo_methods": ("fresh", "brief blister", "roast", "bake", "broil", "grill"),
    "companion_methods": ("saute", "simmer", "build sauce"),
    "preferred_companions": ("onions", "peppers", "garlic", "zucchini", "beans"),
    "avoid_solo_methods": ("long skillet fry",),
    "structure_outcomes": {
        "integrated": "softened into the shared dish or deliberately made sauce-like",
        "layered_bowl": "fresh, briefly blistered, or roasted while still holding its identity",
        "composed_plate": "fresh, roasted, baked, grilled, or briefly blistered as a distinct component",
    },
}

OKRA_RELATIONSHIPS = {
    "solo_methods": ("dry saute", "roast", "bread and fry", "grill"),
    "companion_methods": ("gumbo", "stew", "tomato braise"),
    "preferred_companions": ("tomatoes", "onions", "peppers", "corn"),
    "avoid_solo_methods": ("generic wet simmer",),
    "structure_outcomes": {
        "integrated": "either dry-cooked for defined pieces or intentionally used to thicken a stew",
        "layered_bowl": "browned or roasted with defined edges",
        "composed_plate": "roasted, grilled, or breaded and fried as a distinct component",
    },
}


def ingredient_relationships(name):
    """Return KO relationship intelligence used by every meal path."""
    key = _key(name)
    if "tomato" in key:
        return TOMATO_RELATIONSHIPS
    if "okra" in key:
        return OKRA_RELATIONSHIPS
    if "mushroom" in key:
        return {
            "solo_methods": ("dry brown", "roast"),
            "companion_methods": ("saute", "simmer"),
            "preferred_companions": ("onions", "garlic", "zucchini"),
            "avoid_solo_methods": ("wet cook before browning",),
            "structure_outcomes": {"integrated": "browned before the pan becomes wet"},
        }
    if any(word in key for word in ("onion", "carrot", "pepper")):
        return {
            "solo_methods": ("saute", "roast"),
            "companion_methods": ("soften", "build sauce", "simmer"),
            "preferred_companions": (),
            "avoid_solo_methods": (),
            "structure_outcomes": {"integrated": "given an early head start to soften and develop flavor"},
        }
    if any(word in key for word in ("zucchini", "asparagus", "spinach", "chard")):
        return {
            "solo_methods": ("quick saute", "roast", "grill"),
            "companion_methods": ("late saute", "brief simmer"),
            "preferred_companions": (),
            "avoid_solo_methods": ("long simmer",),
            "structure_outcomes": {"integrated": "added late enough to keep useful color and texture"},
        }
    return {}


def _attach_relationships(profile):
    rules = ingredient_relationships(profile.name)
    for field_name, value in rules.items():
        setattr(profile, field_name, value)
    return profile


def _rice_activities(self, strategy="", state_name=""):
    prep_id = f"prep:{self.name}"
    start_id = f"start:{self.name}"
    simmer_id = f"simmer:{self.name}"
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction="Measure the rice and cooking liquid.",
            minutes=2, human_busy=True, stage="early", parallel_ok=True,
            equipment="counter", activity_id=prep_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="start",
            instruction="Bring the rice and liquid to a simmer, then cover and reduce the heat.",
            minutes=2, human_busy=True, stage="early", parallel_ok=False,
            depends_on=[prep_id], equipment="burner",
            activity_id=start_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="simmer",
            instruction="Let the rice simmer covered without constant attention.",
            minutes=18, human_busy=False, stage="early", parallel_ok=True,
            depends_on=[start_id], equipment="burner",
            activity_id=simmer_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="rest",
            instruction="Remove the rice from heat and let it rest covered before fluffing.",
            minutes=5, human_busy=False, stage="finish", parallel_ok=True,
            depends_on=[simmer_id], equipment="counter",
            activity_id=f"rest:{self.name}",
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
                component=self.name, activity_type="thaw",
                instruction="Thaw the chicken breast safely before skillet cooking.",
                minutes=30, human_busy=True, attention_load=0.1,
                stage="early", parallel_ok=True,
                equipment="counter", activity_id="thaw:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="prep",
                instruction=(
                    "Pat the thawed chicken breast dry; do not rinse it. Make the thickness even if needed, "
                    "then season both sides."
                ),
                minutes=3, human_busy=True, stage="early", parallel_ok=True,
                depends_on=["thaw:Chicken breast"],
                equipment="counter", activity_id="prep:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="cook",
                instruction=(
                    "Heat a lightly oiled skillet over medium to medium-high heat. Add the chicken breast, "
                    "brown the first side, then turn and continue cooking."
                ),
                minutes=12, human_busy=True, attention_load=0.25,
                stage="middle", parallel_ok=False,
                depends_on=["prep:Chicken breast"], equipment="burner",
                activity_id="cook:Chicken breast",
            ),
            KitchenActivity(
                component=self.name, activity_type="verify",
                instruction="Verify that the thickest part of the chicken breast has reached 165°F.",
                minutes=2, human_busy=True, stage="finish", parallel_ok=False,
                depends_on=["cook:Chicken breast"], equipment="counter",
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
    for activity in activities:
        if activity.activity_type == "cook":
            activity.attention_load = 0.25
            activity.instruction += " Cook until the thickest part reaches 165°F, then remove it from the pan and let it rest before slicing."
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
    for activity in activities:
        if activity.activity_type == "saute":
            activity.attention_load = 0.75
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


def _citrus_activities(self, strategy="", state_name=""):
    citrus = _key(self.name).rstrip("s")
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction=f"Zest {self.name} if desired, then cut and juice it; remove any seeds.",
            minutes=2, human_busy=True, stage="middle", parallel_ok=True,
            equipment="counter", activity_id=f"prep:{self.name}",
        ),
        KitchenActivity(
            component=self.name, activity_type="finish",
            instruction=f"Add the {citrus} juice and zest at the finish, tasting as you go.",
            minutes=1, human_busy=True, stage="finish", parallel_ok=False,
            depends_on=[f"prep:{self.name}"], equipment="counter",
            activity_id=f"finish:{self.name}",
        ),
    ]


def _steak_activities(self, strategy="", state_name=""):
    """Give intact steaks visible cues, temperature verification, and a real rest."""
    prep_id = f"prep:{self.name}"
    cook_id = f"cook:{self.name}"
    verify_id = f"verify:{self.name}"
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction=(
                f"Pat {self.name} dry without rinsing it. Season both sides and let the surface lose its refrigerator chill while the skillet heats."
            ),
            minutes=3, human_busy=True, stage="early", parallel_ok=True,
            equipment="counter", activity_id=prep_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="cook",
            instruction=(
                f"Heat a lightly oiled heavy skillet over medium-high heat. Add {self.name} and leave the first side undisturbed to sear. "
                "When the cooked color has climbed roughly halfway to two-thirds up the side, flip it once. "
                "Sear the second side; use the visible band as a flip cue, not as proof of doneness."
            ),
            minutes=8, human_busy=True, attention_load=0.5,
            stage="middle", parallel_ok=False, depends_on=[prep_id],
            equipment="burner", activity_id=cook_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="verify",
            instruction=(
                "Check the center with an instant-read thermometer. For the USDA minimum, cook whole beef steak to 145°F, then rest it for at least 3 minutes."
            ),
            minutes=1, human_busy=True, stage="finish", parallel_ok=False,
            depends_on=[cook_id], equipment="counter", activity_id=verify_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="rest",
            instruction=f"Move {self.name} to a clean plate and rest it for at least 3 minutes before slicing or serving.",
            minutes=3, human_busy=False, stage="finish", parallel_ok=True,
            depends_on=[verify_id], equipment="counter", activity_id=f"rest:{self.name}",
        ),
    ]


def _mashed_potato_activities(self, strategy="", state_name=""):
    """Mashed potatoes are a prepared foundation, not loose food for the steak pan."""
    prep_id = f"prep:{self.name}"
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction=f"Measure {self.name}; add a splash of milk or a small pat of butter if they seem stiff.",
            minutes=1, human_busy=True, stage="middle", parallel_ok=True,
            equipment="counter", activity_id=prep_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="reheat",
            instruction=(
                f"Warm {self.name} gently in a small saucepan, stirring occasionally, or use the microwave in short intervals. "
                "Keep them separate from the steak skillet and cover when hot."
            ),
            minutes=5, human_busy=True, attention_load=0.35,
            stage="middle", parallel_ok=True, depends_on=[prep_id],
            equipment="burner", activity_id=f"reheat:{self.name}",
        ),
    ]


def _broccoli_activities(self, strategy="", state_name=""):
    prep_id = f"prep:{self.name}"
    return [
        KitchenActivity(
            component=self.name, activity_type="prep",
            instruction="Prep Broccoli: cut the crown into evenly sized florets; peel and slice the tender stem if using it.",
            minutes=2, human_busy=True, stage="middle", parallel_ok=True,
            equipment="counter", activity_id=prep_id,
        ),
        KitchenActivity(
            component=self.name, activity_type="saute",
            instruction=(
                "Add the broccoli to the hot skillet and sauté for about 2 minutes. Add 2 tablespoons of water, "
                "cover, and steam for 3–4 minutes. Uncover and cook off any remaining water; stop when it is bright green and fork-tender with a little bite."
            ),
            minutes=6, human_busy=True, attention_load=0.55,
            stage="middle", parallel_ok=False, depends_on=[prep_id],
            equipment="burner", activity_id=f"saute:{self.name}",
        ),
    ]

# Prototype per-KO overrides. These will eventually be supplied by CKB activity data.
CHICKEN_BREAST.publish_activities = _chicken_activities.__get__(CHICKEN_BREAST, IngredientProfile)
SWISS_CHARD.publish_activities = _chard_activities.__get__(SWISS_CHARD, IngredientProfile)
BLACK_OLIVES.publish_activities = _olive_activities.__get__(BLACK_OLIVES, IngredientProfile)
RICE.publish_activities = _rice_activities.__get__(RICE, IngredientProfile)


def _family_activities(self, strategy="", state_name=""):
    """Publish activities inherited from a reusable KO behavior family."""
    resolved = resolve_behavior(self.name, self.role, state_name, strategy, DB_PATH)
    rule = resolved.method
    if rule is None:
        # This profile is classified, but the requested environment is not.
        # An explicit incompatibility activity prevents the old generic
        # "cook until ready" fallback from masquerading as knowledge.
        return [KitchenActivity(
            component=self.name,
            activity_type="method_conflict",
            instruction=resolved.incompatibility_reason or
                f"Choose a trained cooking method for {self.name} in its {state_name or 'saved'} form.",
            minutes=0, human_busy=False, attention_load=0,
            stage="early", parallel_ok=False, equipment="counter",
            source="ko_family_gate", activity_id=f"method_conflict:{self.name}",
        )]

    handling = rule.handling_template.format(name=self.name)
    if resolved.primary_family.code == "ready_protein":
        handling = (
            f"Drain {self.name} and break it into serving-size pieces."
            if _key(self.name).startswith("canned ") else
            f"Remove any bones or skin as desired, then slice or shred {self.name}."
        )
    state_key = _key(state_name)
    if state_key == "canned" and self.role in {"foundation", "vegetable"} and "bean" in _key(self.name):
        handling = f"Drain and rinse {self.name}. Leave them whole, or mash some for a creamier texture."
    if state_key == "frozen raw" and resolved.primary_family.code == "ground_meat":
        handling = f"Transfer the thawed {self.name.lower()} to a clean plate and keep it separate from ready-to-eat food."
    operation = rule.instruction_template.format(name=self.name)
    if state_key == "canned" and "bean" in _key(self.name):
        operation = f"Stir in {self.name}, mash or purée some if desired, and heat it gently until steaming hot."
    endpoint = rule.doneness_cue.strip()
    if endpoint and endpoint.lower() not in operation.lower():
        operation = f"{operation} Stop when {endpoint[0].lower() + endpoint[1:]}"
    prep_id = f"prep:{self.name}"
    if rule.method == "assemble" or rule.cook_minutes == 0:
        return [KitchenActivity(
            component=self.name, activity_type="assemble",
            instruction=f"{handling} {operation}",
            minutes=max(rule.prep_minutes, rule.active_minutes), human_busy=True,
            attention_load=rule.attention_load, stage=rule.stage,
            parallel_ok=True, equipment=rule.equipment,
            source="ko", activity_id=f"assemble:{self.name}",
        )]
    activities = [
        KitchenActivity(
            component=self.name, activity_type="prep", instruction=handling,
            minutes=rule.prep_minutes, human_busy=True, attention_load=1,
            stage="early" if rule.stage == "early" else "middle",
            parallel_ok=True, equipment="counter", source="ko",
            activity_id=prep_id,
        ),
        KitchenActivity(
            component=self.name,
            activity_type="reheat" if rule.method == "reheat" else "cook",
            instruction=operation, minutes=rule.cook_minutes,
            human_busy=True, attention_load=rule.attention_load,
            stage=rule.stage, parallel_ok=False, equipment=rule.equipment,
            depends_on=[prep_id], source="ko",
            activity_id=f"{'reheat' if rule.method == 'reheat' else 'cook'}:{self.name}",
        ),
    ]
    if state_key == "frozen raw" and resolved.primary_family.code == "ground_meat":
        thaw_id = f"thaw:{self.name}"
        activities.insert(0, KitchenActivity(
            component=self.name, activity_type="thaw",
            instruction=(
                f"Remove all packaging and place {self.name} on a microwave-safe plate. "
                "Use the microwave defrost setting for about 7 minutes per pound as a starting point, "
                "turning it and scraping away softened portions as they thaw. Cook it immediately."
            ),
            minutes=7, human_busy=True, attention_load=.65,
            stage="early", parallel_ok=False, equipment="microwave",
            source="ko", activity_id=thaw_id,
        ))
        activities[1].depends_on = [thaw_id]
    return activities


def _family_profile(name, role):
    resolved = resolve_behavior(name, role, db_path=DB_PATH)
    if not resolved.primary_family or not resolved.method:
        return None
    rule = resolved.method
    profile = IngredientProfile(
        name=name, role=role, prep_minutes=rule.prep_minutes,
        cook_minutes=rule.cook_minutes, active_minutes=rule.active_minutes,
        attention_score=round(rule.attention_load * 10), add_stage=rule.stage,
        holdability=rule.holdability, preferred_method=rule.method,
        desired_outcome=rule.desired_outcome, failure_mode=rule.failure_mode,
        recovery_hint=rule.recovery_hint, handling_note=rule.handling_template.format(name=name),
        cooking_note=rule.instruction_template.format(name=name),
    )
    profile.publish_activities = _family_activities.__get__(profile, IngredientProfile)
    return profile


def get_ingredient_profile(name, role="ingredient"):
    """Return a smart profile or a safe generic fallback profile."""

    cleaned_name = _clean(name)
    k = _key(cleaned_name)
    if not cleaned_name:
        return IngredientProfile(name=cleaned_name, role=role)
    if role == "protein" and any(word in k for word in ("ribeye", "sirloin steak", "flank steak", "steak")):
        profile = IngredientProfile(name=cleaned_name, role=role, prep_minutes=3, cook_minutes=8, rest_minutes=3)
        profile.publish_activities = _steak_activities.__get__(profile, IngredientProfile)
        return profile
    if role == "foundation" and "mashed potato" in k:
        profile = IngredientProfile(name=cleaned_name, role=role, prep_minutes=1, cook_minutes=5, holdability="good")
        profile.publish_activities = _mashed_potato_activities.__get__(profile, IngredientProfile)
        return profile
    if role == "vegetable" and k == "broccoli":
        profile = IngredientProfile(name=cleaned_name, role=role, prep_minutes=2, cook_minutes=6, holdability="fair")
        profile.publish_activities = _broccoli_activities.__get__(profile, IngredientProfile)
        return _attach_relationships(profile)
    ckb_profile = _ckb_profile(cleaned_name, role)
    if ckb_profile is not None:
        # The verified CKB still contains the older cook-from-frozen activity
        # sequence. Preserve every other verified CKB sequence, but use the
        # state-aware safety graph for Frozen Raw until that seed is migrated.
        if k == "chicken breast":
            publish_from_ckb = ckb_profile.publish_activities

            def publish_chicken(self, strategy="", state_name=""):
                selected_state = _clean(state_name) or self.default_state
                if selected_state == "Frozen Raw":
                    return _chicken_activities(self, strategy, selected_state)
                return publish_from_ckb(strategy, state_name)

            ckb_profile.publish_activities = publish_chicken.__get__(ckb_profile, IngredientProfile)
        return _attach_relationships(ckb_profile) if role == "vegetable" else ckb_profile
    if k == "swiss chard":
        return _attach_relationships(SWISS_CHARD)
    if k == "chicken breast":
        return CHICKEN_BREAST
    if k == "black olives":
        return BLACK_OLIVES
    if k == "rice":
        return RICE
    if k.endswith(" rice"):
        profile = replace(RICE, name=cleaned_name)
        profile.publish_activities = _rice_activities.__get__(profile, IngredientProfile)
        return profile
    if k == "mushrooms":
        return _attach_relationships(MUSHROOMS)
    if k == "asparagus":
        return _attach_relationships(ASPARAGUS)
    if k in {"lemon", "lemons", "lime", "limes"}:
        profile = IngredientProfile(name=cleaned_name, role=role, prep_minutes=2, cook_minutes=0)
        profile.publish_activities = _citrus_activities.__get__(profile, IngredientProfile)
        return profile
    family_profile = _family_profile(cleaned_name, role)
    if family_profile is not None:
        return _attach_relationships(family_profile) if role == "vegetable" else family_profile
    profile = IngredientProfile(name=cleaned_name, role=role)
    return _attach_relationships(profile) if role == "vegetable" else profile
