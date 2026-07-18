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
            "Broth or water", "1 1/2 cups, divided",
            substitutes=("Chicken broth", "Beef broth", "Vegetable broth", "Water"),
        ),
        SauceIngredient(
            "Cooking oil or butter", "1 tablespoon",
            substitutes=("Cooking oil", "Butter", "Olive oil", "Vegetable oil", "Canola oil"),
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
        "Measure 1 1/2 cups broth or water. Whisk 1/2 cup BBQ sauce with 1 cup of it; reserve the remaining "
        "1/2 cup to adjust the liquid level during the braise. Add 1 tablespoon each Worcestershire sauce "
        "and mustard and 2 tablespoons ketchup when using, plus the measured garlic powder, onion powder, and black pepper. "
        "Keep the hot sauce for the final taste."
    ),
    cook_instruction=(
        "Pour the measured BBQ braising liquid around the browned meat, using only enough to come "
        "one-third to halfway up it. Scrape up the browned bits."
    ),
    prep_minutes=3,
    finish_minutes=2,
)


ITALIAN_TOMATO_SAUCE = SauceProfile(
    name="Italian tomato sauce",
    ingredients=[
        SauceIngredient("Tomato sauce", "1 1/2 cups"),
        SauceIngredient("Olive oil", "1 tablespoon", substitutes=("Butter", "Cooking oil")),
        SauceIngredient("Garlic powder", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Italian seasoning", "1 teaspoon", pantry_optional=True),
        SauceIngredient("Black pepper", "1/4 teaspoon", pantry_optional=True),
    ],
    prep_instruction="Measure the tomato sauce, olive oil, garlic powder, Italian seasoning, and black pepper.",
    cook_instruction=(
        "Add the tomato sauce and seasonings to the browned cooking flavor. Simmer gently until hot and slightly reduced. "
        "Taste before adding salt."
    ),
)


MEXICAN_TACO_SAUCE = SauceProfile(
    name="Mexican taco sauce",
    ingredients=[
        SauceIngredient("Tomato sauce", "1 cup"),
        SauceIngredient("Broth or water", "1/2 cup", substitutes=("Chicken broth", "Beef broth", "Vegetable broth", "Water")),
        SauceIngredient("Chili powder", "1 teaspoon"),
        SauceIngredient("Cumin", "1/2 teaspoon"),
        SauceIngredient("Garlic powder", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Limes", "1 lime", pantry_optional=True, omission_consequence="The sauce will be less bright but will still work."),
    ],
    prep_instruction="Whisk the tomato sauce, broth or water, chili powder, cumin, and garlic powder together. Keep the lime for the finish.",
    cook_instruction="Simmer the sauce with the cooked components until it coats them lightly. Take it off the heat, add lime to taste, and taste before salting.",
)


INDIAN_CURRY_SAUCE = SauceProfile(
    name="Indian curry sauce",
    ingredients=[
        SauceIngredient("Coconut milk", "1 can"),
        SauceIngredient("Broth or water", "1/2 cup", substitutes=("Chicken broth", "Vegetable broth", "Water")),
        SauceIngredient("Cumin", "1 teaspoon"),
        SauceIngredient("Coriander", "1 teaspoon"),
        SauceIngredient("Turmeric", "1/2 teaspoon"),
        SauceIngredient("Ginger", "1 teaspoon", pantry_optional=True),
        SauceIngredient("Garlic powder", "1/2 teaspoon", pantry_optional=True),
    ],
    prep_instruction="Whisk the coconut milk, broth or water, cumin, coriander, turmeric, ginger, and garlic powder together.",
    cook_instruction="Add the curry mixture and simmer gently until the components are cooked and the sauce lightly coats a spoon. Taste before adding salt.",
)


MEDITERRANEAN_LEMON_HERB_SAUCE = SauceProfile(
    name="Mediterranean lemon herb sauce",
    ingredients=[
        SauceIngredient("Olive oil", "2 tablespoons", substitutes=("Butter", "Cooking oil")),
        SauceIngredient("Chicken broth", "3/4 cup", substitutes=("Vegetable broth", "Water")),
        SauceIngredient("Lemons", "1 lemon"),
        SauceIngredient("Oregano", "1 teaspoon", pantry_optional=True),
        SauceIngredient("Garlic powder", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Black pepper", "1/4 teaspoon", pantry_optional=True),
    ],
    prep_instruction="Measure the olive oil, broth, oregano, garlic powder, and black pepper. Zest or cut the lemon, but keep its juice for the finish.",
    cook_instruction="Add the broth and seasonings to the browned cooking flavor and simmer briefly. Take the pan off the heat, add lemon to taste, and taste before salting.",
)


CAJUN_PAN_SAUCE = SauceProfile(
    name="Cajun pan sauce",
    ingredients=[
        SauceIngredient("Chicken broth", "3/4 cup", substitutes=("Vegetable broth", "Water")),
        SauceIngredient("Butter", "1 tablespoon", substitutes=("Olive oil", "Cooking oil")),
        SauceIngredient("Paprika", "1 teaspoon"),
        SauceIngredient("Garlic powder", "1/2 teaspoon"),
        SauceIngredient("Onion powder", "1/2 teaspoon"),
        SauceIngredient("Thyme", "1/2 teaspoon", pantry_optional=True),
        SauceIngredient("Hot sauce", "to taste", pantry_optional=True),
    ],
    prep_instruction="Measure the broth, butter, paprika, garlic powder, onion powder, and thyme. Keep the hot sauce for the final taste.",
    cook_instruction="Add the broth and seasonings to the browned cooking flavor and simmer until lightly reduced. Stir in the butter, then add hot sauce gradually and taste before salting.",
)


MILD_FAVORITE_SAUCE = SauceProfile(
    name="mild favorite sauce",
    ingredients=[
        SauceIngredient("Chicken broth", "1/2 cup", substitutes=("Vegetable broth", "Milk", "Water")),
        SauceIngredient("Butter", "1 tablespoon", substitutes=("Olive oil", "Cooking oil")),
        SauceIngredient("Ketchup", "2 tablespoons", pantry_optional=True),
        SauceIngredient("Garlic powder", "1/4 teaspoon", pantry_optional=True),
    ],
    prep_instruction="Measure the broth, butter, ketchup, and garlic powder.",
    cook_instruction="Add the broth and garlic powder and simmer briefly. Stir in the butter and ketchup when using, then taste before adding salt.",
)


def get_sauce_profile(name: str):
    key = str(name or "").strip().lower()
    if key == "simple stir-fry sauce" or "stir-fry" in key:
        return SIMPLE_STIR_FRY_SAUCE
    if key == "simple comfort pan sauce" or "gravy or cream" in key:
        return SIMPLE_COMFORT_PAN_SAUCE
    if key == "bbq sauce" or "barbecue" in key:
        return BBQ_BRAISING_SAUCE
    if "italian" in key or "tomato sauce or cream" in key:
        return ITALIAN_TOMATO_SAUCE
    if "taco" in key or "mexican" in key:
        return MEXICAN_TACO_SAUCE
    if "curry" in key or "indian" in key:
        return INDIAN_CURRY_SAUCE
    if "lemon herb" in key or "mediterranean" in key:
        return MEDITERRANEAN_LEMON_HERB_SAUCE
    if "cajun" in key:
        return CAJUN_PAN_SAUCE
    if "favorite" in key or "kid" in key:
        return MILD_FAVORITE_SAUCE
    if key == "simple sauce":
        return SIMPLE_COMFORT_PAN_SAUCE
    return None
