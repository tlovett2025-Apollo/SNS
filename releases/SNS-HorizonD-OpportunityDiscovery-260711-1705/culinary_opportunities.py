"""Prototype culinary opportunity discovery for Stock & Stir / SNS.

Horizon D, Heat 1 proves that SNS can observe the resources in a candidate and
recognize applicable culinary opportunities. These prototype rules are kept in
Python only for architectural validation. Later Heats will move curated
opportunity knowledge into the Culinary Knowledge Base (CKB).
"""

from dataclasses import asdict, dataclass
from typing import Iterable, List, Tuple


def _clean(value):
    return "" if value is None else str(value).strip()


def _key(value):
    return _clean(value).lower().replace("-", " ")


def _split_components(value):
    value = _clean(value)
    if not value:
        return []
    return [item.strip() for item in value.split(" & ") if item.strip()]


@dataclass(frozen=True)
class Opportunity:
    """A culinary observation that is applicable to the current resources."""

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


@dataclass(frozen=True)
class OpportunityRule:
    opportunity_id: str
    name: str
    category: str
    confidence: str
    explanation: str
    required_resources: Tuple[str, ...]


# Prototype rules intentionally remain small. Heat 1 proves discovery only;
# these rules do not alter candidate ranking, planning, or instructions.
OPPORTUNITY_RULES = (
    OpportunityRule(
        opportunity_id="fond_mushroom_browning",
        name="Fond-Building Opportunity",
        category="flavor",
        confidence="High",
        explanation=(
            "Mushrooms can be browned before liquid is added to concentrate flavor "
            "and create fond that can flavor the rest of the meal."
        ),
        required_resources=("mushrooms",),
    ),
    OpportunityRule(
        opportunity_id="rice_flavor_carrier",
        name="Flavor-Carrier Opportunity",
        category="flavor",
        confidence="High",
        explanation=(
            "Rice can absorb broth, deglazing liquid, aromatics, and pan flavor instead "
            "of being cooked as an isolated component."
        ),
        required_resources=("rice",),
    ),
    OpportunityRule(
        opportunity_id="swiss_chard_late_addition",
        name="Late-Addition Opportunity",
        category="texture",
        confidence="High",
        explanation=(
            "Swiss chard cooks quickly and is best added near the end so it stays tender "
            "instead of becoming limp and watery."
        ),
        required_resources=("swiss chard",),
    ),
    OpportunityRule(
        opportunity_id="chicken_mushroom_savory_pairing",
        name="Chicken-and-Mushroom Savory Opportunity",
        category="flavor relationship",
        confidence="High",
        explanation=(
            "Chicken and mushrooms support a savory pan preparation in which browned "
            "mushrooms and their fond deepen the chicken and sauce."
        ),
        required_resources=("chicken breast", "mushrooms"),
    ),
    OpportunityRule(
        opportunity_id="ground_beef_oatmeal_extension",
        name="Economical Meat-Extension Opportunity",
        category="economy",
        confidence="High",
        explanation=(
            "Oatmeal can extend compatible ground-beef preparations while helping retain "
            "moisture, increasing yield, and lowering cost per serving."
        ),
        required_resources=("ground beef", "oatmeal"),
    ),
)


def _candidate_resources(candidate):
    resources = []
    resources.extend(_split_components(candidate.get("protein")))
    resources.extend(_split_components(candidate.get("vegetable")))
    resources.extend(_split_components(candidate.get("foundation")))

    # Future pantry-backed discovery can supply additional known resources here
    # without changing the rule-matching contract.
    resources.extend(candidate.get("available_resources") or [])

    normalized = {}
    for resource in resources:
        key = _key(resource)
        if key and key not in normalized:
            normalized[key] = _clean(resource)
    return normalized


def discover_opportunities(candidate: dict) -> List[Opportunity]:
    """Return all prototype opportunities supported by the candidate resources."""

    resources = _candidate_resources(candidate)
    discovered = []

    for rule in OPPORTUNITY_RULES:
        required = tuple(_key(item) for item in rule.required_resources)
        if all(item in resources for item in required):
            discovered.append(Opportunity(
                opportunity_id=rule.opportunity_id,
                name=rule.name,
                category=rule.category,
                confidence=rule.confidence,
                explanation=rule.explanation,
                matched_resources=tuple(resources[item] for item in required),
            ))

    return discovered


def serialize_opportunities(opportunities: Iterable[Opportunity]):
    """Convert Opportunity objects into candidate-safe dictionaries."""

    return [opportunity.to_dict() for opportunity in opportunities]
