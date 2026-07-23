"""Batch-trained side-component knowledge for SNS Round 1.

This module is declarative on purpose. Ingredient identities and capability
requirements belong in the library; orchestration code consumes archetypes and
must not grow a branch for every named side.
"""

from dataclasses import dataclass


INGREDIENT_JOBS = (
    "main", "side_base", "vegetable", "aromatic", "acid", "heat",
    "sauce_liquid", "fat", "binder", "cheese", "seasoning", "garnish",
)


@dataclass(frozen=True)
class SideArchetype:
    code: str
    name: str
    method: str
    equipment: tuple[str, ...]
    required_jobs: tuple[str, ...]
    outcome: str
    holdability: str
    source: str = "round_1_side_batch"


SIDE_ARCHETYPES = {
    item.code: item for item in (
        SideArchetype("macaroni_and_cheese", "Macaroni and cheese", "boil_then_cheese_sauce", ("large saucepan or pot", "colander", "wooden spoon or whisk"), ("side_base", "cheese", "sauce_liquid_or_fat"), "Tender pasta coated in a smooth cheese sauce.", "good"),
        SideArchetype("seasoned_beans", "Seasoned beans", "simmer", ("1- to 2-quart saucepan", "wooden spoon"), ("side_base", "seasoning"), "Hot, creamy-tender beans with a balanced savory broth.", "excellent"),
        SideArchetype("steamed_vegetables", "Steamed vegetables", "steam", ("covered saucepan or pot", "steamer basket preferred"), ("vegetable",), "Bright, crisp-tender vegetables.", "fair"),
        SideArchetype("pepper_onion_medley", "Pepper and onion medley", "saute", ("12-inch skillet", "heat-safe spatula"), ("vegetable", "aromatic"), "Sweetened peppers and onions with lightly browned edges.", "good"),
        SideArchetype("mashed_potatoes", "Mashed potatoes", "boil_then_mash", ("large saucepan or pot", "potato masher"), ("side_base", "fat_or_dairy"), "Tender potatoes mashed to the chosen creamy texture.", "good"),
        SideArchetype("boxed_scalloped_potatoes", "Scalloped potatoes", "package_method", ("baking dish", "oven"), ("side_base",), "Tender sliced potatoes in a cohesive sauce.", "good"),
        SideArchetype("rice_side", "Rice", "absorption_or_appliance", ("covered saucepan, rice cooker, or pressure cooker",), ("side_base",), "Separate tender grains without a hard center.", "excellent"),
        SideArchetype("fried_rice", "Fried rice", "stir_fry", ("wok or large skillet", "heat-safe spatula"), ("side_base", "aromatic", "seasoning"), "Hot separate grains with browned edges and distributed seasoning.", "fair"),
        SideArchetype("green_bean_casserole", "Green bean casserole", "bake", ("casserole dish", "oven"), ("vegetable", "sauce_liquid", "garnish"), "Tender green beans in a creamy sauce with a crisp topping.", "good"),
        SideArchetype("simple_salad", "Simple salad", "cold_assemble", ("mixing bowl",), ("vegetable", "acid", "fat"), "Fresh, dry greens lightly dressed just before serving.", "poor"),
        SideArchetype("fresh_tomato_relish", "Fresh tomato relish", "cold_assemble", ("mixing bowl", "chef's knife and cutting board"), ("vegetable", "acid", "aromatic_or_heat"), "Juicy chopped tomato with fresh acidity and controlled heat.", "poor"),
        SideArchetype("warmed_bread_side", "Warm bread", "warm", ("small sheet pan or warming vessel",), ("side_base",), "Bread warmed through without drying.", "good"),
        SideArchetype("roasted_potatoes", "Roasted potatoes", "roast", ("rimmed sheet pan", "oven"), ("side_base", "fat"), "Tender centers and browned crisp edges.", "fair"),
        SideArchetype("corn_side", "Seasoned corn", "brief_heat", ("1- to 2-quart saucepan or skillet",), ("vegetable", "fat_or_seasoning"), "Hot sweet corn with balanced seasoning.", "good"),
        SideArchetype("au_gratin_potatoes", "Au gratin potatoes", "bake", ("baking dish", "oven"), ("side_base", "cheese", "sauce_liquid"), "Tender sliced potatoes in a browned cheese sauce.", "good"),
    )
}


SIDE_ACTIVITY_TEMPLATES = {
    "macaroni_and_cheese": "Boil and drain {base}, then finish it gently with the cheese and sauce ingredients until smoothly coated.",
    "seasoned_beans": "Put {base} in a small saucepan with a splash of water or broth. Add 1/4 teaspoon of the selected seasoning, simmer gently until steaming hot and creamy-tender, then taste before adding more.",
    "steamed_vegetables": "Steam {ingredients} together in a covered pot until bright and crisp-tender; remove individual pieces early if they finish first.",
    "pepper_onion_medley": "Sauté {ingredients} together in a wide skillet until the aromatic vegetables are sweet and the peppers bend easily with lightly browned edges.",
    "mashed_potatoes": "Boil {base} until completely tender, drain well, then mash with the selected fat or dairy to the desired texture.",
    "boxed_scalloped_potatoes": "Prepare {base} according to its package method, using the package's stated liquid, vessel, temperature, and doneness cues.",
    "rice_side": "Cook {base} by its verified absorption or appliance method; rest covered, then fluff before serving.",
    "fried_rice": "Stir-fry {ingredients} in a wide hot pan until the grains are hot, separate, and lightly browned.",
    "green_bean_casserole": "Combine {ingredients} in a casserole dish and bake until bubbling, adding the crisp topping late enough to prevent burning.",
    "simple_salad": "Dry and combine {ingredients}; dress lightly immediately before serving so the leaves stay crisp.",
    "fresh_tomato_relish": "Chop and combine {ingredients}; rest briefly, then taste for acidity and heat before serving fresh.",
    "warmed_bread_side": "Warm {base} separately until heated through without drying, then cover loosely until serving.",
    "roasted_potatoes": "Coat {base} lightly with fat, spread on a rimmed sheet pan, and roast until tender inside with browned crisp edges.",
    "corn_side": "Heat {ingredients} briefly in a small saucepan or skillet and season to taste without cooking away the corn's sweetness.",
    "au_gratin_potatoes": "Layer {base} with the cheese sauce ingredients and bake until the potatoes are tender and the top is browned.",
}


def side_archetype(code: str) -> SideArchetype | None:
    return SIDE_ARCHETYPES.get(str(code or "").strip())


def side_activity_instruction(code: str, ingredient_names: list[str]) -> str:
    template = SIDE_ACTIVITY_TEMPLATES.get(code, "Prepare {ingredients} as a separate side.")
    joined = " & ".join(ingredient_names) or "the side ingredients"
    return template.format(base=ingredient_names[0] if ingredient_names else "the side", ingredients=joined)
