"""Household safety, dietary, and preference contracts."""

from dataclasses import asdict, dataclass
import re


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


def _values(value) -> list[str]:
    if isinstance(value, str):
        value = value.split(",")
    if isinstance(value, dict):
        value = [value]
    result = []
    for item in value or []:
        raw = item.get("name") if isinstance(item, dict) else item
        result.extend(_clean(part) for part in str(raw or "").split(",") if _clean(part))
    return result


SAFETY_GROUPS = {
    "shellfish": {"shrimp", "prawns", "crab", "lobster", "crawfish", "crayfish", "clams", "mussels", "oysters", "scallops"},
    "crustaceans": {"shrimp", "prawns", "crab", "lobster", "crawfish", "crayfish"},
    "mollusks": {"clams", "mussels", "oysters", "scallops"},
    "peanuts": {"peanut", "peanuts", "peanut butter"},
    "tree nuts": {"almonds", "cashews", "walnuts", "pecans", "pistachios", "hazelnuts"},
    "dairy": {"milk", "butter", "cream", "cheddar cheese", "mozzarella cheese", "parmesan cheese", "yogurt", "greek yogurt", "sour cream", "cream cheese"},
    "milk": {"milk", "butter", "cream", "cheddar cheese", "mozzarella cheese", "parmesan cheese", "yogurt", "greek yogurt", "sour cream", "cream cheese"},
    "eggs": {"egg", "eggs"},
    "fish": {"salmon", "tuna", "cod", "tilapia", "trout"},
    "soy": {"soy", "soy sauce", "tofu", "tempeh"},
    "wheat": {"wheat", "flour", "bread", "pasta", "macaroni", "spaghetti", "biscuits", "rolls"},
    "gluten": {"wheat", "flour", "bread", "pasta", "macaroni", "spaghetti", "biscuits", "rolls"},
    "sesame": {"sesame", "sesame oil", "tahini"},
    "pork": {"pork", "pork chops", "pork loin", "bacon", "ham", "prosciutto", "pancetta", "pork sausage"},
    "alpha gal": {"beef", "ground beef", "steak", "pork", "pork chops", "pork loin", "bacon", "ham", "lamb", "venison"},
}

DIETARY_GROUPS = {
    "vegetarian": {
        "beef", "ground beef", "steak", "chicken", "chicken breast",
        "chicken thighs", "turkey", "ground turkey", "pork", "pork chops",
        "pork loin", "bacon", "ham", "sausage", "shrimp", "fish", "salmon",
        "tuna", "cod", "tilapia", "trout",
    },
    "vegan": {
        "beef", "ground beef", "steak", "chicken", "chicken breast",
        "chicken thighs", "turkey", "ground turkey", "pork", "pork chops",
        "pork loin", "bacon", "ham", "sausage", "shrimp", "fish", "salmon",
        "tuna", "cod", "tilapia", "trout", "egg", "eggs",
        *SAFETY_GROUPS["dairy"],
    },
    "gluten free": SAFETY_GROUPS["gluten"],
    "dairy free": SAFETY_GROUPS["dairy"],
}


@dataclass(frozen=True)
class HouseholdFitProfile:
    hard_exclusions: tuple[str, ...]
    usually_avoid: tuple[str, ...]
    favorite_directions: tuple[str, ...]
    dietary_constraints: tuple[str, ...]
    people_in_scope: tuple[str, ...]
    source: str = "household_fit_round_6"

    def to_dict(self) -> dict:
        return asdict(self)


def _expand(values, groups) -> list[str]:
    result = []
    for value in values:
        for item in (value, *groups.get(_key(value), set())):
            if _key(item) not in {_key(existing) for existing in result}:
                result.append(item)
    return result


def compile_household_fit(preferences: dict, selected_people=None) -> HouseholdFitProfile:
    preferences = preferences if isinstance(preferences, dict) else {}
    hard = []
    for field in (
        "allergies", "never_include", "excluded_items", "exclusions",
        "ingredient_exclusions",
    ):
        hard.extend(_values(preferences.get(field)))
    diets = _values(preferences.get("dietary_constraints") or preferences.get("diet"))
    for diet in diets:
        hard.extend(DIETARY_GROUPS.get(_key(diet), set()))

    requested = {_key(item) for item in _values(selected_people)}
    people_in_scope = []
    for person in preferences.get("people") or []:
        if not isinstance(person, dict) or not _clean(person.get("name")):
            continue
        name = _clean(person["name"])
        if requested and _key(name) not in requested:
            continue
        people_in_scope.append(name)
        hard.extend(_values(person.get("allergies")))
        hard.extend(_values(person.get("never_include") or person.get("exclusions")))

    return HouseholdFitProfile(
        tuple(_expand(hard, SAFETY_GROUPS)),
        tuple(_values(preferences.get("usually_avoid"))),
        tuple(_values(preferences.get("favorite_directions") or preferences.get("favorites"))),
        tuple(diets), tuple(people_in_scope),
    )


def assess_candidate_fit(candidate: dict, profile: HouseholdFitProfile) -> dict:
    ingredients = []
    for value in (
        candidate.get("protein"), candidate.get("vegetable"),
        candidate.get("foundation"), *(candidate.get("selected_extras") or []),
    ):
        ingredients.extend(part.strip() for part in _clean(value).split(" & ") if part.strip())
    ingredients.extend(
        _clean(item.get("resolved_name") or item.get("name"))
        for item in candidate.get("inventory_requirements") or []
        if isinstance(item, dict) and item.get("status") != "Omit"
    )
    ingredient_keys = {_key(item) for item in ingredients if _clean(item)}
    blocked = [item for item in profile.hard_exclusions if _key(item) in ingredient_keys]
    avoided = [item for item in profile.usually_avoid if _key(item) in ingredient_keys]
    cuisine = _key(candidate.get("cuisine"))
    favorites = [item for item in profile.favorite_directions if _key(item) in cuisine or _key(item) in ingredient_keys]
    return {
        "safe": not blocked,
        "blocked": blocked,
        "usually_avoid_matches": avoided,
        "favorite_matches": favorites,
        "preference_adjustment": len(favorites) * 12 - len(avoided) * 25,
        "people_in_scope": list(profile.people_in_scope),
    }
