"""Declarative cuisine identity and compatibility contracts.

Cuisine is a flavor constraint, not a word placed in a recipe title.  These
contracts identify the sauce/seasoning backbone, safe substitutions, and the
minimum evidence required before SNS claims a named flavor direction.
"""

from dataclasses import asdict, dataclass


def _key(value) -> str:
    return "" if value is None else str(value).strip().lower().replace("-", " ")


@dataclass(frozen=True)
class FlavorIdentity:
    code: str
    name: str
    sauce: str
    required_any: tuple[tuple[str, ...], ...]
    signature: tuple[str, ...]
    compatible_accents: tuple[str, ...] = ()
    substitutions: tuple[tuple[str, str], ...] = ()
    source: str = "sns_flavor_identity_v1"

    def to_dict(self) -> dict:
        return asdict(self)


FLAVOR_IDENTITIES = {
    "comfort_food": FlavorIdentity(
        "comfort_food", "Comfort Food", "simple comfort pan sauce", (),
        ("Onion powder", "Garlic powder", "Black pepper"),
        ("Butter", "Cheddar cheese", "Broth"),
    ),
    "italian": FlavorIdentity(
        "italian", "Italian", "Italian tomato sauce",
        (("Tomato sauce", "Tomato paste"), ("Garlic", "Garlic powder")),
        ("Italian seasoning", "Basil", "Oregano"),
        ("Parmesan cheese", "Mozzarella cheese", "Olive oil"),
        (("Garlic", "Garlic powder"),),
    ),
    "mexican": FlavorIdentity(
        "mexican", "Mexican", "Mexican taco sauce",
        (("Chili powder",), ("Cumin",)),
        ("Chili powder", "Cumin", "Garlic powder"),
        ("Limes", "Salsa", "Cilantro", "Poblanos", "Serranos"),
        (("Garlic", "Garlic powder"),),
    ),
    "mediterranean": FlavorIdentity(
        "mediterranean", "Mediterranean", "Mediterranean lemon herb sauce",
        (("Lemons", "Limes"), ("Garlic", "Garlic powder")),
        ("Oregano", "Black pepper", "Garlic"),
        ("Olive oil", "Greek yogurt", "Parsley"),
        (("Lemons", "Limes"), ("Garlic", "Garlic powder")),
    ),
    "bbq": FlavorIdentity(
        "bbq", "BBQ", "BBQ Sauce", (("BBQ sauce",),),
        ("BBQ sauce", "Onion powder", "Black pepper"),
        ("Hot sauce", "Mustard", "Worcestershire sauce"),
    ),
    "cajun": FlavorIdentity(
        "cajun", "Cajun", "Cajun pan sauce",
        (("Paprika", "Cajun seasoning"), ("Garlic", "Garlic powder")),
        ("Paprika", "Cayenne", "Thyme"),
        ("Hot sauce", "Celery", "Onions"),
        (("Garlic", "Garlic powder"),),
    ),
    "chinese": FlavorIdentity(
        "chinese", "Chinese", "simple stir-fry sauce",
        (("Soy sauce",), ("Garlic", "Garlic powder")),
        ("Soy sauce", "Garlic", "Ginger"),
        ("Rice vinegar", "Sesame oil", "Scallions"),
        (("Garlic", "Garlic powder"),),
    ),
    "indian": FlavorIdentity(
        "indian", "Indian", "Indian curry sauce",
        (("Curry powder", "Garam masala"),),
        ("Curry powder", "Cumin", "Turmeric"),
        ("Ginger", "Garlic", "Yogurt"),
        (("Garlic", "Garlic powder"),),
    ),
    "mild_favorite": FlavorIdentity(
        "mild_favorite", "Kid-Friendly", "mild favorite sauce", (),
        ("Garlic powder", "Onion powder"),
        ("Cheddar cheese", "Ketchup"),
    ),
}


_ALIASES = {
    "american": "comfort_food", "comfort": "comfort_food",
    "comfort food": "comfort_food", "kid": "mild_favorite",
    "kid friendly": "mild_favorite", "tex mex": "mexican",
}


def flavor_identity(cuisine) -> FlavorIdentity:
    key = _key(cuisine)
    code = _ALIASES.get(key, key.replace(" ", "_"))
    if code in FLAVOR_IDENTITIES:
        return FLAVOR_IDENTITIES[code]
    for known, identity in FLAVOR_IDENTITIES.items():
        if known.replace("_", " ") in key:
            return identity
    return FLAVOR_IDENTITIES["comfort_food"]


def ingredient_affinity_status(cuisine, affinities) -> str:
    """Return aligned, neutral, or conflicting for an ingredient's KO affinities."""
    identity = flavor_identity(cuisine)
    allowed = {_key(value).replace(" ", "_") for value in affinities if _key(value)}
    if not allowed or identity.code in {"comfort_food", "mild_favorite"}:
        return "neutral"
    aliases = {_key(identity.name).replace(" ", "_"), identity.code}
    return "aligned" if allowed & aliases else "conflicting"


def substitution_preserves_identity(cuisine, original, substitute, substitute_affinities=()) -> bool:
    identity = flavor_identity(cuisine)
    pair = (_key(original), _key(substitute))
    trained = {(_key(source), _key(target)) for source, target in identity.substitutions}
    if pair in trained:
        return True
    return ingredient_affinity_status(cuisine, substitute_affinities) != "conflicting"


def identity_requirements(cuisine) -> list[str]:
    """Return one stable representative from each required capability group."""
    return [group[0] for group in flavor_identity(cuisine).required_any if group]

