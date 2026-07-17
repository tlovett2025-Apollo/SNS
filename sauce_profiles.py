"""Sauce Knowledge Objects for SNS."""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class SauceIngredient:
    name: str
    quantity: str
    pantry_optional: bool = False
    substitutes: Tuple[str, ...] = ()
    omission_consequence: str = ""
    can_omit: bool = False


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
        SauceIngredient("Cold water", "1 tablespoon", pantry_optional=True),
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
        SauceIngredient(
            "Cooking oil or butter", "1 tablespoon",
            substitutes=("Cooking oil", "Butter"),
            omission_consequence="Use rendered ground-beef fat when available; otherwise the pan may brown less evenly.",
        ),
        SauceIngredient(
            "Garlic powder", "1/2 teaspoon", pantry_optional=True,
            substitutes=("Garlic", "Fresh garlic", "Garlic granules", "Dried minced garlic"),
            omission_consequence="The finished skillet will have less garlic flavor.",
        ),
        SauceIngredient(
            "Onion powder", "1/2 teaspoon", pantry_optional=True,
            substitutes=("Onions",),
            omission_consequence="Fresh onion can provide the onion flavor instead.",
        ),
        SauceIngredient(
            "Black pepper", "1/4 teaspoon", pantry_optional=True,
            omission_consequence="The sauce will be milder, but it will still work.",
        ),
        SauceIngredient(
            "Chicken broth", "1/2 cup",
            substitutes=("Chicken stock", "Beef broth", "Beef stock", "Vegetable broth", "Bouillon"),
        ),
        SauceIngredient(
            "Milk", "1/2 cup",
            substitutes=("Evaporated milk", "Cream", "Unsweetened non-dairy milk", "Chicken broth"),
            omission_consequence="Use extra broth for a savory, less-creamy pan sauce.",
            can_omit=True,
        ),
        SauceIngredient(
            "Cornstarch", "1 tablespoon", pantry_optional=True,
            substitutes=("All-purpose flour", "Arrowroot", "Potato starch"),
            omission_consequence="The sauce will remain thinner and spoonable instead of lightly thickened.",
        ),
        SauceIngredient("Cold water", "1 tablespoon", pantry_optional=True),
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


BBQ_BRAISING_SAUCE = SauceProfile(
    name="BBQ Sauce",
    ingredients=[
        SauceIngredient(
            "Broth or water", "1–1 1/2 cups, or enough to come one-third to halfway up the meat",
            substitutes=("Chicken broth", "Beef broth", "Vegetable broth", "Water"),
        ),
        SauceIngredient("BBQ sauce", "1/2 cup"),
        SauceIngredient(
            "Worcestershire sauce", "1 tablespoon", pantry_optional=True,
            omission_consequence="The braise will be slightly less savory but will still work.",
        ),
        SauceIngredient(
            "Mustard", "1 tablespoon", pantry_optional=True,
            omission_consequence="The sauce will have less tang but will still work.",
        ),
        SauceIngredient(
            "Ketchup", "2 tablespoons", pantry_optional=True,
            omission_consequence="The BBQ sauce already supplies sweetness and tomato flavor.",
        ),
        SauceIngredient(
            "Hot sauce", "to taste", pantry_optional=True,
            omission_consequence="Serve the finished braise without additional heat.",
        ),
        SauceIngredient("Garlic powder", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Onion powder", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Black pepper", "1/4 teaspoon", pantry_optional=True),
    ],
    prep_instruction=(
        "Whisk 1/2 cup BBQ sauce with the broth or water. Add 1 tablespoon each Worcestershire sauce "
        "and mustard and 2 tablespoons ketchup when using, plus the measured garlic powder, onion powder, and black pepper. "
        "Keep the hot sauce for the final taste."
    ),
    cook_instruction=(
        "Pour the measured BBQ braising liquid around the browned meat, using only enough to come "
        "one-third to halfway up it. Scrape up the browned bits, cover, and cook gently."
    ),
    prep_minutes=3,
    finish_minutes=2,
)


def get_sauce_profile(name: str):
    key = str(name or "").strip().lower()
    if key == "simple stir-fry sauce" or "stir-fry" in key:
        return SIMPLE_STIR_FRY_SAUCE
    if key == "simple comfort pan sauce" or "gravy or cream" in key:
        return SIMPLE_COMFORT_PAN_SAUCE
    if key == "bbq sauce" or "barbecue" in key:
        return BBQ_BRAISING_SAUCE
    return None
