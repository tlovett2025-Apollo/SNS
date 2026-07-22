"""Review-first retail product knowledge contracts.

Retail identity is evidence about a purchasable object.  It never becomes a
canonical ingredient or executable cooking knowledge until the household
confirms the match and the reusable knowledge passes promotion review.
"""

from dataclasses import asdict, dataclass
import re


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


@dataclass(frozen=True)
class EvidenceField:
    value: str
    source: str
    confidence: str = "provider_reported"


@dataclass(frozen=True)
class RetailProductDraft:
    barcode: str
    product_name: str
    generic_name: str
    product_kind: str
    package_description: str
    preparation_directions: str
    evidence: tuple[EvidenceField, ...]
    household_confirmation_required: bool = True
    executable_directions: bool = False
    enrichment_status: str = "review_required"
    promotion_target: str = "retail_product_registry"
    schema_version: str = "retail_product_v1"

    def to_dict(self) -> dict:
        return asdict(self)


PRODUCT_KINDS = {
    "canned_ingredient": "A canned form of a reusable ingredient.",
    "boxed_side": "A packaged side with product-specific directions.",
    "bread_product": "A ready bread, roll, bun, or wrap used as a component.",
    "sauce_or_condiment": "A prepared sauce or condiment.",
    "prepared_beverage": "A drink; not the ingredient named in its flavor.",
    "prepared_meal": "A ready or heat-and-eat multi-component food.",
    "single_ingredient": "A packaged form of one reusable ingredient.",
    "unknown_retail_product": "A retail object awaiting household review.",
}


@dataclass(frozen=True)
class PackagedPreparationContract:
    product_kind: str
    meal_job: str
    direction_policy: str
    executable_after_confirmation: bool


PREPARATION_CONTRACTS = {
    "canned_ingredient": PackagedPreparationContract(
        "canned_ingredient", "ingredient_or_side",
        "Use canonical canned-form behavior; label directions are supplemental.", True,
    ),
    "boxed_side": PackagedPreparationContract(
        "boxed_side", "known_side",
        "Preserve package water, fat, dairy, vessel, and timing directions.", True,
    ),
    "bread_product": PackagedPreparationContract(
        "bread_product", "foundation_or_side",
        "Ready to serve; warming is optional and must not dry the bread.", True,
    ),
    "sauce_or_condiment": PackagedPreparationContract(
        "sauce_or_condiment", "flavor_builder",
        "Use as a measured prepared sauce and account for salt, sugar, acid, and heat.", True,
    ),
    "prepared_beverage": PackagedPreparationContract(
        "prepared_beverage", "beverage",
        "Do not reinterpret flavor words as ingredient identity.", False,
    ),
    "prepared_meal": PackagedPreparationContract(
        "prepared_meal", "meal_component",
        "Follow confirmed label heating and food-safety directions exactly.", True,
    ),
    "single_ingredient": PackagedPreparationContract(
        "single_ingredient", "ingredient",
        "Map to a canonical ingredient form after household confirmation.", True,
    ),
    "unknown_retail_product": PackagedPreparationContract(
        "unknown_retail_product", "unassigned",
        "Hold for review; do not generate cooking instructions.", False,
    ),
}


def preparation_contract(product_kind: str) -> PackagedPreparationContract:
    return PREPARATION_CONTRACTS.get(
        _clean(product_kind), PREPARATION_CONTRACTS["unknown_retail_product"]
    )


def classify_product(product: dict) -> str:
    evidence = _key(" ".join([
        product.get("product_name_en") or product.get("product_name") or "",
        product.get("generic_name") or "",
        product.get("categories") or "",
        product.get("packaging") or "",
    ]))
    if any(term in evidence for term in (
        "soda", "soft drink", "ginger ale", "beverage", "fruit drink", "cola"
    )):
        return "prepared_beverage"
    if any(term in evidence for term in (
        "boxed side", "macaroni and cheese", "scalloped potatoes",
        "au gratin", "rice mix", "pasta side",
    )):
        return "boxed_side"
    if any(term in evidence for term in (
        "rolls", "buns", "bread", "tortilla", "pita", "naan",
    )):
        return "bread_product"
    if any(term in evidence for term in (
        "sauce", "salsa", "ketchup", "mustard", "mayonnaise", "condiment",
    )):
        return "sauce_or_condiment"
    if "can" in evidence or "canned" in evidence or "tinned" in evidence:
        return "canned_ingredient"
    if any(term in evidence for term in (
        "ready meal", "prepared meal", "frozen dinner", "heat and eat",
    )):
        return "prepared_meal"
    if product.get("generic_name"):
        return "single_ingredient"
    return "unknown_retail_product"


def retail_product_draft(product: dict, barcode: str, source="open_food_facts") -> RetailProductDraft:
    product_name = _clean(
        product.get("product_name_en") or product.get("product_name")
        or product.get("generic_name")
    )
    generic_name = _clean(product.get("generic_name"))
    package = _clean(product.get("quantity") or product.get("packaging"))
    directions = _clean(
        product.get("preparation_en") or product.get("preparation")
        or product.get("instructions")
    )
    evidence = tuple(
        EvidenceField(_clean(value), source)
        for value in (
            product_name, generic_name, product.get("categories"), package, directions
        )
        if _clean(value)
    )
    return RetailProductDraft(
        barcode=_clean(barcode),
        product_name=product_name,
        generic_name=generic_name,
        product_kind=classify_product(product),
        package_description=package,
        preparation_directions=directions,
        evidence=evidence,
        executable_directions=False,
    )
