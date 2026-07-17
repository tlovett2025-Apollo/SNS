"""Discover culinary opportunities from KO capabilities and relationships.

There are intentionally no named ingredient pairings here.  New ingredients
participate as soon as their behavior family publishes the relevant function,
trait, texture, or flavor domain.
"""

from dataclasses import asdict, dataclass
from typing import Iterable, List, Tuple

from ingredient_profiles import get_ingredient_profile


def _clean(value):
    return "" if value is None else str(value).strip()


def _split_components(value):
    return [item.strip() for item in _clean(value).split(" & ") if item.strip()]


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    name: str
    category: str
    confidence: str
    explanation: str
    matched_resources: Tuple[str, ...]

    def to_dict(self):
        data = asdict(self)
        data["matched_resources"] = list(self.matched_resources)
        return data


def _resources(candidate):
    specs = []
    specs.extend((name, "protein") for name in _split_components(candidate.get("protein")))
    specs.extend((name, "vegetable") for name in _split_components(candidate.get("vegetable")))
    specs.extend((name, "foundation") for name in _split_components(candidate.get("foundation")))
    specs.extend((name, "ingredient") for name in candidate.get("available_resources") or [])
    seen = set()
    result = []
    for name, role in specs:
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        profile = get_ingredient_profile(name, role)
        if profile.knowledge_status == "operational":
            result.append((name, profile))
    return result


def _opportunity(identifier, name, category, explanation, resources):
    return Opportunity(identifier, name, category, "High", explanation, tuple(resources))


def discover_opportunities(candidate: dict) -> List[Opportunity]:
    resources = _resources(candidate)
    discovered = []

    browning = [
        name for name, profile in resources
        if "browning-source" in profile.culinary_functions
        or "protect-dry-browning" in profile.behavior_traits
    ]
    if browning:
        discovered.append(_opportunity(
            "ko_dry_browning", "Dry-Browning Opportunity", "flavor",
            "A KO can brown before liquid enters, creating concentrated flavor for the rest of the meal.",
            browning,
        ))

    carriers = [name for name, profile in resources if "absorbs-sauce" in profile.culinary_functions]
    if carriers:
        discovered.append(_opportunity(
            "ko_flavor_carrier", "Flavor-Carrier Opportunity", "flavor",
            "A foundation KO can carry broth, aromatics, sauce, or finishing flavor instead of remaining isolated.",
            carriers,
        ))

    late = [
        name for name, profile in resources
        if set(profile.behavior_traits) & {"late-entry", "last-entry", "late-aromatic", "finish-only-default"}
    ]
    if late:
        discovered.append(_opportunity(
            "ko_late_addition", "Late-Addition Opportunity", "texture",
            "A KO retains more aroma, color, or texture when it joins near the finish.",
            late,
        ))

    anchors = [name for name, profile in resources if "protein-anchor" in profile.culinary_functions]
    depth = [name for name, profile in resources if "savory-depth" in profile.culinary_functions]
    if anchors and depth:
        matched = list(dict.fromkeys([anchors[0], depth[0]]))
        discovered.append(_opportunity(
            "ko_savory_depth_pairing", "Savory-Depth Opportunity", "flavor relationship",
            "A savory-depth KO can reinforce the main protein without requiring a conventional named pairing.",
            matched,
        ))

    stretchers = [name for name, profile in resources if "protein-stretcher" in profile.culinary_functions]
    if anchors and stretchers:
        discovered.append(_opportunity(
            "ko_protein_stretch", "Protein-Stretch Opportunity", "economy",
            "A protein-contributing KO can increase meal volume while keeping the main protein in the anchor role.",
            [anchors[0], stretchers[0]],
        ))

    return discovered


def serialize_opportunities(opportunities: Iterable[Opportunity]):
    return [opportunity.to_dict() for opportunity in opportunities]
