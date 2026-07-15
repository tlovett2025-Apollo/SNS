"""Sauce Knowledge Objects for SNS."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class SauceIngredient:
    name: str
    quantity: str
    pantry_optional: bool = False


@dataclass(frozen=True)
class SauceProfile:
    name: str
    ingredients: List[SauceIngredient] = field(default_factory=list)
    prep_instruction: str = ""
    cook_instruction: str = ""
    prep_minutes: int = 2
    finish_minutes: int = 3


SIMPLE_STIR_FRY_SAUCE = SauceProfile(
    name="simple stir-fry sauce",
    ingredients=[
        SauceIngredient("Soy sauce", "1/4 cup"),
        SauceIngredient("Water or broth", "1/2 cup"),
        SauceIngredient("Garlic", "1–2 teaspoons minced"),
        SauceIngredient("Sugar or preferred sweetener", "1 teaspoon"),
        SauceIngredient("Cornstarch", "1 tablespoon"),
        SauceIngredient("Cold water", "1 tablespoon"),
    ],
    prep_instruction=(
        "Prepare the simple stir-fry sauce: whisk the soy sauce, 1/2 cup water or broth, garlic, and sweetener together. "
        "In a separate small cup, stir the cornstarch with 1 tablespoon cold water until completely smooth."
    ),
    cook_instruction=(
        "Stir the soy mixture and add it to the hot pan. Bring it to a simmer. "
        "Stir the cornstarch slurry again, add it gradually, and cook while stirring until the sauce is glossy and coats a spoon. "
        "Taste and adjust seasoning, salt, sweetness, or acidity."
    ),
)


SIMPLE_COMFORT_PAN_SAUCE = SauceProfile(
    name="simple comfort pan sauce",
    ingredients=[
        SauceIngredient("Cooking oil or butter", "1 tablespoon"),
        SauceIngredient("Garlic powder", "1/2 teaspoon"),
        SauceIngredient("Onion powder", "1/2 teaspoon"),
        SauceIngredient("Black pepper", "1/4 teaspoon"),
        SauceIngredient("Chicken broth", "1/2 cup"),
        SauceIngredient("Milk", "1/2 cup"),
        SauceIngredient("Cornstarch", "1 tablespoon"),
        SauceIngredient("Cold water", "1 tablespoon"),
        SauceIngredient("Salt", "only after tasting, if needed", pantry_optional=True),
    ],
    prep_instruction=(
        "Measure the garlic powder, onion powder, and black pepper. Whisk the chicken broth and milk together. "
        "In a small cup, stir the cornstarch with the cold water until smooth. Do not add salt yet; the broth may already contain enough."
    ),
    cook_instruction=(
        "Add the broth-and-milk mixture to the skillet and scrape up the browned flavor. Bring it to a gentle simmer. "
        "Stir the cornstarch mixture again, add it gradually, and stir until the sauce lightly coats everything in the skillet. "
        "Taste before adding salt; finish with more black pepper only if needed."
    ),
)


def get_sauce_profile(name: str):
    key = str(name or "").strip().lower()
    if key == "simple stir-fry sauce" or "stir-fry" in key:
        return SIMPLE_STIR_FRY_SAUCE
    if key == "simple comfort pan sauce" or "gravy or cream" in key:
        return SIMPLE_COMFORT_PAN_SAUCE
    return None
