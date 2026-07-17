"""Runtime adapter for ingredient Knowledge Objects.

This module contains no ingredient catalog. It resolves family, form, method,
relationship, and exception data from the CKB and publishes activities for the
planner. Ingredient names are data, never branching logic.
"""

from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
import re
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


def _handling_for_state(template: str, name: str, state_name: str) -> str:
    """Render handling language that agrees with the selected physical state."""
    text = (template or "").format(name=name)
    if _key(state_name) == "frozen raw":
        return text
    # KO templates describe all supported forms. Remove frozen-only clauses
    # when the selected item is already fresh rather than telling every cook to
    # thaw every protein defensively.
    patterns = (
        rf"Thaw {re.escape(name)} when frozen[.,]\s*",
        rf"Thaw {re.escape(name)} safely,\s*",
        rf"Thaw {re.escape(name)},\s*",
        r"Thaw safely,\s*",
        r";\s*thaw before browning",
        r"\.\s*Thaw first when frozen\.",
    )
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip(" ;")
    return re.sub(
        r"(^|[.!?]\s+)([a-z])",
        lambda match: match.group(1) + match.group(2).upper(),
        text,
    )


@dataclass
class KitchenActivity:
    component: str
    activity_type: str
    instruction: str
    minutes: Optional[int] = None
    human_busy: bool = True
    attention_load: float = 1.0
    equipment: str = ""
    depends_on: List[str] = field(default_factory=list)
    stage: str = "middle"
    parallel_ok: bool = True
    source: str = "ko"
    activity_id: str = ""
    show_in_plan: bool = True


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
    prep_minutes: int = 0
    cook_minutes: int = 0
    active_minutes: int = 0
    passive_minutes: int = 0
    attention_score: int = 0
    rest_minutes: int = 0
    add_stage: str = "middle"
    holdability: str = "fair"
    preferred_method: str = ""
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
    solo_methods: tuple = ()
    companion_methods: tuple = ()
    preferred_companions: tuple = ()
    avoid_solo_methods: tuple = ()
    structure_outcomes: dict = field(default_factory=dict)
    behavior_family_codes: tuple = ()
    behavior_traits: tuple = ()
    physical_traits: tuple = ()
    flavor_domains: tuple = ()
    culinary_functions: tuple = ()
    texture_contribution: str = ""
    color_contribution: str = ""
    ko_attributes: dict = field(default_factory=dict)
    knowledge_status: str = "untrained"

    @property
    def total_active_minutes(self):
        return self.prep_minutes + (self.active_minutes or self.cook_minutes)

    @property
    def total_passive_minutes(self):
        return self.passive_minutes + self.rest_minutes

    def available_states(self):
        return list(self.states)

    def get_state(self, state_name=""):
        return self.states.get(_clean(state_name) or self.default_state)

    def effort_score(self):
        return round(
            (self.attention_score + self.work_score + self.cleanup_score + self.mental_load_score) / 4
        )

    def prep_instruction(self):
        return self.handling_note or f"No verified preparation is available for {self.name}."

    def cook_instruction(self, strategy=""):
        return self.cooking_note or f"No verified {strategy or 'cooking'} method is available for {self.name}."

    def finish_note(self):
        return self.timing_note

    def publish_activities(self, strategy="", state_name=""):
        return [KitchenActivity(
            component=self.name, activity_type="knowledge_gap",
            instruction=f"No completed KO method is available for {self.name} in this form and cooking environment.",
            minutes=0, human_busy=False, attention_load=0, equipment="counter",
            stage="early", parallel_ok=False, source="ko_gate",
            activity_id=f"knowledge_gap:{self.name}",
        )]


def _family_activities(self, strategy="", state_name=""):
    resolved = resolve_behavior(self.name, self.role, state_name, strategy, DB_PATH)
    rule = resolved.method
    if rule is None:
        return [KitchenActivity(
            component=self.name, activity_type="method_conflict",
            instruction=resolved.incompatibility_reason or
                f"No verified method connects {self.name} to the requested cooking environment.",
            minutes=0, human_busy=False, attention_load=0,
            stage="early", parallel_ok=False, equipment="counter",
            source="ko_gate", activity_id=f"method_conflict:{self.name}",
        )]

    handling = _handling_for_state(rule.handling_template, self.name, state_name)
    operation = rule.instruction_template.format(name=self.name)
    outcome = rule.desired_outcome.strip()
    if outcome and outcome.lower() not in operation.lower():
        operation = f"{operation} Aim for {outcome[0].lower() + outcome[1:]}"
    endpoint = rule.doneness_cue.strip()
    if endpoint and endpoint.lower() not in operation.lower():
        operation = f"{operation} Stop when {endpoint[0].lower() + endpoint[1:]}"

    if rule.method == "assemble" or rule.cook_minutes == 0:
        return [KitchenActivity(
            component=self.name, activity_type="assemble",
            instruction=f"{handling} {operation}",
            minutes=max(rule.prep_minutes, rule.active_minutes), human_busy=True,
            attention_load=rule.attention_load, stage=rule.stage,
            parallel_ok=True, equipment=rule.equipment,
            activity_id=f"assemble:{self.name}",
        )]

    activities = []
    thaw_id = ""
    if _key(state_name) == "frozen raw" and rule.frozen_thaw_template:
        thaw_id = f"thaw:{self.name}"
        activities.append(KitchenActivity(
            component=self.name, activity_type="thaw",
            instruction=rule.frozen_thaw_template.format(name=self.name),
            minutes=rule.frozen_thaw_minutes, human_busy=True,
            attention_load=.35, stage="early", parallel_ok=False,
            equipment=rule.frozen_thaw_equipment, activity_id=thaw_id,
        ))

    prep_id = f"prep:{self.name}"
    activities.append(KitchenActivity(
        component=self.name, activity_type="prep", instruction=handling,
        minutes=rule.prep_minutes, human_busy=True, attention_load=1,
        stage="early" if rule.stage == "early" else "middle",
        parallel_ok=True, equipment="counter",
        depends_on=[thaw_id] if thaw_id else [], activity_id=prep_id,
    ))

    activity_type = "reheat" if rule.method == "reheat" else "cook"
    cook_id = f"{activity_type}:{self.name}"
    activities.append(KitchenActivity(
        component=self.name, activity_type=activity_type,
        instruction=operation, minutes=rule.cook_minutes,
        human_busy=rule.active_minutes > 0,
        attention_load=rule.attention_load, stage=rule.stage,
        parallel_ok=False, equipment=rule.equipment,
        depends_on=[prep_id], activity_id=cook_id,
    ))

    terminal_id = cook_id
    if rule.verification_required:
        terminal_id = f"verify:{self.name}"
        activities.append(KitchenActivity(
            component=self.name, activity_type="verify",
            instruction=f"Verify {self.name}: {rule.doneness_cue}",
            minutes=2, human_busy=True, attention_load=1,
            stage=rule.stage, parallel_ok=False, equipment="counter",
            depends_on=[cook_id], activity_id=terminal_id,
        ))
    if rule.rest_minutes:
        activities.append(KitchenActivity(
            component=self.name, activity_type="rest",
            instruction=(rule.rest_template or "Rest {name} before serving.").format(name=self.name),
            minutes=rule.rest_minutes, human_busy=False, attention_load=0,
            stage="late", parallel_ok=True, equipment="counter",
            depends_on=[terminal_id], activity_id=f"rest:{self.name}",
        ))
    return activities


def _family_profile(name, role, form_name=""):
    resolved = resolve_behavior(name, role, form_name, db_path=DB_PATH)
    if not resolved.primary_family:
        return None
    rule = resolved.method or (resolved.primary_family.methods[0] if resolved.primary_family.methods else None)
    if not rule:
        return None
    families = [resolved.primary_family, *resolved.trait_families]
    profile = IngredientProfile(
        name=name, role=role, prep_minutes=rule.prep_minutes,
        cook_minutes=rule.cook_minutes, active_minutes=rule.active_minutes,
        attention_score=round(rule.attention_load * 10),
        rest_minutes=rule.rest_minutes, add_stage=rule.stage,
        holdability=rule.holdability, preferred_method=rule.method,
        desired_outcome=rule.desired_outcome, failure_mode=rule.failure_mode,
        recovery_hint=rule.recovery_hint,
        handling_note=rule.handling_template.format(name=name),
        cooking_note=rule.instruction_template.format(name=name),
        behavior_family_codes=tuple(resolved.family_codes),
        behavior_traits=tuple(dict.fromkeys(
            trait for family in families for trait in family.relationship_traits
        )),
        physical_traits=tuple(dict.fromkeys(
            trait for family in families for trait in family.physical_traits
        )),
        flavor_domains=tuple(dict.fromkeys(
            value for family in families for value in family.flavor_domains
        )),
        culinary_functions=tuple(dict.fromkeys(
            value for family in families for value in family.culinary_functions
        )),
        texture_contribution=resolved.primary_family.texture_contribution,
        color_contribution=resolved.primary_family.color_contribution,
        ko_attributes=dict(resolved.attributes),
        knowledge_status="operational",
    )
    profile.publish_activities = _family_activities.__get__(profile, IngredientProfile)
    return profile


def ingredient_relationships(name, role="vegetable", form_name=""):
    resolved = resolve_behavior(name, role, form_name, db_path=DB_PATH)
    if not resolved.primary_family:
        return {}
    families = [resolved.primary_family, *resolved.trait_families]
    methods = tuple(dict.fromkeys(rule.method for family in families for rule in family.methods))
    return {
        "solo_methods": methods,
        "companion_methods": methods,
        "preferred_companions": (),
        "avoid_solo_methods": (),
        "structure_outcomes": {},
        "behavior_family_codes": tuple(resolved.family_codes),
        "behavior_traits": tuple(dict.fromkeys(
            trait for family in families for trait in family.relationship_traits
        )),
        "physical_traits": tuple(dict.fromkeys(
            trait for family in families for trait in family.physical_traits
        )),
    }


def _load_legacy_profile(name, role):
    """Read arbitrary imported legacy KOs without adding ingredient branches."""
    try:
        with closing(sqlite3.connect(DB_PATH)) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM ko_profiles WHERE lower(component_name)=lower(?) AND role=? AND verified=1",
                (_clean(name), _clean(role).lower()),
            ).fetchone()
            if not row:
                return None
            activity_rows = con.execute(
                """SELECT * FROM ko_activities
                   WHERE lower(component_name)=lower(?) AND role=? AND verified=1
                   ORDER BY state_name, sequence""",
                (row["component_name"], row["role"]),
            ).fetchall()
        profile = IngredientProfile(
            name=row["component_name"], role=row["role"],
            prep_minutes=row["prep_minutes"] or 0, cook_minutes=row["cook_minutes"] or 0,
            active_minutes=row["active_minutes"] or 0,
            attention_score=row["attention_score"] or 0,
            rest_minutes=row["rest_minutes"] or 0, add_stage=row["add_stage"] or "middle",
            holdability=row["holdability"] or "fair",
            desired_outcome=row["desired_outcome"] or "",
            failure_mode=row["failure_mode"] or "", recovery_hint=row["recovery_hint"] or "",
            handling_note=row["handling_note"] or "", cooking_note=row["cooking_note"] or "",
            knowledge_status="legacy",
        )
        if activity_rows:
            def publish(self, strategy="", state_name=""):
                selected = [a for a in activity_rows if a["state_name"] == _clean(state_name)]
                selected = selected or [a for a in activity_rows if not a["state_name"]]
                ids = {a["sequence"]: f"{a['activity_type']}:{self.name}" for a in selected}
                return [KitchenActivity(
                    self.name, a["activity_type"], a["instruction"], a["minutes"],
                    bool(a["human_busy"]), float(a["attention_load"] or 0),
                    a["equipment_name"] or "counter",
                    [ids[a["depends_on_sequence"]]] if a["depends_on_sequence"] else [],
                    a["stage"] or "middle", bool(a["parallel_ok"]), "legacy_ko",
                    ids[a["sequence"]],
                ) for a in selected]
            profile.publish_activities = publish.__get__(profile, IngredientProfile)
        return profile
    except (sqlite3.Error, OSError, KeyError):
        return None


def get_ingredient_profile(name, role="ingredient"):
    cleaned = _clean(name)
    if not cleaned:
        return IngredientProfile(name="", role=role)
    return (
        _family_profile(cleaned, role)
        or _load_legacy_profile(cleaned, role)
        or IngredientProfile(name=cleaned, role=role)
    )
