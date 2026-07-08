"""
Technique Profiles for Stock & Stir / SNS.

Technique babies know the general behavior of cooking methods.
Ingredient babies still decide what that technique means for THEM.
"""

from dataclasses import dataclass
from typing import Dict


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ").replace("_", " ")


@dataclass(frozen=True)
class TechniqueProfile:
    name: str
    active_attention: int = 5       # 1 low, 10 high
    cleanup_effort: int = 3         # 1 low, 10 high
    heat_level: str = "medium"
    equipment: str = "stovetop"
    goal: str = "cook until ready"
    produces_fond: bool = False
    default_parallel_ok: bool = False

    def effort_note(self) -> str:
        if self.active_attention >= 8:
            return f"{self.name} needs close attention."
        if self.active_attention <= 3:
            return f"{self.name} is mostly hands-off once started."
        return f"{self.name} needs normal attention."


_TECHNIQUES: Dict[str, TechniqueProfile] = {}


def register(t: TechniqueProfile, *aliases: str) -> TechniqueProfile:
    for value in (t.name, *aliases):
        _TECHNIQUES[_key(value)] = t
    return t


register(TechniqueProfile("saute", active_attention=8, cleanup_effort=3, heat_level="medium-high", equipment="skillet", goal="cook quickly in a little fat", produces_fond=True), "sauté", "skillet")
register(TechniqueProfile("brown", active_attention=7, cleanup_effort=4, heat_level="medium-high", equipment="skillet", goal="develop browning and flavor", produces_fond=True), "sear")
register(TechniqueProfile("simmer", active_attention=3, cleanup_effort=3, heat_level="low", equipment="pot", goal="cook gently in liquid", default_parallel_ok=True))
register(TechniqueProfile("boil", active_attention=4, cleanup_effort=3, heat_level="high", equipment="pot", goal="cook in boiling water"))
register(TechniqueProfile("steam", active_attention=4, cleanup_effort=2, heat_level="medium", equipment="pot", goal="cook with steam"))
register(TechniqueProfile("roast", active_attention=2, cleanup_effort=4, heat_level="oven", equipment="oven", goal="cook with dry oven heat", default_parallel_ok=True))
register(TechniqueProfile("bake", active_attention=2, cleanup_effort=4, heat_level="oven", equipment="oven", goal="cook with steady oven heat", default_parallel_ok=True))
register(TechniqueProfile("braise", active_attention=2, cleanup_effort=5, heat_level="low", equipment="covered pot", goal="cook low and slow until tender", default_parallel_ok=True))
register(TechniqueProfile("warm", active_attention=2, cleanup_effort=1, heat_level="low", equipment="any", goal="heat through", default_parallel_ok=True))
register(TechniqueProfile("prepare", active_attention=3, cleanup_effort=2, heat_level="varies", equipment="varies", goal="prepare as directed", default_parallel_ok=True))


def get_technique_profile(name) -> TechniqueProfile:
    cleaned = _key(name)
    return _TECHNIQUES.get(cleaned) or TechniqueProfile(_clean(name) or "cook")
