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


def get_sauce_profile(name: str):
    key = str(name or "").strip().lower()
    if key == "simple stir-fry sauce" or "stir-fry" in key:
        return SIMPLE_STIR_FRY_SAUCE
    return None
