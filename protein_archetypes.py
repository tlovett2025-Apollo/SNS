"""Round 2 main-protein execution contracts.

Ingredient KO methods contain the detailed actions. These contracts define the
coverage and safety promises every protein family must satisfy across cooking
environments, independent of any particular recipe.
"""

from dataclasses import dataclass

from config import DB_PATH
from ko_behavior import resolve_behavior


@dataclass(frozen=True)
class ProteinExecutionContract:
    family_code: str
    name: str
    safety_endpoint: str
    verification_required: bool
    rest_minutes: int
    holdability: str
    environment_methods: tuple[tuple[str, str], ...]

    def method_for(self, environment: str) -> str:
        return dict(self.environment_methods).get(str(environment or "").strip(), "")


PROTEIN_CONTRACTS = {
    item.family_code: item for item in (
        ProteinExecutionContract("ground_meat", "Ground meat", "160°F for beef/pork; 165°F for poultry", True, 0, "fair", (("stovetop", "skillet"), ("oven", "casserole"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("tough_meat", "Collagen-rich roast", "Fork-tender after passing about 190°F", True, 0, "excellent", (("stovetop", "braise"), ("oven", "oven_braise"))),
        ProteinExecutionContract("stew_cut", "Stew-cut meat", "Fork-tender after passing about 190°F", True, 0, "excellent", (("stovetop", "braise"), ("oven", "oven_braise"))),
        ProteinExecutionContract("poultry_piece", "Poultry pieces", "165°F in the thickest edible portion", True, 5, "fair", (("stovetop", "skillet"), ("oven", "roast"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("fish_fillet", "Fish fillet", "145°F in the thickest portion", True, 0, "poor", (("stovetop", "skillet"), ("oven", "roast"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("shellfish_quick", "Quick shellfish", "Opaque and pearly; 145°F when measurable", True, 0, "poor", (("stovetop", "skillet"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("sausage", "Sausage", "160°F for beef/pork; 165°F for poultry", True, 3, "fair", (("stovetop", "skillet"), ("oven", "roast"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("plant_protein", "Firm plant protein", "Hot center with browned surfaces", False, 0, "good", (("stovetop", "skillet"), ("oven", "roast"), ("soup", "simmer"), ("grill", "grill"))),
        ProteinExecutionContract("tender_steak", "Tender steak", "145°F plus at least a 3-minute rest for the verified endpoint", True, 5, "fair", (("stovetop", "skillet"), ("grill", "grill"))),
        ProteinExecutionContract("pork_cut", "Intact pork cut", "145°F plus at least a 3-minute rest", True, 3, "fair", (("stovetop", "skillet"), ("oven", "roast"), ("grill", "grill"))),
        ProteinExecutionContract("pork_roast", "Pork roast", "145°F plus at least a 3-minute rest", True, 10, "excellent", (("oven", "roast"), ("grill", "grill"))),
        ProteinExecutionContract("whole_poultry", "Whole poultry", "165°F in breast and innermost thigh", True, 15, "good", (("oven", "roast"), ("grill", "grill"))),
        ProteinExecutionContract("bacon", "Bacon", "Rendered and deeply colored without burned edges", False, 0, "fair", (("stovetop", "skillet"), ("oven", "roast"))),
        ProteinExecutionContract("ready_protein", "Ready-to-eat protein", "Steaming hot throughout when served hot", False, 0, "good", (("stovetop", "reheat"), ("oven", "reheat"), ("soup", "simmer"))),
        ProteinExecutionContract("egg", "Egg", "No liquid raw egg; 160°F when a fully verified endpoint is needed", False, 0, "poor", (("stovetop", "skillet"), ("oven", "bake"))),
        ProteinExecutionContract("ready_cured_meat", "Ready cured meat", "Steaming hot throughout when served hot", False, 0, "good", (("stovetop", "reheat"), ("oven", "reheat"), ("soup", "simmer"))),
    )
}


def protein_contract(name: str, form_name: str = "") -> ProteinExecutionContract | None:
    behavior = resolve_behavior(name, "protein", form_name, db_path=DB_PATH)
    family = behavior.primary_family
    return PROTEIN_CONTRACTS.get(family.code if family else "")


def method_for_main(name: str, form_name: str, environment: str) -> str:
    """Return the trained family method for a broad customer environment."""
    if str(form_name or "").strip().lower() in {"cooked", "canned", "ready to eat"}:
        return "reheat" if environment != "soup" else "simmer"
    contract = protein_contract(name, form_name)
    return contract.method_for(environment) if contract else ""
