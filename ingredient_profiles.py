"""
Ingredient Profiles for Stock & Stir / SNS.

V5: Python-baby layer with practical cooking experiences.
Each ingredient can answer: how long, how active, how passive, how fussy,
how forgiving, and what instruction it wants for a given technique.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


@dataclass
class CookingExperience:
    technique: str
    total_minutes: int
    active_minutes: int
    passive_minutes: int = 0
    attention_score: int = 5      # 1 background, 10 constant attention
    cleanup_score: int = 3        # 1 minimal, 10 messy
    forgiveness_score: int = 5    # 1 fussy, 10 forgiving
    instruction: str = ""
    note: str = ""
    parallel_ok: bool = False

    @property
    def down_day_score(self) -> int:
        # Lower is easier on a down day.
        return max(1, self.active_minutes + self.attention_score + self.cleanup_score - self.forgiveness_score)


@dataclass
class IngredientProfile:
    name: str
    role: str = "ingredient"
    category: str = "general"
    prep_minutes: int = 3
    default_cook_minutes: int = 8
    rest_minutes: int = 0
    add_stage: str = "middle"      # early, middle, late
    holdability: str = "fair"      # poor, fair, good, excellent
    cost_tier: str = "budget"      # pantry, budget, moderate, high
    effort_tier: str = "medium"    # very_low, low, medium, high
    preferred_methods: List[str] = field(default_factory=lambda: ["cook"])
    handling_note: str = ""
    timing_note: str = ""
    experiences: Dict[str, CookingExperience] = field(default_factory=dict)

    def experience_for(self, technique: str) -> CookingExperience:
        raw = _key(technique)
        aliases = {
            "quick bowl": "skillet",   # raw proteins still need real cooking unless specifically reheat is defined
            "quick_bowl": "skillet",
            "plate": "skillet",
            "handheld": "skillet",
            "kid adventure": "skillet",
            "kid_adventure": "skillet",
            "saute": "skillet",
            "sauté": "skillet",
            "casserole": "bake",
            "soup": "simmer",
        }
        candidates = [raw, aliases.get(raw, raw)]
        # Foundations and already-cooked pantry items often define reheat explicitly.
        if raw == "reheat":
            candidates.insert(0, "reheat")
        for t in candidates:
            if t in self.experiences:
                return self.experiences[t]

        active = min(self.default_cook_minutes, max(3, self.default_cook_minutes // 2 + self.prep_minutes))
        passive = max(0, self.default_cook_minutes - active) + self.rest_minutes
        return CookingExperience(
            technique=technique or "cook",
            total_minutes=self.prep_minutes + self.default_cook_minutes + self.rest_minutes,
            active_minutes=active,
            passive_minutes=passive,
            attention_score=5,
            cleanup_score=3,
            forgiveness_score=5,
            instruction=f"Cook {self.name} until ready.",
            note=self.timing_note,
            parallel_ok=self.holdability in {"good", "excellent"},
        )

    def prep_instruction(self) -> str:
        return f"Prep {self.name}: {self.handling_note}" if self.handling_note else f"Prep {self.name}."


def xp(technique, total, active, passive=0, attention=5, cleanup=3, forgiveness=5, instruction="", note="", parallel=False):
    return CookingExperience(
        technique=technique,
        total_minutes=total,
        active_minutes=active,
        passive_minutes=passive,
        attention_score=attention,
        cleanup_score=cleanup,
        forgiveness_score=forgiveness,
        instruction=instruction,
        note=note,
        parallel_ok=parallel,
    )


def _bone_in_poultry(name: str) -> IngredientProfile:
    return IngredientProfile(
        name=name, role="protein", category="bone-in poultry",
        prep_minutes=5, default_cook_minutes=32, rest_minutes=5,
        add_stage="early", holdability="good", cost_tier="budget", effort_tier="medium",
        timing_note="Bone-in poultry takes longer than quick proteins and should rest before serving.",
        experiences={
            "skillet": xp(
                "skillet", 37, 14, 23, attention=7, cleanup=5, forgiveness=7,
                instruction=f"Brown {name} in the skillet, turn several times, then cover or lower the heat until fully cooked; rest before serving.",
                note="Bone-in chicken is not a 12-minute protein. Plan closer to 30+ minutes plus rest.",
            ),
            "bake": xp(
                "bake", 45, 8, 37, attention=2, cleanup=4, forgiveness=8,
                instruction=f"Bake {name} until cooked through and browned; rest before serving.",
                parallel=True,
            ),
            "simmer": xp(
                "simmer", 35, 8, 27, attention=2, cleanup=3, forgiveness=9,
                instruction=f"Simmer {name} until fully cooked and tender.",
                parallel=True,
            ),
            "reheat": xp(
                "reheat", 12, 4, 8, attention=2, cleanup=2, forgiveness=8,
                instruction=f"If {name} is already cooked, reheat gently until hot throughout.",
                parallel=True,
            ),
        },
    )


def _mushroom_profile(name: str = "Mushrooms") -> IngredientProfile:
    return IngredientProfile(
        name=name, role="vegetable", category="fungi",
        prep_minutes=4, default_cook_minutes=10, add_stage="early", holdability="good",
        timing_note="Mushrooms release water first, then brown after the moisture cooks off.",
        experiences={
            "skillet": xp(
                "skillet", 12, 8, 4, attention=6, cleanup=3, forgiveness=7,
                instruction=f"Cook {name} before delicate vegetables so they can release moisture and brown.",
                note="Give mushrooms enough pan space; crowding makes them steam.",
            ),
            "simmer": xp(
                "simmer", 12, 3, 9, attention=2, cleanup=1, forgiveness=8,
                instruction=f"Add {name} early enough to soften and flavor the liquid.",
                parallel=True,
            ),
            "reheat": xp(
                "reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=8,
                instruction=f"Warm {name} through; if they are raw, cook them first until their moisture releases.",
                parallel=True,
            ),
        },
    )


KNOWN = {
    "chicken drumsticks": _bone_in_poultry("Chicken drumsticks"),
    "drumsticks": _bone_in_poultry("Chicken drumsticks"),
    "mushrooms": _mushroom_profile("Mushrooms"),
    "mushroom": _mushroom_profile("Mushrooms"),
    "swiss chard": IngredientProfile(
        name="Swiss chard", role="vegetable", category="leafy green",
        prep_minutes=5, default_cook_minutes=4, add_stage="late", holdability="poor",
        cost_tier="budget", effort_tier="low",
        handling_note="wash well, trim tough stems, and chop leaves separately from stems if needed.",
        timing_note="Swiss chard wilts quickly and is best cooked close to serving time.",
        experiences={
            "skillet": xp("skillet", 5, 5, attention=4, cleanup=2, forgiveness=4, instruction="Add Swiss chard near the end and saute just until wilted.", note="Do not start this early; it loses texture fast."),
            "simmer": xp("simmer", 4, 2, 2, attention=2, cleanup=1, forgiveness=4, instruction="Stir Swiss chard into the hot pot near the end and simmer just until wilted."),
            "reheat": xp("reheat", 3, 2, 1, attention=2, cleanup=1, forgiveness=4, instruction="Warm Swiss chard only briefly near the end so it does not collapse."),
        },
    ),
    "asparagus": IngredientProfile(
        name="Asparagus", role="vegetable", category="quick vegetable",
        prep_minutes=4, default_cook_minutes=5, add_stage="late", holdability="poor",
        timing_note="Asparagus cooks quickly and is best near serving time.",
        experiences={
            "skillet": xp("skillet", 6, 6, attention=5, cleanup=2, forgiveness=4, instruction="Add asparagus late and saute until bright green and tender-crisp."),
            "roast": xp("roast", 12, 3, 9, attention=2, cleanup=2, forgiveness=5, instruction="Roast asparagus until tender-crisp; start it after long-cooking items are mostly done.", parallel=True),
            "reheat": xp("reheat", 3, 2, 1, attention=2, cleanup=1, forgiveness=4, instruction="Warm asparagus only briefly near the end so it stays tender-crisp."),
        },
    ),
    "brussels sprouts": IngredientProfile(
        name="Brussels sprouts", role="vegetable", category="cruciferous",
        prep_minutes=6, default_cook_minutes=12, add_stage="middle", holdability="fair",
        experiences={
            "skillet": xp("skillet", 14, 9, 5, attention=6, cleanup=3, forgiveness=6, instruction="Cook Brussels sprouts cut-side down first, then cover briefly if needed to finish tender."),
            "roast": xp("roast", 25, 6, 19, attention=2, cleanup=3, forgiveness=7, instruction="Roast Brussels sprouts until browned outside and tender inside.", parallel=True),
            "reheat": xp("reheat", 5, 2, 3, attention=2, cleanup=1, forgiveness=7, instruction="Warm Brussels sprouts through; if raw, cook them cut-side down first."),
        },
    ),
    "peas": IngredientProfile(
        name="Peas", role="vegetable", category="quick vegetable",
        prep_minutes=1, default_cook_minutes=3, add_stage="late", holdability="fair",
        experiences={
            "skillet": xp("skillet", 3, 2, 1, attention=2, cleanup=1, forgiveness=7, instruction="Add peas near the end and warm through."),
            "simmer": xp("simmer", 3, 1, 2, attention=1, cleanup=1, forgiveness=8, instruction="Stir peas in near the end just to heat through."),
            "reheat": xp("reheat", 2, 1, 1, attention=1, cleanup=1, forgiveness=8, instruction="Warm peas through near the end."),
        },
    ),
    "tilapia": IngredientProfile(
        name="Tilapia", role="protein", category="fish",
        prep_minutes=3, default_cook_minutes=5, add_stage="late", holdability="poor",
        cost_tier="moderate", effort_tier="low",
        timing_note="Tilapia is quick but fragile and does not hold well.",
        experiences={
            "skillet": xp("skillet", 6, 6, attention=8, cleanup=2, forgiveness=3, instruction="Cook tilapia quickly in the skillet and flip gently once; serve right away."),
            "bake": xp("bake", 12, 4, 8, attention=3, cleanup=2, forgiveness=5, instruction="Bake tilapia just until it flakes; avoid overcooking.", parallel=True),
            "reheat": xp("reheat", 4, 3, 1, attention=5, cleanup=1, forgiveness=3, instruction="Warm tilapia gently and briefly; it overcooks easily."),
        },
    ),
    "ground beef": IngredientProfile(
        name="Ground beef", role="protein", category="ground meat",
        prep_minutes=1, default_cook_minutes=10, holdability="good", cost_tier="budget",
        experiences={
            "skillet": xp("skillet", 10, 9, 1, attention=5, cleanup=4, forgiveness=8, instruction="Brown ground beef in the skillet, breaking it apart as it cooks; drain fat if needed."),
            "simmer": xp("simmer", 12, 6, 6, attention=3, cleanup=3, forgiveness=8, instruction="Brown ground beef first if possible, then simmer in the sauce or soup base."),
            "reheat": xp("reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction="Reheat cooked ground beef until hot."),
        },
    ),
    "italian sausage": IngredientProfile(
        name="Italian sausage", role="protein", category="sausage",
        prep_minutes=2, default_cook_minutes=14, holdability="good", cost_tier="moderate",
        experiences={
            "skillet": xp("skillet", 15, 10, 5, attention=6, cleanup=4, forgiveness=7, instruction="Brown Italian sausage in the skillet until cooked through; slice or crumble depending on the meal."),
            "simmer": xp("simmer", 18, 6, 12, attention=3, cleanup=3, forgiveness=8, instruction="Brown Italian sausage if possible, then simmer it into the sauce or soup."),
            "reheat": xp("reheat", 6, 2, 4, attention=1, cleanup=1, forgiveness=8, instruction="Reheat cooked Italian sausage until hot."),
        },
    ),
    "basmati rice": IngredientProfile(
        name="Basmati rice", role="foundation", category="rice",
        prep_minutes=2, default_cook_minutes=18, rest_minutes=10, add_stage="early", holdability="excellent",
        cost_tier="budget", effort_tier="very_low",
        timing_note="Rice is mostly passive and can rest covered while the rest of dinner finishes.",
        experiences={
            "simmer": xp("simmer", 30, 3, 27, attention=1, cleanup=2, forgiveness=8, instruction="Start basmati rice early; simmer covered, then let it rest off heat before fluffing.", parallel=True),
            "reheat": xp("reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction="Reheat prepared basmati rice and keep covered until serving.", parallel=True),
            "skillet": xp("skillet", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction="Add prepared basmati rice only to warm through; do not treat raw rice as a skillet add-in.", parallel=True),
        },
    ),
    "black beans": IngredientProfile(
        name="Black beans", role="foundation", category="beans",
        prep_minutes=2, default_cook_minutes=8, add_stage="early", holdability="excellent",
        cost_tier="budget", effort_tier="very_low",
        timing_note="Canned or cooked beans are forgiving and hold well.",
        experiences={
            "simmer": xp("simmer", 10, 3, 7, attention=1, cleanup=2, forgiveness=9, instruction="Warm black beans gently with seasoning; hold warm until serving.", parallel=True),
            "skillet": xp("skillet", 8, 4, 4, attention=2, cleanup=2, forgiveness=9, instruction="Warm black beans in the skillet or pan juices until hot.", parallel=True),
            "reheat": xp("reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction="Reheat black beans and keep warm.", parallel=True),
        },
    ),
    "biscuits": IngredientProfile(
        name="Biscuits", role="foundation", category="bread",
        prep_minutes=2, default_cook_minutes=15, add_stage="early", holdability="good",
        experiences={
            "bake": xp("bake", 17, 3, 14, attention=2, cleanup=2, forgiveness=7, instruction="Bake biscuits early enough to finish with the meal; hold warm loosely covered.", parallel=True),
            "reheat": xp("reheat", 5, 1, 4, attention=1, cleanup=1, forgiveness=8, instruction="Warm biscuits near the end or hold them wrapped.", parallel=True),
            "simmer": xp("simmer", 5, 1, 4, attention=1, cleanup=1, forgiveness=8, instruction="Keep biscuits out of the simmering pot; warm them separately and serve alongside the meal.", parallel=True),
        },
    ),
}


def _generic_by_role(name: str, role: str) -> IngredientProfile:
    role = _clean(role) or "ingredient"
    k = _key(name)

    if role == "protein":
        if "drumstick" in k or "bone" in k or "thigh" in k:
            return _bone_in_poultry(name)
        if "fish" in k or "tilapia" in k or "cod" in k or "mahi" in k or "grouper" in k:
            return IngredientProfile(name=name, role=role, category="fish", prep_minutes=3, default_cook_minutes=6, add_stage="late", holdability="poor", experiences={
                "skillet": xp("skillet", 7, 7, attention=8, cleanup=2, forgiveness=3, instruction=f"Cook {name} quickly and gently; serve right away."),
                "bake": xp("bake", 12, 4, 8, attention=3, cleanup=2, forgiveness=5, instruction=f"Bake {name} just until done; avoid overcooking.", parallel=True),
            })
        return IngredientProfile(name=name, role=role, category="protein", prep_minutes=3, default_cook_minutes=12, rest_minutes=3, holdability="fair")

    if role == "foundation":
        if "rice" in k:
            return IngredientProfile(name=name, role=role, category="rice", prep_minutes=2, default_cook_minutes=18, rest_minutes=10, add_stage="early", holdability="excellent", experiences={
                "simmer": xp("simmer", 30, 3, 27, attention=1, cleanup=2, forgiveness=8, instruction=f"Start {name} early; simmer covered, then rest before serving.", parallel=True),
                "reheat": xp("reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction=f"Reheat prepared {name} and keep covered.", parallel=True),
            })
        if "bean" in k:
            return IngredientProfile(name=name, role=role, category="beans", prep_minutes=2, default_cook_minutes=8, add_stage="early", holdability="excellent", experiences={
                "simmer": xp("simmer", 10, 3, 7, attention=1, cleanup=2, forgiveness=9, instruction=f"Warm {name} gently with seasoning; hold warm until serving.", parallel=True),
                "skillet": xp("skillet", 8, 4, 4, attention=2, cleanup=2, forgiveness=9, instruction=f"Warm {name} in the skillet or pan juices until hot.", parallel=True),
                "reheat": xp("reheat", 5, 2, 3, attention=1, cleanup=1, forgiveness=9, instruction=f"Reheat {name} and keep warm.", parallel=True),
            })
        if "potato" in k:
            return IngredientProfile(name=name, role=role, category="potatoes", prep_minutes=8, default_cook_minutes=25, add_stage="early", holdability="good", experiences={
                "bake": xp("bake", 45, 8, 37, attention=2, cleanup=3, forgiveness=8, instruction=f"Start {name} early and let the oven do most of the work.", parallel=True),
                "skillet": xp("skillet", 15, 8, 7, attention=4, cleanup=3, forgiveness=7, instruction=f"Add prepared {name} to the skillet and heat through until browned or hot."),
                "reheat": xp("reheat", 8, 3, 5, attention=2, cleanup=1, forgiveness=8, instruction=f"Reheat prepared {name} until hot.", parallel=True),
            })
        return IngredientProfile(name=name, role=role, category="foundation", prep_minutes=3, default_cook_minutes=15, add_stage="early", holdability="good")

    if role == "vegetable":
        if any(word in k for word in ["spinach", "chard", "greens", "lettuce"]):
            return IngredientProfile(name=name, role=role, category="leafy green", prep_minutes=5, default_cook_minutes=4, add_stage="late", holdability="poor", experiences={
                "skillet": xp("skillet", 5, 5, attention=4, cleanup=2, forgiveness=4, instruction=f"Add {name} near the end and cook just until wilted."),
                "simmer": xp("simmer", 4, 2, 2, attention=2, cleanup=1, forgiveness=4, instruction=f"Stir {name} into the hot pot near the end and simmer just until wilted."),
            })
        if "mushroom" in k:
            return _mushroom_profile(name)
        if any(word in k for word in ["carrot", "beet", "turnip", "parsnip"]):
            return IngredientProfile(name=name, role=role, category="root vegetable", prep_minutes=6, default_cook_minutes=18, add_stage="early", holdability="good", experiences={
                "skillet": xp("skillet", 18, 8, 10, attention=4, cleanup=3, forgiveness=7, instruction=f"Start {name} early so it has time to become tender."),
                "simmer": xp("simmer", 18, 4, 14, attention=2, cleanup=2, forgiveness=8, instruction=f"Add {name} early and simmer until tender.", parallel=True),
            })
        return IngredientProfile(name=name, role=role, category="vegetable", prep_minutes=4, default_cook_minutes=8, add_stage="middle", holdability="fair")

    return IngredientProfile(name=name, role=role)


def get_ingredient_profile(name, role="ingredient") -> Optional[IngredientProfile]:
    cleaned_name = _clean(name)
    if not cleaned_name:
        return None
    k = _key(cleaned_name)
    if k in KNOWN:
        return KNOWN[k]
    return _generic_by_role(cleaned_name, role)


def get_ingredient_profiles(names, role="ingredient") -> List[IngredientProfile]:
    if names is None:
        return []
    if isinstance(names, str):
        parts = [part.strip() for part in names.replace(" & ", ",").split(",")]
    else:
        parts = list(names)
    profiles = []
    seen = set()
    for name in parts:
        profile = get_ingredient_profile(name, role)
        if profile and _key(profile.name) not in seen:
            profiles.append(profile)
            seen.add(_key(profile.name))
    return profiles
