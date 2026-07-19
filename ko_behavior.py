"""Composable behavior-family intelligence for Stock & Stir Knowledge Objects.

An ingredient inherits an operational family, optional trait families, form
rules, and finally ingredient-specific exceptions.  The planner consumes the
resolved behavior; it does not invent ingredient science from the ingredient
name.
"""

from dataclasses import dataclass, field, replace
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import sqlite3
from typing import Dict, Iterable, Tuple


def _key(value):
    return str(value or "").strip().lower().replace("-", " ")


@dataclass(frozen=True)
class MethodRule:
    method: str
    forms: Tuple[str, ...]
    environment: str
    creates_environment: str
    prep_minutes: int
    cook_minutes: int
    active_minutes: int
    attention_load: float
    equipment: str
    stage: str
    handling_template: str
    instruction_template: str
    desired_outcome: str
    doneness_cue: str
    failure_mode: str
    recovery_hint: str
    holdability: str = "fair"
    verification_required: bool = False
    rest_minutes: int = 0
    rest_template: str = ""
    frozen_thaw_minutes: int = 0
    frozen_thaw_equipment: str = "counter"
    frozen_thaw_template: str = ""


@dataclass(frozen=True)
class BehaviorFamily:
    code: str
    name: str
    role: str
    description: str
    physical_traits: Tuple[str, ...]
    methods: Tuple[MethodRule, ...]
    relationship_traits: Tuple[str, ...] = ()
    portion_basis: str = "flexible"
    portion_per_standard: float = 1.0
    portion_label: str = "portion"
    portion_rounding: str = "practical"
    stretchable: bool = False
    flavor_domains: Tuple[str, ...] = ()
    culinary_functions: Tuple[str, ...] = ()
    texture_contribution: str = ""
    color_contribution: str = ""


@dataclass
class ResolvedBehavior:
    ingredient_name: str
    role: str
    form_name: str
    primary_family: BehaviorFamily | None
    trait_families: list[BehaviorFamily] = field(default_factory=list)
    method: MethodRule | None = None
    source: str = "unclassified"
    incompatibility_reason: str = ""
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def family_codes(self):
        return [family.code for family in [self.primary_family, *self.trait_families] if family]


def method(
    name, forms, environment, creates, prep, cook, active, attention,
    equipment, stage, handling, instruction, outcome, cue, failure, recovery,
    holdability="fair", verification_required=False, rest_minutes=0,
    rest_template="", frozen_thaw_minutes=0,
    frozen_thaw_equipment="counter", frozen_thaw_template="",
):
    return MethodRule(
        name, tuple(forms), environment, creates, prep, cook, active, attention,
        equipment, stage, handling, instruction, outcome, cue, failure,
        recovery, holdability, verification_required, rest_minutes,
        rest_template, frozen_thaw_minutes, frozen_thaw_equipment,
        frozen_thaw_template,
    )


READY_REHEAT = method(
    "reheat", ("cooked", "canned", "ready to eat"), "gentle moist heat",
    "warm finishing environment", 2, 4, 4, .5, "burner", "late",
    "Portion {name}; drain it first when canned.",
    "Fold in {name} near the end and heat gently until steaming hot; do not recook it.",
    "Hot throughout without becoming dry or tough.", "Steaming hot throughout.",
    "Prolonged heat dries or toughens an already-cooked ingredient.",
    "Add moisture or sauce and stop heating as soon as it is hot.", "good",
)


FAMILY_LIBRARY: Dict[str, BehaviorFamily] = {
    "ground_meat": BehaviorFamily(
        "ground_meat", "Ground raw meat", "protein",
        "Crumbled raw meat that must be fully cooked and can contribute rendered fat.",
        ("raw", "ground", "fat-rendering"),
        (method(
            "skillet", ("fresh raw", "frozen raw"), "hot lightly oiled skillet",
            "browned crumbles and rendered fat", 2, 8, 7, .7, "burner", "middle",
            "Keep raw {name} separate from ready-to-eat food. Thaw first when frozen.",
            "Add {name} to the hot skillet and break it into small crumbles. Cook until no raw areas remain, then verify safe doneness.",
            "Evenly browned, moist crumbles.", "Beef reaches 160°F; poultry reaches 165°F in the center of the thickest clump.",
            "Large clumps can brown outside while remaining undercooked inside.",
            "Break apart large clumps and continue cooking; add sauce if it becomes dry.", "fair",
            frozen_thaw_minutes=7, frozen_thaw_equipment="microwave",
            frozen_thaw_template="Remove all packaging, place {name} on a microwave-safe plate, and use the microwave defrost setting in short intervals, turning and scraping away softened portions; cook immediately.",
        ), READY_REHEAT),
        ("early-browning", "can-share-skillet-after-safe"),
    ),
    "tough_meat": BehaviorFamily(
        "tough_meat", "Collagen-rich meat", "protein",
        "A tough cut that becomes tender through a long moist cook, not a quick generic skillet pass.",
        ("raw", "dense", "collagen-rich"),
        (method(
            "braise", ("fresh raw", "frozen raw"), "covered moist heat",
            "rich braising liquid", 4, 120, 15, .2, "burner", "early",
            "Cut {name} into 1 1/2- to 2-inch pieces so it can tenderize on this stovetop schedule; thaw before browning.",
            "Brown {name} in batches, add enough liquid for a braise, cover, and cook gently until fork-tender.",
            "Fork-tender meat with connective tissue softened into the cooking liquid.",
            "The center has passed 190°F and a fork enters easily; the meat yields without springing back.",
            "A short hot cook leaves the meat safe but unpleasantly tough.",
            "Add liquid, cover, lower the heat, and continue until tender.", "excellent",
        ), method(
            "oven_braise", ("fresh raw", "frozen raw"), "covered moderate oven",
            "rich oven-braising liquid", 4, 150, 15, .15, "oven", "early",
            "Cut {name} into even pieces when appropriate; thaw before browning.",
            "Brown {name}, add braising liquid, cover tightly, and cook in a 325°F oven until fork-tender.",
            "Fork-tender meat with connective tissue softened into the cooking liquid.",
            "The center has passed 190°F and a fork enters easily; the meat yields without springing back.",
            "An uncovered or dry vessel leaves the meat tough and can scorch the sauce.",
            "Add hot liquid, cover tightly, and continue at 325°F until tender.", "excellent",
        ), READY_REHEAT),
        ("long-lead", "wet-cook"),
    ),
    "poultry_piece": BehaviorFamily(
        "poultry_piece", "Raw poultry piece", "protein",
        "Whole or cut poultry requiring contamination control and 165°F verification.",
        ("raw", "animal-protein", "safety-critical"),
        (method(
            "skillet", ("fresh raw", "frozen raw"), "moderate hot skillet",
            "browned poultry and fond", 3, 14, 8, .45, "burner", "middle",
            "Do not rinse {name}. Thaw safely, pat dry, make pieces even, and season.",
            "Brown {name}, turn, and continue cooking without crowding the pan.",
            "Brown outside and juicy inside.", "The thickest edible portion reaches 165°F.",
            "Uneven thickness can leave the center raw while thinner areas dry out.",
            "Lower the heat, cover briefly if necessary, and continue until 165°F; serve dry pieces with sauce.", "fair",
            verification_required=True, rest_minutes=5,
            rest_template="Rest {name} off heat before slicing or serving.",
            frozen_thaw_minutes=30, frozen_thaw_equipment="counter",
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water, changing the water every 30 minutes; cook immediately.",
        ), READY_REHEAT),
        ("requires-rest-when-intact", "keep-raw-separate"),
    ),
    "fish_fillet": BehaviorFamily(
        "fish_fillet", "Fish fillet", "protein",
        "Delicate fish that cooks quickly and should not be treated like meat or poultry.",
        ("raw", "delicate", "quick-cooking"),
        (method(
            "skillet", ("fresh raw", "frozen raw"), "hot skillet with light fat",
            "delicate browned surface", 2, 8, 5, .55, "burner", "late",
            "Thaw {name} when frozen, pat dry, remove obvious bones, and season.",
            "Cook {name} without moving it until the first side releases, turn carefully, and finish gently.",
            "Moist flakes with a lightly browned surface.", "The thickest portion reaches 145°F and flakes easily.",
            "Overcooking makes fish dry and chalky; turning too early tears it.",
            "Stop promptly and serve with sauce or a bright finish if it becomes dry.", "poor",
            verification_required=True, frozen_thaw_minutes=20,
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water until flexible; cook immediately.",
        ), READY_REHEAT),
        ("late-cooking", "fragile-turn"),
    ),
    "shellfish_quick": BehaviorFamily(
        "shellfish_quick", "Quick-cooking shellfish", "protein",
        "Small shellfish that changes from raw to overcooked quickly.",
        ("raw", "very-quick", "delicate"),
        (method(
            "skillet", ("fresh raw", "frozen raw"), "hot skillet",
            "lightly browned shellfish", 3, 5, 5, .8, "burner", "late",
            "Thaw {name}, drain, pat dry, and remove shells or veins as appropriate.",
            "Cook {name} in a single layer, turning once, and remove it promptly when opaque.",
            "Juicy, opaque shellfish with a tender bite.", "Opaque and pearly throughout; 145°F when temperature can be checked reliably.",
            "It becomes tight and rubbery within minutes of overcooking.",
            "Remove from heat immediately and serve with sauce; severe overcooking cannot be reversed.", "poor",
        ), READY_REHEAT),
        ("last-minute",),
    ),
    "sausage": BehaviorFamily(
        "sausage", "Sausage", "protein",
        "Seasoned ground meat in links or bulk form, sometimes already cooked.",
        ("fat-rendering", "seasoned", "form-sensitive"),
        (method(
            "skillet", ("fresh raw", "frozen raw"), "moderate skillet",
            "browned sausage and rendered fat", 2, 10, 7, .6, "burner", "middle",
            "Thaw {name} when frozen. Leave links whole or remove casings when crumbles are desired.",
            "Cook {name}, turning links or breaking bulk sausage into crumbles, until browned and safely cooked through.",
            "Brown exterior with a moist, safely cooked center.", "160°F for pork/beef sausage or 165°F for poultry sausage.",
            "High heat can burn the casing while the center remains raw.",
            "Lower the heat and cover briefly; slice only after the center is safely cooked.", "fair",
            verification_required=True, rest_minutes=3,
            rest_template="Rest {name} briefly before slicing links.",
            frozen_thaw_minutes=25,
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water; cook immediately.",
        ), method(
            "simmer", ("fresh raw", "frozen raw"), "gentle simmering liquid",
            "seasoned cooking liquid", 2, 15, 4, .3, "burner", "late",
            "Thaw {name} when frozen. Leave links whole so the center can be checked before slicing.",
            "Add {name} during the final simmer and cook gently until safely cooked through; rest briefly, then slice when the meal needs smaller pieces.",
            "Juicy, safely cooked sausage that seasons the surrounding liquid.",
            "160°F for pork/beef sausage or 165°F for poultry sausage.",
            "Adding raw sausage too late can leave the center unsafe; simmering it for the entire long cook can make it dry.",
            "Continue the gentle simmer until the center reaches the correct temperature; add liquid if the pot becomes too concentrated.", "fair",
            verification_required=True, rest_minutes=3,
            rest_template="Rest {name} briefly before slicing links.",
            frozen_thaw_minutes=25,
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water; cook immediately.",
        ), READY_REHEAT),
        ("can-flavor-fat",),
    ),
    "plant_protein": BehaviorFamily(
        "plant_protein", "Firm plant protein", "protein",
        "Ready-to-cook plant protein whose main goal is seasoning and surface texture.",
        ("ready-to-cook", "absorbent", "browning"),
        (method(
            "skillet", ("fresh", "refrigerated", "fresh raw"), "hot dry-to-lightly-oiled skillet",
            "browned plant protein", 5, 8, 7, .65, "burner", "middle",
            "Drain {name}; press excess moisture when appropriate, then cut into even pieces.",
            "Season {name} and brown it in a single layer, turning only after the first side releases.",
            "Brown edges with a seasoned, tender center.", "Several sides are browned and the center is hot.",
            "Excess surface water causes steaming and weak flavor.",
            "Let moisture evaporate, then add seasoning or sauce after browning.", "good",
        ), READY_REHEAT),
        ("browns-before-liquid",),
    ),
    "aromatic_slow": BehaviorFamily(
        "aromatic_slow", "Slow aromatic", "vegetable",
        "An aromatic vegetable that benefits from an early softening and flavor-development stage.",
        ("aromatic", "firm", "flavor-base"),
        (method(
            "saute", ("fresh", "fresh raw"), "moderate skillet with fat",
            "soft aromatic base", 3, 7, 6, .6, "burner", "early",
            "Trim and peel {name} as needed, then cut it into an even 1/2-inch dice for a skillet meal.",
            "Cook {name} in a light coating of fat, stirring occasionally, until soft and beginning to color.",
            "Soft, sweet, aromatic pieces with light browning.", "Translucent or tender with lightly colored edges.",
            "Too much heat burns the outside before the pieces soften.",
            "Lower the heat and add a small splash of liquid if browning outruns softening.", "excellent",
        ),),
        ("joins-sauce-base", "early-entry"),
    ),
    "aromatic_fast": BehaviorFamily(
        "aromatic_fast", "Fast aromatic", "vegetable",
        "A concentrated aromatic that burns quickly and usually enters after sturdy aromatics.",
        ("aromatic", "quick", "burn-prone"),
        (method(
            "bloom", ("fresh", "fresh raw", "dried"), "hot fat",
            "aromatic fat", 2, 1, 1, .9, "burner", "middle",
            "Prepare {name} in the form recorded in My Kitchen; mince fresh forms evenly.",
            "Add {name} to hot fat and stir just until fragrant, about 30–60 seconds, before adding wetter ingredients.",
            "Fragrant without dark or bitter edges.", "Strong aroma appears before visible burning.",
            "It becomes bitter when left in hot fat too long.",
            "Discard badly burned aromatics; mild over-browning can be diluted by promptly adding the next ingredient.", "fair",
        ),),
        ("blooms-in-fat",),
    ),
    "sturdy_root": BehaviorFamily(
        "sturdy_root", "Sturdy root vegetable", "vegetable",
        "Dense produce that needs small, even pieces and an early head start.",
        ("dense", "fibrous", "slow-softening"),
        (method(
            "saute", ("fresh", "fresh raw", "frozen"), "moderate skillet with fat and optional steam",
            "softened browned vegetable", 4, 10, 7, .55, "burner", "early",
            "Scrub or peel {name} as appropriate and cut it into an even 1/4-inch dice for a quick skillet meal.",
            "Cook {name} with a light coating of fat. Add a splash of water and cover briefly when needed, then uncover to finish.",
            "Tender pieces with some browned edges.", "A fork enters the center with the intended amount of resistance.",
            "Large pieces stay hard while the outside over-browns.",
            "Add a splash of liquid, cover, and continue gently until the center softens.", "excellent",
        ),),
        ("early-entry", "steam-then-brown"),
    ),
    "tender_watery": BehaviorFamily(
        "tender_watery", "Tender watery vegetable", "vegetable",
        "Fast-cooking produce that releases water and loses structure during long cooking.",
        ("high-water", "tender", "quick-cooking"),
        (method(
            "saute", ("fresh", "fresh raw", "frozen"), "hot uncrowded skillet",
            "brief moist saute", 3, 5, 5, .65, "burner", "late",
            "Trim {name} and cut it into even bite-size pieces; dry the surface when possible.",
            "Cook {name} over medium-high heat, stirring only as needed, and stop while it still holds its shape.",
            "Tender pieces with color and recognizable shape.", "Tender at the center without collapsing or releasing a pool of liquid.",
            "Crowding or long cooking makes it watery and mushy.",
            "Increase heat to evaporate excess water and stop cooking as soon as the texture is acceptable.", "poor",
        ),),
        ("late-entry", "adds-water"),
    ),
    "tomato": BehaviorFamily(
        "tomato", "Tomato", "vegetable",
        "Watery acidic produce whose outcome changes from distinct pieces to sauce with time.",
        ("high-water", "acidic", "tender", "outcome-sensitive"),
        (method(
            "brief_heat", ("fresh", "fresh raw"), "hot skillet",
            "warm juicy finishing environment", 3, 4, 4, .7, "burner", "late",
            "Remove the stem and cut {name} according to the meal structure.",
            "Warm or blister {name} briefly and stop while the pieces still hold their shape.",
            "Warm, juicy tomato with recognizable shape.", "The surface softens or blisters while the pieces remain distinct.",
            "Extended solo skillet cooking unintentionally turns it into sauce.",
            "Choose whether to stop for distinct pieces or continue deliberately as a sauce.", "poor",
        ), method(
            "simmer_sauce", ("fresh", "fresh raw", "canned"), "wet simmer",
            "tomato sauce environment", 4, 15, 8, .4, "burner", "middle",
            "Prepare {name} and any sturdy aromatics before beginning the sauce.",
            "Simmer {name} with its companion aromatics until deliberately softened into a cohesive sauce.",
            "A cohesive tomato sauce with no accidental raw or watery stage.", "Liquid reduces and the tomato texture matches the intended sauce.",
            "Stopping too early leaves a watery raw-tasting sauce; continuing too far can scorch it.",
            "Simmer longer to reduce excess water or add liquid and lower the heat if it becomes too thick.", "excellent",
        )),
        ("party-cooked", "late-when-distinct", "wet-environment-creator"),
    ),
    "leafy_tender": BehaviorFamily(
        "leafy_tender", "Tender leafy green", "vegetable",
        "A fragile leaf that wilts rapidly and should enter near the finish.",
        ("leafy", "fragile", "very-quick"),
        (method(
            "wilt", ("fresh", "fresh raw", "frozen"), "brief moist heat",
            "moist finishing environment", 3, 3, 3, .8, "burner", "late",
            "Wash {name} thoroughly and remove damaged leaves or tough stems.",
            "Add {name} near the end and toss just until wilted and hot.",
            "Bright, just-wilted leaves.", "Leaves collapse and become tender while retaining color.",
            "Long cooking makes tender greens dull, watery, and slimy.",
            "Drain excess liquid and add a bright finishing seasoning.", "poor",
        ),),
        ("last-entry", "adds-water"),
    ),
    "leafy_sturdy": BehaviorFamily(
        "leafy_sturdy", "Sturdy leafy green", "vegetable",
        "Fibrous leaves that need more softening than spinach but still dislike prolonged holding.",
        ("leafy", "fibrous", "stem-sensitive"),
        (method(
            "saute_steam", ("fresh", "fresh raw", "frozen"), "saute followed by brief steam",
            "moist green-vegetable environment", 5, 8, 6, .55, "burner", "middle",
            "Wash {name}; remove or finely cut tough stems and chop the leaves evenly.",
            "Soften sturdy stems first, add the leaves and a splash of liquid, cover briefly, then uncover and finish.",
            "Tender greens without tough stems or excess water.", "Stems are tender and leaves no longer taste raw or fibrous.",
            "Undercooked stems remain tough; overcooked leaves become dull and watery.",
            "Continue covered for tough stems or uncover to evaporate excess liquid.", "fair",
        ),),
        ("staged-stem-and-leaf",),
    ),
    "raw_finish": BehaviorFamily(
        "raw_finish", "Normally raw finishing produce", "vegetable",
        "Produce normally used raw, chilled, or added at service rather than generically fried.",
        ("ready-to-eat", "fresh", "texture-sensitive"),
        (method(
            "assemble", ("fresh", "fresh raw", "refrigerated"), "no-cook counter",
            "fresh finishing component", 4, 0, 4, 1, "counter", "finish",
            "Wash and prepare {name} for serving; remove damaged or inedible parts.",
            "Keep {name} fresh and add it during assembly or at the table.",
            "Fresh flavor and intact texture.", "Prepared, fresh, and ready to eat.",
            "Unrequested heat destroys the texture that gives it value.",
            "Replace with a fresh portion; cooked texture cannot be reversed.", "poor",
        ),),
        ("no-cook-default",),
    ),
    "white_rice": BehaviorFamily(
        "white_rice", "White or aromatic rice", "foundation",
        "Dry white rice cooked with measured liquid and a covered rest.",
        ("dry-grain", "starch", "long-lead"),
        (method(
            "simmer", ("dry", "shelf stable"), "covered gentle simmer",
            "starchy covered pot", 3, 18, 3, .15, "burner", "early",
            "Measure and rinse {name} when appropriate; measure its cooking liquid.",
            "Bring {name} and its measured liquid to a simmer, cover, reduce heat, and cook without lifting the lid; rest covered before fluffing.",
            "Tender separate grains.", "Liquid is absorbed and the grains are tender after the covered rest.",
            "Incorrect liquid or heat causes hard, scorched, or gummy rice.",
            "For firm rice add a little hot liquid and continue covered; for wet rice rest uncovered briefly.", "good",
        ), READY_REHEAT),
        ("start-first", "passive-long-lead"),
    ),
    "brown_rice": BehaviorFamily(
        "brown_rice", "Brown or wild rice", "foundation",
        "Whole-grain rice requiring more liquid and substantially more time than white rice.",
        ("dry-grain", "whole-grain", "long-lead"),
        (method(
            "simmer", ("dry", "shelf stable"), "covered gentle simmer",
            "starchy covered pot", 4, 42, 4, .15, "burner", "early",
            "Rinse {name}, check for debris, and measure the grain and liquid.",
            "Simmer {name} covered at low heat until the grains are tender, then rest covered before fluffing.",
            "Tender, pleasantly chewy grains.", "The grain is tender through the center without a hard core.",
            "Using a white-rice timeline leaves whole-grain rice hard and undercooked.",
            "Add hot liquid and continue covered until the center softens.", "excellent",
        ), READY_REHEAT),
        ("very-long-lead",),
    ),
    "cauliflower_rice": BehaviorFamily(
        "cauliflower_rice", "Cauliflower rice", "foundation",
        "Finely chopped vegetable used in the serving role of rice but not cooked like a grain.",
        ("vegetable", "high-water", "quick-cooking"),
        (method(
            "saute", ("fresh", "fresh raw", "frozen"), "hot skillet",
            "dry vegetable foundation", 2, 6, 6, .7, "burner", "late",
            "Break up clumps in {name} and remove excess surface moisture.",
            "Sauté {name} uncovered, stirring occasionally, until hot and tender but not wet or mushy.",
            "Tender, separate cauliflower granules.", "Hot and tender with no raw crunch or pooled water.",
            "Adding grain-style liquid makes it watery and mushy.",
            "Increase heat and cook uncovered to evaporate water; stop before it collapses.", "poor",
        ),),
        ("never-grain-liquid",),
    ),
    "pasta": BehaviorFamily(
        "pasta", "Dry pasta or noodles", "foundation",
        "A dry starch cooked in ample boiling liquid and drained or finished in sauce.",
        ("dry-starch", "boil", "separate-pot"),
        (method(
            "boil", ("dry", "shelf stable"), "boiling salted water",
            "hot drained pasta", 2, 10, 4, .35, "burner", "early",
            "Choose a pot large enough for {name} and bring the cooking water to a full boil.",
            "Boil {name}, stirring early to prevent sticking. Taste near the package's minimum time, reserve cooking water if useful, and drain when tender.",
            "Tender pasta with the intended bite.", "A tasted piece has no hard center and the desired firmness.",
            "Overcooking makes pasta soft and fragile; too little water encourages sticking.",
            "Drain immediately when over-softening begins; loosen sticky pasta with sauce or reserved water.", "fair",
        ), READY_REHEAT),
        ("boiling-water-required",),
    ),
    "legume": BehaviorFamily(
        "legume", "Bean or legume", "foundation",
        "A form-sensitive foundation: canned/cooked forms reheat, while dry forms need a long full cook.",
        ("starchy", "protein-contributing", "form-sensitive"),
        (method(
            "simmer", ("dry", "shelf stable"), "long moist simmer",
            "thickening legume pot", 8, 75, 10, .15, "burner", "early",
            "Sort and rinse {name}; soak when the specific legume or schedule benefits from it.",
            "Cover {name} with fresh cooking liquid and simmer gently until fully tender, adding hot liquid as needed.",
            "Creamy-tender legumes with no hard or chalky center.", "A bean crushes creamy throughout when tasted.",
            "Acid or old beans can delay softening; an eight-minute generic cook leaves dry legumes inedible.",
            "Continue with hot liquid until tender; add acidic ingredients after softening when possible.", "excellent",
        ), method(
            "reheat", ("canned", "cooked", "ready to eat"), "gentle moist heat",
            "creamy thickening foundation", 2, 4, 4, .5, "burner", "late",
            "Drain and rinse {name}. Leave it whole, or mash some for a creamier texture.",
            "Stir in {name}, mash or purée some if desired, and heat gently until steaming hot.",
            "Hot creamy-tender legumes without recooking.", "Steaming hot throughout.",
            "Prolonged heat can turn cooked legumes pasty or scorch a thickened base.",
            "Add liquid to loosen and stop heating as soon as it is hot.", "good",
        )),
        ("dry-versus-canned-critical", "can-stretch-protein", "soup-friendly"),
    ),
    "bread_wrap": BehaviorFamily(
        "bread_wrap", "Bread or wrap foundation", "foundation",
        "A ready-to-eat foundation that may be warmed or toasted but never generically simmered.",
        ("ready-to-eat", "assembly", "dry-heat"),
        (method(
            "warm", ("fresh", "shelf stable", "refrigerated", "frozen"), "brief dry heat",
            "warm assembly foundation", 1, 3, 2, .4, "burner", "finish",
            "Separate the amount of {name} needed and thaw it first when frozen.",
            "Warm or toast {name} briefly, then keep it covered until assembly.",
            "Warm and flexible, or intentionally crisp when toasted.", "Heated through without drying or burning.",
            "Long heating makes bread dry and wraps brittle.",
            "Cover briefly to soften or replace a badly burned portion.", "fair",
        ),),
        ("assembly-foundation",),
    ),
    "raw_fruit": BehaviorFamily(
        "raw_fruit", "Normally raw fruit", "vegetable",
        "Fruit normally served fresh rather than assigned a generic vegetable cooking step.",
        ("ready-to-eat", "sweet", "fresh"),
        (method(
            "assemble", ("fresh", "frozen", "refrigerated"), "no-cook counter",
            "fresh finishing component", 4, 0, 4, 1, "counter", "finish",
            "Wash {name}; peel, core, pit, or hull it as appropriate, then cut for serving.",
            "Add {name} fresh during assembly unless the meal explicitly requests a cooked-fruit preparation.",
            "Fresh flavor and appropriate ripe texture.", "Prepared and ready to eat.",
            "Generic skillet cooking can destroy fresh texture or release unwanted liquid.",
            "Replace with a fresh portion or deliberately convert it to a compote.", "poor",
        ),),
        ("no-cook-default",),
    ),
}

# Retail stew meat is already cut into small pieces and reaches its intended
# tenderness sooner than a whole brisket or roast. It remains collagen-rich
# long-cook meat, but owns a distinct verified time instead of forcing every
# member of the broad tough-meat family onto one clock.
FAMILY_LIBRARY["stew_cut"] = replace(
    FAMILY_LIBRARY["tough_meat"],
    code="stew_cut",
    name="Stew-cut collagen-rich meat",
    description="Small stew-ready pieces that become fork-tender through a moderate moist cook.",
    methods=(
        replace(
            FAMILY_LIBRARY["tough_meat"].methods[0],
            cook_minutes=75,
            instruction_template=(
                "Brown {name} in batches, add enough liquid for a braise, cover, "
                "and simmer gently until the pieces are fork-tender."
            ),
        ),
        READY_REHEAT,
    ),
)

# Additional operational families discovered by auditing every selectable KO.
# They use the same contract as the original library; ingredient names below
# only classify membership and never contain the cooking instructions.
FAMILY_LIBRARY.update({
    "tender_steak": BehaviorFamily(
        "tender_steak", "Tender intact steak", "protein",
        "An intact tender cut cooked with dry heat, verified by temperature, and rested before slicing.",
        ("raw", "intact-muscle", "quick-dry-heat"),
        (method(
            "skillet", ("fresh raw", "frozen raw", "refrigerated"), "very hot skillet",
            "browned fond", 4, 9, 7, .7, "burner", "middle",
            "Thaw {name} when frozen, pat it dry, and season both sides.",
            "Sear {name} without moving it. When the cooked color has climbed roughly halfway to two-thirds up the side and the steak releases readily, turn once; cook to the chosen doneness, then rest before slicing.",
            "A deeply browned exterior and the requested interior doneness.",
            "For the verified safety endpoint, the center reaches 145°F followed by at least a 3-minute rest.",
            "Turning too early prevents browning; cooking only by the clock can over- or undercook a thick steak.",
            "Lower the heat if the crust darkens too quickly; rest and serve a more-done steak with sauce.", "fair",
            verification_required=True, rest_minutes=5,
            rest_template="Rest {name} for at least 5 minutes before slicing across the grain.",
            frozen_thaw_minutes=30,
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water, changing the water every 30 minutes; cook immediately.",
        ), READY_REHEAT), ("rest-required", "temperature-led"),
    ),
    "pork_cut": BehaviorFamily(
        "pork_cut", "Intact pork cut", "protein",
        "A pork chop or small loin portion that should remain juicy while reaching a verified endpoint.",
        ("raw", "intact-muscle", "lean"),
        (method(
            "skillet", ("fresh raw", "frozen raw", "refrigerated"), "moderately hot skillet",
            "browned pork and fond", 4, 12, 7, .5, "burner", "middle",
            "Thaw {name}, pat dry, trim only excess exterior fat, and make portions even.",
            "Brown {name}, turn, lower the heat as needed, and cook until the center is safely done; rest before slicing.",
            "Brown outside and juicy inside.", "The thickest part reaches 145°F, followed by at least a 3-minute rest.",
            "High heat can dry the outside before a thick center reaches temperature.",
            "Lower the heat and cover briefly; serve dry pork with sauce or pan juices.", "fair",
            verification_required=True, rest_minutes=3,
            rest_template="Rest {name} for at least 3 minutes before slicing or serving.",
            frozen_thaw_minutes=30,
            frozen_thaw_template="Keep {name} sealed and thaw it in cold water; cook immediately.",
        ), READY_REHEAT), ("rest-required",),
    ),
    "ready_protein": BehaviorFamily(
        "ready_protein", "Ready-to-eat protein", "protein",
        "A cooked or canned protein needing preparation and gentle reheating, never recooking.",
        ("ready-to-eat", "form-sensitive"), (method(
            "reheat", ("canned", "pantry"), "gentle moist heat",
            "warm finishing environment", 2, 4, 4, .5, "burner", "late",
            "Drain {name} and break it into serving-size pieces.",
            "Fold in {name} near the end and heat gently until steaming hot; do not recook it.",
            "Hot moist protein.", "Steaming hot throughout.",
            "Prolonged heat dries an already-cooked protein.",
            "Add moisture or sauce and stop heating promptly.", "good",
        ), method(
            "reheat", ("cooked", "ready to eat", "refrigerated"), "gentle moist heat",
            "warm finishing environment", 2, 4, 4, .5, "burner", "late",
            "Remove unwanted bones or skin from {name}, then slice or shred it as the meal needs.",
            "Fold in {name} near the end and heat gently until steaming hot; do not recook it.",
            "Hot moist protein.", "Steaming hot throughout.",
            "Prolonged heat dries an already-cooked protein.",
            "Add moisture or sauce and stop heating promptly.", "good",
        )), ("late-entry",),
    ),
    "egg": BehaviorFamily(
        "egg", "Egg", "protein",
        "A fast-setting protein whose preparation determines the method and endpoint.",
        ("quick-cooking", "coagulating", "delicate"),
        (method(
            "skillet", ("fresh raw", "refrigerated"), "low-to-moderate skillet",
            "soft egg curds", 3, 5, 5, .9, "burner", "late",
            "Crack {name} into a separate bowl, check for shell, and whisk for scrambled eggs.",
            "Cook {name} over moderate heat, folding gently as curds form, and remove from heat just before the curds look fully dry.",
            "Tender, moist curds.", "No liquid raw egg remains; cook to 160°F when serving people who need a fully verified endpoint.",
            "High heat makes eggs rubbery and watery.",
            "Remove from heat immediately; fold in a small amount of dairy or sauce if they become dry.", "poor",
        ), READY_REHEAT), ("last-minute",),
    ),
    "mushroom": BehaviorFamily(
        "mushroom", "Fresh mushroom", "vegetable",
        "A high-water fungus that browns only after surface and released moisture evaporate.",
        ("high-water", "browning", "crowding-sensitive"),
        (method(
            "saute", ("fresh", "frozen"), "dry uncrowded hot skillet",
            "browned savory skillet", 4, 8, 5, .55, "burner", "early",
            "Brush or quickly rinse attached dirt from {name}, dry well, trim the stem ends, and cut evenly.",
            "Cook {name} in an uncrowded layer until released moisture evaporates and the bottoms brown; turn and finish cooking.",
            "Deeply browned mushrooms without pooled water.", "Moisture has evaporated and broad surfaces are browned and tender.",
            "Crowding or early liquid steams mushrooms and prevents browning.",
            "Increase heat or work in batches; add sauce only after browning.", "good",
        ), READY_REHEAT), ("protect-dry-browning",),
    ),
    "quick_green": BehaviorFamily(
        "quick_green", "Quick green vegetable", "vegetable",
        "A crisp green vegetable that benefits from brief sauté-steaming and a visible color/texture endpoint.",
        ("green", "crisp", "quick-cooking"),
        (method(
            "saute_steam", ("fresh", "frozen"), "hot skillet then brief steam",
            "moist green-vegetable environment", 4, 6, 5, .6, "burner", "middle",
            "Wash {name}, trim tough ends or strings, and cut thick pieces evenly.",
            "Sauté {name} briefly, add a small splash of water, cover until nearly tender, then uncover to evaporate the water.",
            "Bright color and crisp-tender centers.", "Brightened in color and fork-tender with a little bite.",
            "Long covered cooking turns green vegetables dull and soft.",
            "Uncover promptly and finish with a bright seasoning; severe overcooking cannot be reversed.", "fair",
        ), READY_REHEAT), ("brief-moist-heat",),
    ),
    "cruciferous": BehaviorFamily(
        "cruciferous", "Dense cruciferous vegetable", "vegetable",
        "Dense florets or sprouts that need even sizing and enough heat to tenderize without sulfurous overcooking.",
        ("dense", "floret-or-sprout", "steam-friendly"),
        (method(
            "saute_steam", ("fresh", "frozen"), "hot skillet then covered steam",
            "moist vegetable environment", 5, 7, 5, .5, "burner", "middle",
            "Trim {name} and cut it into evenly sized florets, wedges, or halves; include tender stems.",
            "Brown {name} briefly, add a small splash of water, cover until almost tender, then uncover and cook off the water.",
            "Tender centers, browned edges, and retained color.", "A fork enters the thickest part with slight resistance and no raw crunch.",
            "Uneven pieces cook unevenly; prolonged covered heat creates a dull, sulfurous result.",
            "Cut large pieces smaller and continue briefly; uncover to remove excess water.", "fair",
        ), READY_REHEAT), ("even-size-critical",),
    ),
    "pepper": BehaviorFamily(
        "pepper", "Fresh pepper", "vegetable",
        "A thin-walled or fleshy pepper that can soften with aromatics or remain crisp as a late addition.",
        ("aromatic", "outcome-sensitive", "quick-to-medium"),
        (method(
            "saute", ("fresh", "frozen"), "moderately hot skillet",
            "sweet aromatic base", 4, 7, 5, .55, "burner", "early",
            "Wash {name}; remove stem, seeds, and membranes as desired, then cut evenly.",
            "Sauté {name} until softened and lightly colored, stopping earlier when a crisp texture is intended.",
            "Sweetened pepper with the intended crisp or soft texture.", "Edges color and the pieces bend easily while retaining the chosen bite.",
            "Crowding releases water; very high heat can scorch thin pieces.",
            "Cook uncovered to evaporate water or lower the heat when edges darken too quickly.", "good",
        ), READY_REHEAT), ("joins-aromatics", "joins-sauce-base"),
    ),
    "winter_squash": BehaviorFamily(
        "winter_squash", "Dense winter squash", "vegetable",
        "A dense squash that needs peeling/cutting awareness and substantially longer tenderizing than summer squash.",
        ("dense", "starchy", "longer-cooking"),
        (method(
            "saute_steam", ("fresh", "frozen"), "covered moist skillet",
            "soft starchy vegetable environment", 8, 15, 8, .35, "burner", "early",
            "Cut {name} safely on a stable board; remove seeds, peel when needed, and cut into small even cubes.",
            "Brown {name} lightly, add a small amount of liquid, cover, and cook gently until completely tender; uncover to reduce excess liquid.",
            "Creamy-tender centers with intact pieces.", "A fork slides through the center without resistance.",
            "Large uneven pieces remain hard; excess liquid makes them waterlogged.",
            "Cut hard pieces smaller and continue covered; uncover to evaporate excess liquid.", "excellent",
        ), READY_REHEAT), ("long-lead-vegetable",),
    ),
    "cabbage": BehaviorFamily(
        "cabbage", "Cabbage", "vegetable",
        "Layered leaves and a firm core that soften at different rates.",
        ("leafy", "dense-core", "volume-reducing"),
        (method(
            "saute_steam", ("fresh",), "wide skillet with brief steam",
            "sweet softened cabbage environment", 6, 10, 7, .5, "burner", "middle",
            "Remove damaged outer leaves from {name}, cut out the tough core, and slice the leaves evenly.",
            "Cook {name} in a wide skillet until beginning to color, add a splash of liquid, cover briefly, then uncover and finish.",
            "Sweet, tender cabbage with some structure.", "Thick pieces are tender and the raw sulfurous bite is gone.",
            "Crowding traps water; prolonged cooking can make cabbage limp and sulfurous.",
            "Uncover and raise the heat to evaporate water; add acid at the finish to brighten it.", "good",
        ), READY_REHEAT), ("shrinks-substantially",),
    ),
    "okra": BehaviorFamily(
        "okra", "Okra", "vegetable",
        "A mucilage-rich pod whose texture depends strongly on dryness, cutting, acid, and cooking environment.",
        ("mucilage-rich", "surface-dryness-critical"),
        (method(
            "saute", ("fresh", "frozen"), "hot dry skillet",
            "browned low-moisture vegetable environment", 5, 9, 6, .6, "burner", "middle",
            "Wash {name} and dry it very thoroughly; trim the caps without cutting deeply into the pods.",
            "Cook {name} in a lightly oiled uncrowded skillet, stirring only as needed, until browned at the edges and tender.",
            "Tender pods with browned edges and controlled slipperiness.", "Edges are browned and the pod is tender without added water.",
            "Water, crowding, and excessive stirring can increase a slippery texture.",
            "Increase heat and spread it out; add tomato or another acidic ingredient only when deliberately making a wet dish.", "fair",
        ), READY_REHEAT), ("dry-or-deliberately-wet",),
    ),
    "crisp_stir_fry": BehaviorFamily(
        "crisp_stir_fry", "Crisp stir-fry vegetable", "vegetable",
        "A crisp, high-water vegetable used for crunch and therefore added late.",
        ("crisp", "high-water", "late-entry"),
        (method(
            "saute", ("fresh",), "very hot skillet or wok",
            "crisp stir-fry environment", 4, 3, 3, .8, "burner", "late",
            "Rinse and drain {name} well; cut only as needed and dry the surface.",
            "Add {name} late and stir-fry briefly over high heat just until hot and slightly tender.",
            "Hot, crisp pieces with no pooled liquid.", "Heated through while retaining a clear crunch.",
            "Long cooking makes it limp and watery.",
            "Remove from heat promptly; lost crunch cannot be restored.", "poor",
        ), READY_REHEAT), ("late-entry",),
    ),
    "sweet_kernel": BehaviorFamily(
        "sweet_kernel", "Sweet kernel vegetable", "vegetable",
        "Corn or peas that need only brief heating when fresh/frozen and gentle reheating when canned.",
        ("small", "sweet", "quick-cooking"),
        (method(
            "brief_heat", ("fresh", "frozen"), "brief moist heat",
            "sweet finishing component", 2, 5, 3, .4, "burner", "late",
            "Prepare {name}; drain canned forms or break up frozen clumps.",
            "Add {name} near the end and heat only until tender and hot.",
            "Sweet, plump kernels or peas.", "Hot throughout and tender without wrinkling or collapse.",
            "Prolonged heat dulls sweetness and makes the texture starchy.",
            "Stop cooking and add a little fat or bright seasoning.", "fair",
        ), READY_REHEAT), ("late-entry",),
    ),
    "artichoke": BehaviorFamily(
        "artichoke", "Artichoke", "vegetable",
        "A form-critical vegetable: fresh whole artichokes need a long steam, while canned hearts only reheat.",
        ("form-sensitive", "fibrous", "long-cook-when-fresh"),
        (method(
            "simmer", ("fresh",), "covered steam or simmer",
            "steamy tenderizing environment", 8, 35, 5, .15, "burner", "early",
            "Trim the stem and sharp leaf tips from {name}; rinse between the leaves and rub cut surfaces with lemon.",
            "Steam or gently simmer {name} covered until a leaf pulls free easily and the heart is tender.",
            "Tender edible leaf bases and heart.", "An inner leaf pulls out easily and a knife enters the heart without resistance.",
            "A short skillet cook leaves fresh artichoke fibrous and inedible.",
            "Continue steaming with enough water until tender.", "good",
        ), READY_REHEAT), ("form-critical",),
    ),
})


def _add_family_method(family_code, rule):
    family = FAMILY_LIBRARY[family_code]
    FAMILY_LIBRARY[family_code] = replace(family, methods=(*family.methods, rule))


def grill_method(
    forms, prep, cook, active, stage, handling, instruction, outcome, cue,
    failure, recovery, holdability="poor", verification_required=False,
    rest_minutes=0, rest_template="",
):
    return method(
        "grill", forms, "preheated outdoor grill", "grilled dry-heat environment",
        prep, cook, active, .65, "grill", stage, handling, instruction, outcome,
        cue, failure, recovery, holdability,
        verification_required=verification_required, rest_minutes=rest_minutes,
        rest_template=rest_template,
    )


def casserole_method(
    forms, prep, cook, active, handling, instruction, outcome, cue,
    failure, recovery, verification_required=False,
):
    return method(
        "casserole", forms, "covered or uncovered baking dish",
        "cohesive oven-baked meal", prep, cook, active, .25, "oven", "middle",
        handling, instruction, outcome, cue, failure, recovery, "good",
        verification_required=verification_required,
    )


_add_family_method("poultry_piece", casserole_method(
    ("fresh raw", "frozen raw"), 4, 30, 5,
    "Thaw {name} when frozen; do not rinse it. Pat dry and cut thick pieces to an even casserole size.",
    "Bake {name} in the assembled dish until the thickest piece is safely cooked.",
    "Juicy chicken integrated with the sauce and vegetables.",
    "The thickest edible portion reaches 165°F.",
    "Large uneven pieces can remain raw while the surrounding casserole is hot.",
    "Cover to retain moisture and continue baking until every thick piece reaches 165°F.", True,
))
_add_family_method("ground_meat", casserole_method(
    ("fresh raw", "frozen raw"), 4, 30, 6,
    "Thaw {name} when frozen and break it into small, evenly distributed pieces.",
    "Bake {name} in the assembled dish, stirring once when practical to eliminate large raw clumps.",
    "Evenly cooked crumbles distributed through the casserole.",
    "No pink ground meat remains; poultry reaches 165°F and beef reaches 160°F.",
    "Dense clumps may remain undercooked in the center.",
    "Break up clumps and continue baking to the temperature required for the named meat.", True,
))
_add_family_method("sausage", casserole_method(
    ("fresh raw", "frozen raw"), 3, 30, 4,
    "Thaw {name} when frozen. Leave links whole or cut them into equal thick pieces for the casserole.",
    "Bake {name} in the assembled dish until safely cooked through.",
    "Juicy sausage that seasons the surrounding casserole.",
    "Poultry sausage reaches 165°F; pork or beef sausage reaches 160°F.",
    "Thick links can remain raw in the center.",
    "Cover and continue baking until the center reaches the required temperature.", True,
))
_add_family_method("fish_fillet", casserole_method(
    ("fresh raw", "frozen raw"), 3, 20, 3,
    "Thaw {name} when frozen, pat dry, and arrange it in an even layer.",
    "Bake {name} with the assembled casserole only until the fish is opaque and tender.",
    "Moist flakes in a cohesive baked dish.",
    "The thickest portion reaches 145°F and flakes easily.",
    "A long casserole bake dries delicate fish.",
    "Add fish later in the bake when other components need more time.", True,
))
_add_family_method("pork_cut", casserole_method(
    ("fresh raw", "frozen raw"), 4, 25, 4,
    "Thaw {name} when frozen, pat dry, and make the portions even.",
    "Bake {name} in the assembled dish until safely cooked without prolonged dry heat.",
    "Tender pork surrounded by the finished casserole.",
    "The center reaches 145°F and rests for at least 3 minutes.",
    "Thin pork dries before dense vegetables soften.",
    "Cut vegetables smaller, cover the dish, and stop cooking the pork at temperature.", True,
))
_add_family_method("plant_protein", casserole_method(
    ("fresh", "refrigerated", "frozen"), 3, 25, 3,
    "Drain {name}, pat it dry, and cut it into even bite-size pieces.",
    "Bake {name} in the assembled dish until hot and lightly firm at the edges.",
    "Seasoned pieces integrated throughout the casserole.",
    "The center is steaming hot and the exterior has taken on the sauce.",
    "Excess moisture can make the casserole watery.",
    "Drain excess liquid and finish uncovered briefly.",
))

for _family_code in (
    "aromatic_slow", "aromatic_fast", "sturdy_root", "tender_watery",
    "tomato", "mushroom", "quick_green", "cruciferous", "pepper",
    "winter_squash", "cabbage", "okra", "sweet_kernel", "leafy_sturdy",
):
    _add_family_method(_family_code, casserole_method(
        ("fresh", "fresh raw", "frozen", "canned"), 4, 25, 4,
        "Prepare {name} in even bite-size pieces; drain or thaw it when its form requires it.",
        "Bake {name} in the assembled dish until tender and hot while it still has an intentional texture.",
        "Tender vegetables integrated with the sauce and other components.",
        "The thickest pieces are tender and the dish is bubbling at the edges.",
        "Uneven pieces cook at different rates and excess moisture can make the casserole watery.",
        "Cut firm pieces smaller, uncover to evaporate moisture, and continue until tender.",
    ))


def soup_protein_method(
    family_code, forms, prep, cook, handling, instruction, outcome, cue,
    failure, recovery, verification_required=False,
):
    _add_family_method(family_code, method(
        "simmer", forms, "gentle soup simmer", "seasoned one-pot soup",
        prep, cook, min(5, prep + 2), .25, "burner", "middle", handling,
        instruction, outcome, cue, failure, recovery, "good",
        verification_required=verification_required,
    ))


soup_protein_method(
    "poultry_piece", ("fresh raw", "frozen raw"), 4, 30,
    "Thaw {name} when frozen; do not rinse it. Cut it into even soup-size pieces when appropriate.",
    "Gently simmer {name} in the soup until safely cooked and tender.",
    "Juicy fully cooked chicken in the broth.", "The thickest piece reaches 165°F.",
    "A hard boil makes poultry tough while thick pieces may remain raw.",
    "Lower to a simmer and continue until every thick piece reaches 165°F.", True,
)
soup_protein_method(
    "ground_meat", ("fresh raw", "frozen raw"), 3, 20,
    "Thaw {name} when frozen and break it into small crumbles.",
    "Brown {name} in the soup pot, then simmer it in the broth until safely cooked.",
    "Small savory crumbles throughout the soup.",
    "No pink remains; poultry reaches 165°F and beef reaches 160°F.",
    "Large clumps can remain raw inside.", "Break up clumps and continue simmering to temperature.", True,
)
soup_protein_method(
    "sausage", ("fresh raw", "frozen raw"), 3, 20,
    "Thaw {name} when frozen and leave links whole for an accurate center-temperature check.",
    "Gently simmer {name} in the soup until safely cooked, then slice if desired.",
    "Juicy sausage that seasons the broth.",
    "Poultry sausage reaches 165°F; pork or beef sausage reaches 160°F.",
    "A hard boil can split casings while the center remains undercooked.",
    "Lower the heat and continue gently to the required temperature.", True,
)
for _code in ("ready_protein", "plant_protein"):
    soup_protein_method(
        _code, ("cooked", "canned", "ready to eat", "refrigerated", "fresh"), 2, 8,
        "Drain, portion, or cut {name} into soup-size pieces as needed.",
        "Add {name} near the end and simmer gently only until steaming hot.",
        "Hot, moist pieces that retain their intended texture.", "Steaming hot throughout.",
        "Prolonged simmering can make a ready ingredient dry or mushy.",
        "Add it later or remove the pot from heat once hot.",
    )
soup_protein_method(
    "fish_fillet", ("fresh raw", "frozen raw"), 3, 8,
    "Thaw {name} when frozen, pat dry, and cut it into large even pieces.",
    "Slip {name} into the soup near the finish and poach gently without stirring hard.",
    "Moist tender flakes in the broth.", "The thickest piece reaches 145°F and flakes easily.",
    "A long or hard simmer breaks fish apart and dries it.",
    "Lower the heat and remove the pot promptly once the fish is done.", True,
)
soup_protein_method(
    "shellfish_quick", ("fresh raw", "frozen raw"), 3, 5,
    "Thaw {name} when frozen, peel or clean it as needed, and pat it dry.",
    "Add {name} during the final minutes and poach gently until opaque.",
    "Juicy opaque shellfish.", "Opaque and pearly throughout; 145°F when checked.",
    "Shellfish becomes rubbery with prolonged simmering.", "Remove from heat immediately when opaque.", True,
)


_add_family_method("ground_meat", grill_method(
    ("fresh raw", "frozen raw"), 5, 10, 7, "middle",
    "Thaw {name}, keep it cold, and shape even patties without compacting them heavily.",
    "Grill {name} patties over direct heat, turning once after they release cleanly; do not press out the juices.",
    "Brown grill marks and a moist safely cooked center.",
    "The center reaches the safe temperature for the specific ground meat.",
    "Thick or tightly packed patties can char outside while remaining raw inside.",
    "Move to a cooler zone and continue to temperature; serve dry patties with a moist topping.",
    verification_required=True, rest_minutes=3,
    rest_template="Rest {name} patties briefly before serving.",
))
_add_family_method("poultry_piece", grill_method(
    ("fresh raw", "frozen raw"), 5, 16, 9, "middle",
    "Thaw {name}, do not rinse it, pat dry, make thickness even, and season.",
    "Grill {name} over medium direct heat with the lid closed as appropriate, turning after it releases; move to indirect heat if the exterior browns too quickly.",
    "Brown grill marks and juicy safely cooked poultry.", "The thickest edible portion reaches 165°F.",
    "Flare-ups burn the exterior and uneven pieces cook at different rates.",
    "Move to indirect heat and continue to 165°F; serve dry pieces with sauce.",
    verification_required=True, rest_minutes=5,
    rest_template="Rest {name} for 5 minutes before slicing or serving.",
))
_add_family_method("fish_fillet", grill_method(
    ("fresh raw", "frozen raw"), 4, 8, 6, "late",
    "Thaw {name}, pat dry, remove obvious bones, oil the fish and clean grates lightly, and season.",
    "Grill {name} over medium-high heat without moving it until it releases, then turn carefully or finish skin-side down with the lid closed.",
    "Moist flakes, intact shape, and light grill marks.", "The thickest portion reaches 145°F and flakes easily.",
    "Delicate fish sticks to dirty grates and dries rapidly when overcooked.",
    "Use a grill basket or foil for fragile fillets and remove promptly at temperature.",
    verification_required=True,
))
_add_family_method("shellfish_quick", grill_method(
    ("fresh raw", "frozen raw"), 5, 5, 5, "late",
    "Thaw, clean, drain, and dry {name}; thread small pieces on skewers or use a grill basket.",
    "Grill {name} over direct heat, turning once, and remove immediately when opaque.",
    "Juicy opaque shellfish with light charring.", "Opaque and pearly throughout; 145°F when measurable.",
    "Small shellfish fall through grates and become rubbery within minutes.",
    "Use skewers or a basket and remove promptly; severe overcooking cannot be reversed.",
    verification_required=True,
))
_add_family_method("sausage", grill_method(
    ("fresh raw", "frozen raw", "refrigerated"), 3, 12, 7, "middle",
    "Thaw {name}; keep links intact and lightly oil clean grates.",
    "Grill {name} over medium heat, turning to brown all sides; use a cooler zone to finish the center without splitting the casing.",
    "Brown casing and a moist safely cooked center.", "160°F for pork/beef sausage or 165°F for poultry sausage.",
    "High direct heat splits or burns the casing before the center is safe.",
    "Move to indirect heat and continue to temperature.", verification_required=True,
))
_add_family_method("plant_protein", grill_method(
    ("fresh", "refrigerated", "fresh raw"), 6, 8, 7, "middle",
    "Drain and press {name}, cut thick sturdy slabs or use skewers, then oil and season.",
    "Grill {name} over medium-high heat until it releases and has marks on both sides; brush on sugary sauce only near the finish.",
    "Brown grill marks and a seasoned tender center.", "Several surfaces are browned and the center is hot.",
    "Wet pieces stick and steam; sugary marinades burn over direct heat.",
    "Dry the surface, move to a clean grate area, and add sauce late.", "fair",
))
_add_family_method("tender_steak", grill_method(
    ("fresh raw", "frozen raw", "refrigerated"), 4, 10, 7, "middle",
    "Thaw {name}, pat dry, and season both sides.",
    "Grill {name} over high direct heat until it releases and is well marked; turn once, finish to the chosen temperature, and rest.",
    "Deep grill marks and the requested interior doneness.",
    "For the verified safety endpoint, the center reaches 145°F followed by at least a 3-minute rest.",
    "Cooking only by time overcooks thin steaks and undercooks thick ones.",
    "Use a cooler grill zone when the exterior browns before the center is ready.",
    verification_required=True, rest_minutes=5,
    rest_template="Rest {name} for at least 5 minutes before slicing across the grain.",
))
_add_family_method("pork_cut", grill_method(
    ("fresh raw", "frozen raw", "refrigerated"), 4, 12, 7, "middle",
    "Thaw {name}, pat dry, make portions even, and season.",
    "Grill {name} over medium-high direct heat, turning after it releases; finish over a cooler zone when needed.",
    "Brown grill marks and a juicy center.", "The thickest portion reaches 145°F, followed by at least a 3-minute rest.",
    "Lean pork dries when held over high heat after reaching temperature.",
    "Move to indirect heat to finish gently and serve overdone pork with sauce.",
    verification_required=True, rest_minutes=3,
    rest_template="Rest {name} for at least 3 minutes before serving.",
))

for _family_code in (
    "mushroom", "quick_green", "cruciferous", "pepper", "winter_squash",
    "cabbage", "okra", "tender_watery", "sturdy_root", "bread_wrap",
):
    _add_family_method(_family_code, grill_method(
        ("fresh", "fresh raw", "frozen"), 5, 10, 6, "middle",
        "Prepare {name} in pieces large enough for the grates, or use skewers or a grill basket; dry, oil lightly, and season.",
        "Grill {name} over medium to medium-high heat, turning after clear marks form, until its stated doneness cue is reached.",
        "Defined pieces with browned grill marks and an appropriately tender center.",
        "The thickest pieces are tender at the center while still holding their intended shape.",
        "Small pieces fall through grates; excess oil causes flare-ups; sugary finishes burn.",
        "Use a basket or skewers, move to a cooler zone, and add sweet sauce only near the finish.",
        "fair",
    ))

_add_family_method("tomato", grill_method(
    ("fresh", "fresh raw"), 4, 6, 5, "late",
    "Cut {name} into sturdy halves or thick pieces, remove only loose seeds, dry the cut surfaces, and oil lightly.",
    "Grill {name} cut-side down until marked, turn carefully, and stop while the pieces still hold their shape.",
    "Smoky warm pieces that remain recognizable.", "Surfaces are marked and softened while the pieces remain intact.",
    "Thin pieces collapse through the grates and prolonged heat turns them into sauce.",
    "Use a grill basket and remove promptly; use collapsed pieces deliberately as a smoky sauce.",
))

# Handheld meals still use trained component methods: raw proteins cook in a
# skillet, ready proteins reheat, and produce that belongs fresh in a sandwich
# or wrap publishes a no-cook assembly activity.
for _family_code in ("tomato", "leafy_tender", "pepper"):
    _add_family_method(_family_code, method(
        "assemble", ("fresh", "fresh raw", "refrigerated"), "no-cook counter",
        "fresh handheld filling", 3, 0, 3, .8, "counter", "finish",
        "Wash and dry {name}; trim it and cut it into practical handheld pieces.",
        "Keep {name} fresh and add it during assembly so it retains its intended texture.",
        "Fresh, tidy pieces that fit the bread or wrap.",
        "The pieces are dry enough not to soak the wrapper and small enough for an even bite.",
        "Wet or oversized pieces make a handheld difficult to eat.",
        "Drain or blot excess moisture and cut the pieces smaller.", "poor",
    ))

FAMILY_LIBRARY.update({
    "citrus_finish": BehaviorFamily(
        "citrus_finish", "Citrus finishing fruit", "vegetable",
        "Acidic fruit normally zested, juiced, or served fresh rather than generically cooked as a vegetable.",
        ("acidic", "aromatic-zest", "no-cook-default"),
        (method(
            "assemble", ("fresh", "refrigerated"), "no-cook counter",
            "bright acidic finish", 3, 0, 3, 1, "counter", "finish",
            "Wash {name}; zest before cutting when zest is wanted, then cut and remove visible seeds.",
            "Add {name} juice or wedges at the finish so the aroma stays bright; cook it only for a deliberate baked or preserved preparation.",
            "Fresh citrus aroma and balanced acidity.", "Juice and zest are added to taste without overwhelming the meal.",
            "Long cooking dulls fresh aroma and pith can add bitterness.",
            "Add fresh zest or juice off heat; dilute excess acidity with the rest of the dish.", "poor",
        ),), ("finish-only-default",),
    ),
    "quinoa": BehaviorFamily(
        "quinoa", "Quinoa", "foundation",
        "A small seed cooked with measured liquid, then rested and fluffed.",
        ("dry-seed", "covered-simmer"),
        (method(
            "simmer", ("dry", "shelf stable"), "covered gentle simmer",
            "absorbed-grain pot", 3, 17, 3, .15, "burner", "early",
            "Rinse {name} thoroughly unless the package says it is pre-rinsed; measure it and its liquid.",
            "Simmer {name} covered until the liquid is absorbed, remove from heat, rest covered, and fluff.",
            "Tender separate grains with visible spirals.", "Liquid is absorbed and the grains are tender with their germ rings visible.",
            "Skipping the rinse can taste bitter; excess liquid makes it soggy.",
            "Drain excess liquid if necessary and rest uncovered briefly; add hot liquid if the center is hard.", "good",
        ), READY_REHEAT), ("start-first",),
    ),
    "corn_porridge": BehaviorFamily(
        "corn_porridge", "Cornmeal porridge", "foundation",
        "Grits or polenta gradually hydrated while stirring to prevent lumps and scorching.",
        ("dry-meal", "thickening", "stirring"),
        (method(
            "simmer", ("dry", "shelf stable"), "gentle simmer in a heavy pot",
            "thick creamy starch environment", 3, 25, 10, .4, "burner", "early",
            "Measure {name} and its liquid; choose a heavy saucepan and a whisk.",
            "Whisk {name} gradually into simmering liquid, reduce the heat, and cook gently while stirring often until creamy and fully tender.",
            "Creamy spoonable porridge without gritty raw meal.", "The grains taste tender, the mixture is cohesive, and no raw grit remains.",
            "Adding it too quickly forms lumps; high heat scorches the thick base.",
            "Whisk firmly to break small lumps, add hot liquid to loosen, and lower the heat.", "fair",
        ), READY_REHEAT), ("stir-often",),
    ),
    "soft_potato": BehaviorFamily(
        "soft_potato", "Soft prepared potato", "foundation",
        "A cooked potato foundation kept creamy through gentle reheating and added moisture.",
        ("cooked", "soft", "reheat"),
        (method(
            "reheat", ("cooked", "refrigerated", "ready to eat"), "gentle moist heat",
            "soft creamy foundation", 2, 6, 4, .45, "burner", "late",
            "Portion {name} and break up cold compacted areas.",
            "Reheat {name} gently, stirring in a small amount of milk, broth, or butter as needed until smooth and steaming hot.",
            "Hot, smooth, spoonable potatoes.", "Steaming hot throughout with no cold center and the intended consistency.",
            "High heat scorches the bottom while cold dense areas remain.",
            "Lower the heat and add liquid a little at a time while stirring.", "fair",
        ),), ("gentle-reheat",),
    ),
    "crisp_potato": BehaviorFamily(
        "crisp_potato", "Crisp prepared potato", "foundation",
        "A potato foundation whose value comes from a dry crisp exterior.",
        ("cooked-or-parcooked", "crisp", "dry-heat"),
        (method(
            "saute", ("fresh", "frozen", "cooked", "refrigerated"), "hot uncrowded dry heat",
            "crisp browned foundation", 3, 12, 7, .55, "burner", "middle",
            "Separate {name}, remove surface moisture, and keep pieces or shreds evenly sized.",
            "Cook {name} in a thin layer of fat without crowding, leaving it undisturbed long enough to brown before turning.",
            "Crisp brown surfaces and a hot tender center.", "Broad surfaces are browned and crisp and the center is steaming hot.",
            "Crowding or frequent stirring causes pale, soft potatoes.",
            "Spread into a thinner layer, raise the heat moderately, and allow uninterrupted contact with the pan.", "poor",
        ),), ("protect-dry-crisping",),
    ),
    "baked_potato": BehaviorFamily(
        "baked_potato", "Whole baked potato", "foundation",
        "A whole potato baked until fluffy or gently reheated when already cooked.",
        ("whole", "dense", "oven"),
        (method(
            "roast", ("fresh", "fresh raw"), "hot oven",
            "dry roasting environment", 4, 50, 4, .08, "oven", "early",
            "Scrub and dry {name}; pierce the skin in several places and season the exterior if desired.",
            "Bake {name} directly on a rack or sheet until the center is completely tender; split promptly to release steam.",
            "Crisp skin and a fluffy tender center.", "A thin knife or skewer slides through the center without resistance.",
            "An underbaked center stays hard and waxy; wrapping traps steam and softens the skin.",
            "Continue baking until fully tender; crisp a softened skin briefly in a hot oven.", "excellent",
        ), READY_REHEAT), ("long-lead",),
    ),
})

FAMILY_LIBRARY.update({
    "bacon": BehaviorFamily(
        "bacon", "Bacon", "protein",
        "A cured fatty strip or piece that renders its own cooking fat and moves quickly from crisp to burned.",
        ("cured", "fat-rendering", "thin"),
        (method(
            "skillet", ("fresh raw", "frozen raw", "refrigerated"), "cool-to-moderate skillet",
            "rendered fat and crisp bacon", 2, 9, 6, .65, "burner", "early",
            "Separate {name} and cut it first only when the meal needs small pieces.",
            "Start {name} in the skillet before it is fully hot and cook, turning as needed, until the fat renders and the desired crispness is reached.",
            "Evenly rendered bacon at the chosen tenderness or crispness.", "The bacon is safely cooked, its fat is rendered, and the meat is deeply colored without blackened edges.",
            "High starting heat burns lean areas before the fat renders.",
            "Lower the heat and turn more often; badly burned bacon cannot be recovered.", "fair",
        ), READY_REHEAT), ("renders-cooking-fat", "early-entry"),
    ),
    "whole_poultry": BehaviorFamily(
        "whole_poultry", "Whole poultry or large poultry roast", "protein",
        "A large uneven poultry piece requiring oven roasting and temperature checks in more than one location.",
        ("raw", "large", "oven"),
        (method(
            "roast", ("fresh raw", "frozen raw", "refrigerated"), "preheated oven",
            "roasting-pan juices", 12, 75, 15, .15, "oven", "early",
            "Thaw {name} completely, remove packaging or giblets, do not rinse, pat dry, and season.",
            "Roast {name} until browned and safely cooked, checking the thickest breast and innermost thigh without touching bone; rest before carving.",
            "Brown skin and juicy safely cooked meat.", "Every checked location reaches at least 165°F, followed by a rest before carving.",
            "Partial thawing causes dangerously uneven cooking; overcooking the breast while waiting on the thigh dries it out.",
            "Shield browned areas with foil and continue roasting until every location is safe; serve dry portions with pan juices.", "good",
            verification_required=True, rest_minutes=15,
            rest_template="Rest {name} for 15 minutes before carving.",
        ), READY_REHEAT), ("oven-required", "rest-required"),
    ),
    "pork_roast": BehaviorFamily(
        "pork_roast", "Pork loin roast", "protein",
        "A lean intact pork roast that is oven-cooked by temperature and rested before slicing.",
        ("raw", "large", "lean", "oven"),
        (method(
            "roast", ("fresh raw", "frozen raw", "refrigerated"), "preheated oven",
            "roasting-pan juices", 8, 45, 10, .15, "oven", "early",
            "Thaw {name}, pat dry, tie or shape it evenly when needed, and season the exterior.",
            "Roast {name} until browned and the center reaches its safe endpoint, then rest before slicing across the grain.",
            "Even slices with a browned exterior and juicy center.", "The center reaches 145°F, followed by at least a 3-minute rest.",
            "Cooking only by time can leave a thick roast raw or a small one dry.",
            "Use temperature as the endpoint; serve an overdone roast thinly sliced with sauce.", "excellent",
            verification_required=True, rest_minutes=10,
            rest_template="Rest {name} for at least 10 minutes before slicing.",
        ), READY_REHEAT), ("oven-required", "rest-required"),
    ),
})


_add_family_method("whole_poultry", grill_method(
    ("fresh raw", "frozen raw", "refrigerated"), 12, 80, 18, "early",
    "Thaw {name} completely, remove packaging or giblets, do not rinse, pat dry, and season.",
    "Grill {name} with indirect heat and the lid closed, rotating as needed for even browning; keep it away from direct flare-ups.",
    "Brown skin and juicy safely cooked meat.",
    "The thickest breast and innermost thigh both reach at least 165°F without touching bone.",
    "Direct flame burns the skin before the interior is safe.",
    "Move fully to indirect heat, shield dark areas with foil, and continue until every location is safe.",
    "good", verification_required=True, rest_minutes=15,
    rest_template="Rest {name} for 15 minutes before carving.",
))
_add_family_method("pork_roast", grill_method(
    ("fresh raw", "frozen raw", "refrigerated"), 8, 50, 12, "early",
    "Thaw {name}, pat dry, shape it evenly, and season.",
    "Grill {name} over indirect heat with the lid closed, turning occasionally for even browning.",
    "Brown exterior and a juicy evenly cooked center.",
    "The center reaches 145°F, followed by at least a 3-minute rest.",
    "Direct high heat dries and burns the exterior before a large center is ready.",
    "Move to indirect heat and use temperature as the endpoint.",
    "excellent", verification_required=True, rest_minutes=10,
    rest_template="Rest {name} for at least 10 minutes before slicing.",
))

FAMILY_LIBRARY["corn"] = BehaviorFamily(
    "corn", "Corn", "vegetable",
    "A sweet kernel vegetable that can be briefly heated off the cob or grilled on the cob.",
    ("sweet", "kernel", "grillable-on-cob"),
    (method(
        "brief_heat", ("fresh", "frozen", "canned"), "brief moist heat",
        "sweet finishing component", 3, 5, 3, .4, "burner", "late",
        "Husk {name} when on the cob, or drain canned kernels and break up frozen clumps.",
        "Heat {name} only until tender and hot.", "Sweet plump kernels.",
        "Hot and tender without shriveling.", "Prolonged cooking dulls sweetness.",
        "Stop heating and finish with fat or a bright seasoning.", "fair",
    ), grill_method(
        ("fresh",), 5, 12, 7, "middle",
        "Remove the husk and silk from {name}, or pull the husk back and retie it when a steamed result is preferred; oil lightly.",
        "Grill {name} over medium-high heat, turning every few minutes, until hot and browned in spots.",
        "Juicy kernels with smoky browned spots.", "Kernels are tender, hot, and browned on several sides.",
        "Very high heat can blacken kernels before the cob heats through.",
        "Move to a cooler zone and continue turning.", "fair",
    )), ("grill-whole", "late-entry"),
)

_add_family_method("corn", casserole_method(
    ("fresh", "frozen", "canned"), 3, 18, 3,
    "Drain canned {name}, break up frozen clumps, or cut fresh kernels from the cob.",
    "Bake {name} in the casserole until the kernels are hot and tender without shriveling.",
    "Sweet, plump kernels distributed through the casserole.",
    "The kernels are hot and tender while retaining their shape.",
    "A long uncovered bake can dry and toughen the kernels.",
    "Cover the dish or add the kernels later when the other ingredients need a long bake.",
))


def support_method(
    name, environment, creates, prep, cook, equipment, stage, handling,
    instruction, outcome, cue, failure, recovery, holdability="good",
):
    """Describe a supporting ingredient without pretending it is a meal component.

    These methods let sauces, seasonings, fats, dairy, and baking helpers carry
    their own handling and failure knowledge.  They are deliberately different
    from protein/produce/foundation methods: a bottle of vinegar is not assigned
    a generic eight-minute cooking step merely because it entered the pantry.
    """
    return method(
        name, (), environment, creates, prep, cook, min(prep + cook, 3), .45,
        equipment, stage, handling, instruction, outcome, cue, failure, recovery,
        holdability,
    )


FAMILY_LIBRARY.update({
    "dry_seasoning": BehaviorFamily(
        "dry_seasoning", "Dry seasoning", "ingredient",
        "A concentrated dry seasoning measured to taste and added at a stage that protects its aroma.",
        ("concentrated", "dry", "seasoning"),
        (support_method(
            "season", "mixing or brief heat", "seasoned cooking environment", 1, 1,
            "counter", "middle", "Measure {name}; begin with less when its strength is unfamiliar.",
            "Add {name} in a measured amount, bloom it briefly in fat when appropriate, and taste before adding more.",
            "Integrated seasoning without a raw dusty taste.", "Its aroma is present and the food tastes balanced.",
            "Too much concentrated seasoning can dominate the whole meal; dry spices scorch quickly.",
            "Dilute with more unseasoned food or liquid; replace badly burned spices.",
        ),), ("layers-flavor",),
    ),
    "salt_seasoning": BehaviorFamily(
        "salt_seasoning", "Salt seasoning", "ingredient",
        "A seasoning whose total must account for broth, cheese, cured food, and condiments already in the meal.",
        ("salty", "concentrated", "seasoning"),
        (support_method(
            "season", "layered seasoning", "salt-balanced meal", 1, 0, "counter", "finish",
            "Keep {name} available but do not measure the full amount before accounting for salty ingredients.",
            "Taste the assembled food first, then add {name} a small amount at a time only as needed.",
            "Seasoned food whose other flavors remain distinct.", "The meal tastes complete rather than distinctly salty.",
            "Salt cannot be removed once dissolved.", "Increase the unsalted bulk or liquid and rebalance acidity and fat.",
        ),), ("taste-before-adding",),
    ),
    "fresh_herb": BehaviorFamily(
        "fresh_herb", "Fresh herb", "ingredient",
        "A tender aromatic whose fresh character is strongest late in cooking or at service.",
        ("fresh", "aromatic", "delicate"),
        (support_method(
            "finish", "off heat", "fresh aromatic finish", 3, 0, "counter", "finish",
            "Rinse and dry {name}; remove tough stems and chop or tear it just before use.",
            "Fold in {name} near the end or scatter it over the finished meal.",
            "Bright fresh aroma and color.", "The herb smells fresh and remains visibly green.",
            "Long heat dulls its aroma and color.", "Add a fresh portion off heat.", "poor",
        ),), ("late-aromatic",),
    ),
    "cooking_fat": BehaviorFamily(
        "cooking_fat", "Cooking fat", "ingredient",
        "Fat chosen for heat level, browning, flavor, and flare-up risk.",
        ("fat", "heat-transfer", "concentrated"),
        (support_method(
            "incorporate", "controlled heat", "lubricated cooking surface", 1, 1, "burner", "early",
            "Measure {name}; use only enough to coat the cooking surface or ingredients lightly.",
            "Heat {name} only to the temperature needed for the next operation; reduce heat if it smokes.",
            "Even browning without greasiness.", "The surface is lightly coated and the fat is not smoking.",
            "Overheated fat smokes; excess fat makes food greasy and can cause grill flare-ups.",
            "Remove from heat, replace scorched fat, and drain excess before continuing.",
        ),), ("supports-browning", "grill-flare-risk"),
    ),
    "broth_liquid": BehaviorFamily(
        "broth_liquid", "Broth or stock", "ingredient",
        "A seasoned cooking liquid that supplies moisture, savory depth, and often significant salt.",
        ("liquid", "savory", "often-salty"),
        (support_method(
            "build_sauce", "gentle simmer", "moist savory environment", 1, 4, "burner", "middle",
            "Measure {name} and note whether it is salted.",
            "Add {name} to build the cooking liquid or loosen browned flavor; simmer only as long as the meal needs.",
            "Savory moisture at the intended concentration.", "The food is moist and the liquid tastes balanced.",
            "Reducing salted broth too far makes the meal overly salty.",
            "Dilute with water or unsalted liquid and delay any added salt.",
        ),), ("supplies-liquid", "taste-before-salt"),
    ),
    "cultured_creamy": BehaviorFamily(
        "cultured_creamy", "Cultured creamy dairy", "ingredient",
        "A tangy creamy ingredient normally used cool, off heat, or gently tempered.",
        ("creamy", "tangy", "heat-sensitive"),
        (support_method(
            "finish", "off heat or gentle heat", "creamy tangy finish", 1, 1, "counter", "finish",
            "Portion {name} and keep it cool until the meal is nearly finished.",
            "Serve {name} on top or alongside, or temper it with warm liquid before stirring it in off heat.",
            "Smooth creamy tang without curdling.", "It remains smooth and visibly creamy.",
            "Boiling can split or curdle cultured dairy.", "Remove from heat and whisk in a fresh spoonful gradually.", "poor",
        ),), ("cooling-contrast", "finish-off-heat"),
    ),
    "milk_cream": BehaviorFamily(
        "milk_cream", "Milk or cream", "ingredient",
        "A dairy liquid that adds richness but needs moderate heat to avoid scorching or separation.",
        ("liquid", "creamy", "heat-sensitive"),
        (support_method(
            "build_sauce", "gentle heat", "creamy sauce environment", 1, 4, "burner", "late",
            "Measure {name} and bring very cold dairy closer to room temperature when practical.",
            "Add {name} over moderate or low heat and stir until hot and integrated; do not boil aggressively.",
            "Smooth creamy liquid or sauce.", "Steaming and smooth, without scorching or separation.",
            "High heat scorches milk and can split a sauce.", "Lower the heat and whisk in a small amount of fresh dairy.",
        ),), ("adds-richness", "gentle-heat"),
    ),
    "melting_cheese": BehaviorFamily(
        "melting_cheese", "Melting cheese", "ingredient",
        "Cheese used for salty richness, melting, or a browned topping.",
        ("salty", "fatty", "protein-rich"),
        (support_method(
            "melt", "low heat or residual heat", "melted cheese finish", 2, 3, "burner", "finish",
            "Shred, crumble, or portion {name} so it melts evenly.",
            "Add {name} near the finish and melt it with gentle or residual heat.",
            "Evenly melted or intentionally softened cheese.", "Soft and integrated without releasing excess oil.",
            "Excess heat makes many cheeses oily, stringy, or grainy.", "Remove from direct heat and stir in more liquid if the sauce tightens.",
        ),), ("adds-salt", "adds-richness"),
    ),
    "acid_condiment": BehaviorFamily(
        "acid_condiment", "Culinary acid", "ingredient",
        "Vinegar or another concentrated acid used to balance richness and brighten flavor.",
        ("acidic", "liquid", "concentrated"),
        (support_method(
            "finish", "off heat or brief simmer", "bright balanced finish", 1, 0, "counter", "finish",
            "Measure a small amount of {name}; more can be added after tasting.",
            "Add {name} near the finish, stir, and taste before adding more.",
            "Brighter flavor without obvious harsh sourness.", "Richness is balanced and the acid does not dominate.",
            "Too much acid tastes harsh and can delay dry beans softening when added early.",
            "Dilute with more food or liquid and rebalance with fat or a small amount of sweetness.",
        ),), ("late-with-dry-legumes", "balances-richness"),
    ),
    "prepared_condiment": BehaviorFamily(
        "prepared_condiment", "Prepared condiment or sauce", "ingredient",
        "A ready sauce whose salt, sugar, acid, heat, and thickness must be considered before adding more seasoning.",
        ("ready-to-eat", "concentrated", "form-sensitive"),
        (support_method(
            "finish", "off heat or gentle heat", "seasoned sauce finish", 1, 2, "counter", "finish",
            "Taste {name} and check its salt, sweetness, heat, and thickness before measuring more seasoning.",
            "Stir in {name} near the finish, or serve it alongside when its fresh texture matters.",
            "A balanced recognizable sauce contribution.", "The sauce coats or accompanies the food without overwhelming it.",
            "Sugary sauces burn over high heat and concentrated condiments can oversalt a meal.",
            "Move off direct heat, dilute, and reserve additional sauce for the table.",
        ),), ("account-before-seasoning", "sweet-sauce-add-late-on-grill"),
    ),
    "tomato_product": BehaviorFamily(
        "tomato_product", "Prepared tomato product", "ingredient",
        "A form-sensitive tomato base: paste needs blooming and dilution; sauce and diced forms build a wet simmer.",
        ("acidic", "wet", "sauce-building"),
        (support_method(
            "build_sauce", "sauté then simmer", "tomato sauce environment", 1, 10, "burner", "middle",
            "Open and measure {name}; inspect an already-open container before use.",
            "Add {name} after dry browning is complete and simmer it with compatible ingredients until the raw canned edge softens.",
            "A cohesive savory tomato base.", "The sauce tastes integrated and has the intended thickness.",
            "Adding it too early stops dry browning; prolonged reduction can scorch or over-concentrate acid.",
            "Add liquid and lower the heat; restore brightness with a fresh finish.",
        ),), ("ends-dry-browning", "builds-wet-environment"),
    ),
    "thickener": BehaviorFamily(
        "thickener", "Starch thickener", "ingredient",
        "A dry starch that must be dispersed correctly before it thickens liquid.",
        ("dry", "starch", "thickening"),
        (support_method(
            "thicken", "simmering liquid", "thickened sauce environment", 2, 3, "burner", "late",
            "Measure {name}; make a cold slurry when required so it disperses without lumps.",
            "Whisk in {name} gradually and simmer only until the liquid reaches the intended body.",
            "A smooth sauce at the intended thickness.", "The liquid coats a spoon without raw starch flavor or lumps.",
            "Adding dry starch directly to hot liquid creates lumps; too much becomes gluey.",
            "Strain stubborn lumps or whisk in more liquid to loosen.",
        ),), ("requires-dispersion",),
    ),
    "dry_baking_helper": BehaviorFamily(
        "dry_baking_helper", "Dry baking helper", "ingredient",
        "Flour, leavener, or sugar whose function depends on a measured formula rather than improvisational stovetop cooking.",
        ("dry", "formula-sensitive", "baking"),
        (support_method(
            "incorporate", "measured mixing", "structured batter or dough", 2, 0, "counter", "early",
            "Measure {name} accurately using the recipe's specified unit and technique.",
            "Incorporate {name} only according to a trained batter, dough, coating, or thickening formula.",
            "The intended structure, sweetness, or lift.", "It is evenly dispersed in the measured mixture.",
            "Unmeasured substitution can prevent thickening, lift, or proper texture.",
            "Correct the formula before cooking; do not guess with additional leavener.",
        ),), ("requires-formula",),
    ),
    "sweetener": BehaviorFamily(
        "sweetener", "Culinary sweetener", "ingredient",
        "A concentrated sweet ingredient used for balance, browning, or a deliberate sweet profile.",
        ("sweet", "concentrated", "browning-prone"),
        (support_method(
            "finish", "low heat or off heat", "sweet-balanced finish", 1, 1, "counter", "finish",
            "Measure {name}; start with less when balancing a savory dish.",
            "Stir in {name} gradually and taste; keep it away from intense direct heat unless deliberate caramelization is trained.",
            "Balanced sweetness without a burnt edge.", "Sweetness supports rather than masks the other flavors.",
            "Sugar burns readily over direct heat and excess sweetness is difficult to remove.",
            "Dilute and rebalance with acid or salt; discard a scorched glaze.",
        ),), ("burns-over-direct-heat",),
    ),
    "creamy_soup_base": BehaviorFamily(
        "creamy_soup_base", "Condensed creamy soup base", "ingredient",
        "A thick seasoned canned base that supplies liquid binding, salt, and creaminess.",
        ("canned", "creamy", "salty", "thick"),
        (support_method(
            "build_sauce", "gentle simmer", "creamy bound environment", 1, 5, "burner", "middle",
            "Open and inspect {name}; measure any added liquid before combining.",
            "Stir {name} into the cooking liquid over moderate heat until smooth and steaming.",
            "A smooth cohesive creamy base.", "Hot and smooth at the intended consistency.",
            "It scorches when undiluted over high heat and may make added salt unnecessary.",
            "Lower the heat, add liquid gradually, and taste before salting.",
        ),), ("supplies-liquid", "taste-before-salt"),
    ),
    "prepared_legume": BehaviorFamily(
        "prepared_legume", "Prepared bean or legume", "foundation",
        "A fully cooked seasoned legume product that needs only safe gentle reheating.",
        ("cooked", "ready-to-eat", "starchy", "protein-contributing"),
        (method(
            "reheat", ("canned", "cooked", "ready to eat", "shelf stable"), "gentle moist heat",
            "warm thick foundation", 1, 5, 4, .45, "burner", "late",
            "Open {name}, inspect it, and portion at least half a can when practical.",
            "Heat {name} gently, stirring often enough to prevent sticking; do not recook it.",
            "Steaming hot beans at their intended consistency.", "Steaming throughout without a scorched bottom.",
            "Thick prepared beans scorch with high heat or prolonged holding.",
            "Lower the heat and loosen with a little water or broth.", "good",
        ),), ("can-stretch-protein", "gentle-reheat", "soup-friendly"),
    ),
    "ready_cured_meat": BehaviorFamily(
        "ready_cured_meat", "Ready cured meat", "protein",
        "A cured or fully cooked meat used as a main item or concentrated savory accent.",
        ("ready-to-eat", "salty", "fat-rendering"),
        (READY_REHEAT,), ("accent-capable", "taste-before-salt"),
    ),
})

soup_protein_method(
    "ready_cured_meat", ("cooked", "ready to eat", "refrigerated"), 2, 8,
    "Cut {name} into soup-size pieces and account for its salt before seasoning the broth.",
    "Add {name} near the end and simmer gently only until steaming hot.",
    "Hot savory pieces that retain their texture.", "Steaming hot throughout.",
    "A long simmer can make cured meat dry and oversalt the broth.",
    "Add it later, dilute the broth if needed, and taste before salting.",
)


def _set_portion(family_code, basis, amount, label, rounding="practical", stretchable=False):
    FAMILY_LIBRARY[family_code] = replace(
        FAMILY_LIBRARY[family_code], portion_basis=basis,
        portion_per_standard=amount, portion_label=label,
        portion_rounding=rounding, stretchable=stretchable,
    )


for _code in ("ground_meat", "tough_meat", "stew_cut", "pork_roast", "whole_poultry"):
    _set_portion(_code, "weight_oz", 4, "pound", "quarter_pound_up", True)
for _code in ("poultry_piece", "fish_fillet", "pork_cut", "tender_steak", "sausage"):
    _set_portion(_code, "pieces", 1, "piece", "whole_up", True)
_set_portion("shellfish_quick", "weight_oz", 4, "pound", "quarter_pound_up", True)
_set_portion("plant_protein", "weight_oz", 4, "pound", "quarter_pound_up", True)
_set_portion("ready_protein", "cans", .5, "can", "half_can_minimum", True)
_set_portion("egg", "pieces", 2, "egg", "whole_up")
_set_portion("bacon", "pieces", 2, "strip", "whole_up")
for _code in ("white_rice", "brown_rice", "quinoa"):
    _set_portion(_code, "dry_cups", .25, "cup", "quarter_cup_up", True)
_set_portion("pasta", "dry_cups", .25, "cup", "quarter_cup_up", True)
_set_portion("bread_wrap", "pieces", 2, "slice", "whole_up", True)
for _code in ("soft_potato", "corn_porridge"):
    _set_portion(_code, "prepared_cups", .5, "cup", "quarter_cup_up", True)
_set_portion("legume", "cans", .25, "can", "half_can_minimum", True)
_set_portion("prepared_legume", "cans", .25, "can", "half_can_minimum", True)
_set_portion("ready_cured_meat", "pieces", 1, "piece", "whole_up", True)
# Vegetable amounts are planning estimates, expressed as practical prepared
# volume so a cook knows whether "carrots" means one handful or a stockpot.
for _code in (
    "sturdy_root", "tender_watery", "tomato", "leafy_tender", "leafy_sturdy",
    "mushroom", "quick_green", "cruciferous", "winter_squash", "cabbage",
    "okra", "crisp_stir_fry", "sweet_kernel", "corn", "artichoke",
):
    _set_portion(_code, "prepared_cups", .5, "cup", "quarter_cup_up", True)
for _code in ("aromatic_slow", "pepper"):
    _set_portion(_code, "prepared_cups", .25, "cup", "quarter_cup_up", True)
_set_portion("aromatic_fast", "prepared_cups", .125, "cup", "quarter_cup_up", True)
_set_portion("fresh_herb", "prepared_cups", .0625, "cup", "tablespoon_up", True)
_set_portion("citrus_finish", "whole_count", .25, "whole fruit", "whole_up", True)


def _set_sensory(family_code, flavors=(), functions=(), texture="", color=""):
    FAMILY_LIBRARY[family_code] = replace(
        FAMILY_LIBRARY[family_code], flavor_domains=tuple(flavors),
        culinary_functions=tuple(functions), texture_contribution=texture,
        color_contribution=color,
    )


# Combination intelligence is family knowledge.  The selector can recognize
# an unusual but coherent meal from functions and contrasts without knowing an
# ingredient's name or consulting a list of conventional recipes.
for _code in (
    "ground_meat", "poultry_piece", "tender_steak", "pork_cut", "whole_poultry",
    "pork_roast", "fish_fillet", "shellfish_quick", "sausage", "bacon",
    "ready_protein", "ready_cured_meat", "plant_protein", "tough_meat", "stew_cut", "egg",
):
    _set_sensory(_code, ("savory", "umami"), ("protein-anchor", "browning-source"), "substantial")
for _code in ("white_rice", "brown_rice", "quinoa", "pasta", "bread_wrap", "soft_potato", "crisp_potato", "baked_potato", "corn_porridge"):
    _set_sensory(_code, ("neutral", "starchy"), ("foundation", "absorbs-sauce"), "substantial")
for _code in ("legume", "prepared_legume"):
    _set_sensory(_code, ("earthy", "savory"), ("foundation", "protein-stretcher", "thickens"), "creamy")
for _code in ("aromatic_slow", "aromatic_fast", "fresh_herb", "dry_seasoning"):
    _set_sensory(_code, ("aromatic",), ("flavor-builder",), "soft")
for _code in ("sturdy_root", "winter_squash", "corn", "sweet_kernel"):
    _set_sensory(_code, ("sweet", "earthy"), ("vegetable-body", "sweetness-balance"), "tender")
for _code in ("quick_green", "leafy_tender", "leafy_sturdy", "cruciferous", "cabbage", "okra"):
    _set_sensory(_code, ("green", "vegetal"), ("fresh-contrast", "vegetable-body"), "tender-crisp", "green")
for _code in ("tender_watery", "tomato", "mushroom", "pepper", "crisp_stir_fry", "artichoke", "cauliflower_rice"):
    _set_sensory(_code, ("vegetal",), ("vegetable-body", "moisture-balance"), "tender")
_set_sensory("tomato", ("acidic", "savory", "sweet"), ("brightness", "sauce-builder", "moisture-source"), "juicy", "red")
_set_sensory("mushroom", ("earthy", "umami"), ("savory-depth", "browning-source"), "meaty")
_set_sensory("pepper", ("sweet", "vegetal"), ("aromatic-body", "color-contrast"), "tender-crisp", "bright")
_set_sensory("raw_finish", ("fresh", "acidic"), ("crisp-contrast", "brightness"), "crisp")
_set_sensory("raw_fruit", ("sweet", "fresh"), ("fresh-contrast", "sweetness-balance"), "juicy", "bright")
_set_sensory("citrus_finish", ("acidic", "aromatic"), ("brightness", "balances-richness"), "juicy", "bright")
_set_sensory("broth_liquid", ("savory", "salty"), ("supplies-liquid", "savory-depth"), "liquid")
_set_sensory("milk_cream", ("creamy", "rich"), ("adds-richness", "sauce-builder"), "creamy", "pale")
_set_sensory("cultured_creamy", ("tangy", "creamy"), ("cooling-contrast", "balances-richness"), "creamy", "pale")
_set_sensory("melting_cheese", ("salty", "savory", "rich"), ("adds-richness", "savory-depth"), "melty")
_set_sensory("acid_condiment", ("acidic",), ("brightness", "balances-richness"), "liquid")
_set_sensory("prepared_condiment", ("seasoned",), ("flavor-builder", "sauce-builder"), "saucy")
_set_sensory("tomato_product", ("acidic", "savory", "sweet"), ("sauce-builder", "supplies-liquid"), "saucy", "red")
_set_sensory("cooking_fat", ("rich",), ("supports-browning", "adds-richness"), "silky")
_set_sensory("sweetener", ("sweet",), ("sweetness-balance", "browning-source"), "")
_set_sensory("salt_seasoning", ("salty",), ("flavor-builder",), "")
_set_sensory("thickener", ("neutral",), ("thickens",), "")
_set_sensory("creamy_soup_base", ("creamy", "savory", "salty"), ("sauce-builder", "supplies-liquid", "thickens"), "creamy", "pale")
_set_sensory("dry_baking_helper", ("neutral",), ("formula-structure",), "")


ASSIGNMENTS = {
    "ground_meat": {"ground beef", "ground chicken", "ground turkey"},
    "tough_meat": {"chuck roast", "beef brisket", "pork shoulder"},
    "stew_cut": {"beef stew meat"},
    "poultry_piece": {"chicken breast", "chicken thighs", "chicken drumsticks", "chicken wings"},
    "fish_fillet": {"cod", "tilapia", "salmon"},
    "shellfish_quick": {"shrimp"},
    "sausage": {"turkey sausage", "breakfast sausage", "italian sausage", "kielbasa"},
    "plant_protein": {"tofu", "tempeh"},
    "aromatic_slow": {"onions", "leeks", "shallots", "fennel", "celery"},
    "aromatic_fast": {"garlic", "scallions"},
    "sturdy_root": {"carrots", "parsnips", "turnips", "rutabagas", "beets", "celery root", "potatoes", "sweet potatoes"},
    "tender_watery": {"zucchini", "yellow squash", "eggplant"},
    "tomato": {"tomatoes", "cherry tomatoes", "tomatillos"},
    "leafy_tender": {"spinach"},
    "leafy_sturdy": {"kale", "collard greens", "mustard greens", "swiss chard", "bok choy"},
    "raw_finish": {"cucumbers", "radishes", "lettuce", "romaine lettuce", "iceberg lettuce", "pickles", "sauerkraut", "green olives", "black olives"},
    "white_rice": {"white rice", "basmati rice", "jasmine rice"},
    "brown_rice": {"brown rice", "wild rice"},
    "cauliflower_rice": {"cauliflower rice"},
    "pasta": {"egg noodles", "pasta", "spaghetti", "macaroni", "rotini"},
    "legume": {"black beans", "white beans", "pinto beans", "great northern beans", "navy beans", "chickpeas", "lentils"},
    "bread_wrap": {"bread", "flour tortillas", "corn tortillas", "biscuits", "cornbread"},
    "raw_fruit": {"apples", "avocado", "bananas", "blackberries", "blueberries", "coconut", "cranberries", "grapes", "kiwi", "mango", "oranges", "papaya", "peaches", "pears", "pineapple", "raisins", "raspberries", "strawberries"},
}

ASSIGNMENTS.update({
    "tender_steak": {"flank steak", "ribeye steak", "sirloin steak"},
    "pork_cut": {"pork chops"},
    "pork_roast": {"pork loin"},
    "whole_poultry": {"whole chicken", "turkey breast"},
    "bacon": {"bacon"},
    "ready_protein": {"canned chicken", "canned tuna", "ham", "rotisserie chicken"},
    "egg": {"eggs"},
    "mushroom": {"mushrooms"},
    "quick_green": {"asparagus", "green beans", "snap peas", "snow peas"},
    "cruciferous": {"broccoli", "brussels sprouts", "cauliflower"},
    "pepper": {"green bell pepper", "red bell pepper", "yellow bell pepper", "orange bell pepper", "jalapenos", "poblanos", "serranos"},
    "winter_squash": {"acorn squash", "butternut squash", "pumpkin"},
    "cabbage": {"cabbage", "napa cabbage"},
    "okra": {"okra"},
    "crisp_stir_fry": {"bamboo shoots", "bean sprouts", "water chestnuts"},
    "sweet_kernel": {"peas"},
    "corn": {"corn"},
    "artichoke": {"artichokes"},
    "tough_meat": ASSIGNMENTS["tough_meat"] | {"corned beef"},
    "citrus_finish": {"lemons", "limes"},
    "quinoa": {"quinoa"},
    "corn_porridge": {"grits", "polenta"},
    "soft_potato": {"mashed potatoes"},
    "crisp_potato": {"french fries", "hash browns", "roasted potatoes"},
    "baked_potato": {"baked potatoes"},
    "legume": ASSIGNMENTS["legume"] | {
        "black-eyed peas", "butter beans", "cannellini beans", "cranberry beans",
        "green lentils", "kidney beans", "lima beans", "mayocoba beans",
        "red lentils", "split peas", "yellow lentils",
    },
    "prepared_legume": {"baked beans", "refried beans"},
    "bread_wrap": ASSIGNMENTS["bread_wrap"] | {"tortillas"},
    "ready_cured_meat": {"hot dogs", "pepperoni"},
    "aromatic_fast": ASSIGNMENTS["aromatic_fast"] | {"ginger"},
    "dry_seasoning": {
        "basil", "bay leaves", "black pepper", "cayenne pepper", "celery seed",
        "chili powder", "cinnamon", "cloves", "coriander", "cumin", "dill",
        "garlic powder", "italian seasoning", "mustard powder", "nutmeg",
        "onion powder", "oregano", "paprika", "parsley", "red pepper flakes",
        "rosemary", "sage", "smoked paprika", "thyme", "turmeric", "white pepper",
    },
    "fresh_herb": {"cilantro", "fresh basil", "fresh parsley", "fresh thyme"},
    "salt_seasoning": {"salt"},
    "cooking_fat": {"butter", "canola oil", "margarine", "olive oil", "sesame oil", "vegetable oil"},
    "broth_liquid": {"beef broth", "chicken broth", "vegetable broth"},
    "milk_cream": {"coconut milk", "half-and-half", "heavy cream", "milk"},
    "cultured_creamy": {"cottage cheese", "cream cheese", "greek yogurt", "ricotta cheese", "sour cream"},
    "melting_cheese": {
        "american cheese", "blue cheese", "cheddar cheese", "colby jack cheese",
        "feta cheese", "monterey jack cheese", "mozzarella cheese", "parmesan cheese",
        "pepper jack cheese", "swiss cheese",
    },
    "acid_condiment": {"apple cider vinegar", "balsamic vinegar", "white vinegar"},
    "prepared_condiment": {
        "bbq sauce", "hot sauce", "ketchup", "mayonnaise", "mustard", "soy sauce",
        "worcestershire sauce", "peanut butter", "vanilla extract",
    },
    "tomato_product": {"crushed tomatoes", "diced tomatoes", "rotel", "tomato paste", "tomato sauce"},
    "thickener": {"cornstarch"},
    "dry_baking_helper": {"all-purpose flour", "baking powder", "baking soda", "yeast"},
    "sweetener": {"brown sugar", "honey", "maple syrup", "molasses", "powdered sugar", "sugar"},
    "creamy_soup_base": {"cream of chicken soup", "cream of mushroom soup"},
})


def _db_family_codes(name, form_name, db_path) -> list[str]:
    if not db_path:
        return []
    try:
        with closing(sqlite3.connect(db_path)) as con:
            rows = con.execute(
                """SELECT f.family_code
                     FROM ingredient_behavior_memberships m
                     JOIN ingredients i USING (ingredient_id)
                     JOIN ko_behavior_families f USING (family_id)
                    WHERE lower(i.name)=lower(?) AND m.verified=1
                      AND (m.form_name='' OR lower(m.form_name)=lower(?))
                    ORDER BY m.is_primary DESC,m.priority,m.membership_id""",
                (name, form_name or ""),
            ).fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error:
        return []


def family_codes_for(name, role, form_name="", db_path=None) -> tuple[list[str], str]:
    codes = _db_family_codes(name, form_name, db_path)
    if codes:
        return codes, "ckb_membership"
    key = _key(name)
    inferred = [code for code, names in ASSIGNMENTS.items() if key in names]
    return inferred, "built_in_classification" if inferred else "unclassified"


def _db_family(family_code, db_path):
    if not db_path:
        return None
    try:
        with closing(sqlite3.connect(db_path)) as con:
            con.row_factory = sqlite3.Row
            family = con.execute(
                "SELECT * FROM ko_behavior_families WHERE family_code=? AND verified=1",
                (family_code,),
            ).fetchone()
            if not family:
                return None
            rows = con.execute(
                """SELECT * FROM ko_family_methods
                   WHERE family_id=? AND verified=1
                   ORDER BY family_method_id""",
                (family["family_id"],),
            ).fetchall()
        methods = tuple(MethodRule(
            _key(row["method_name"]), (_key(row["form_name"]),) if row["form_name"] else (),
            row["cooking_environment"], row["creates_environment"] or "",
            int(row["prep_minutes"] or 0), int(row["cook_minutes"] or 0),
            int(row["active_minutes"] or 0), float(row["attention_load"] or 0),
            row["equipment_name"] or "counter", row["add_stage"] or "middle",
            row["handling_template"] or "", row["instruction_template"] or "",
            row["desired_outcome"] or "", row["doneness_cue"] or "",
            row["failure_mode"] or "", row["recovery_hint"] or "",
            row["holdability"] or "fair",
            bool(row["verification_required"]) if "verification_required" in row.keys() else False,
            int(row["rest_minutes"] or 0) if "rest_minutes" in row.keys() else 0,
            (row["rest_template"] or "") if "rest_template" in row.keys() else "",
            int(row["frozen_thaw_minutes"] or 0) if "frozen_thaw_minutes" in row.keys() else 0,
            (row["frozen_thaw_equipment"] or "counter") if "frozen_thaw_equipment" in row.keys() else "counter",
            (row["frozen_thaw_template"] or "") if "frozen_thaw_template" in row.keys() else "",
        ) for row in rows)
        return BehaviorFamily(
            family["family_code"], family["family_name"], family["role"],
            family["description"],
            tuple(part.strip() for part in (family["physical_traits"] or "").split(",") if part.strip()),
            methods,
            (),
            family["portion_basis"] if "portion_basis" in family.keys() else "flexible",
            float(family["portion_per_standard"] or 1) if "portion_per_standard" in family.keys() else 1.0,
            family["portion_label"] if "portion_label" in family.keys() else "portion",
            family["portion_rounding"] if "portion_rounding" in family.keys() else "practical",
            bool(family["stretchable"]) if "stretchable" in family.keys() else False,
            tuple(part.strip() for part in (family["flavor_domains"] or "").split(",") if part.strip()) if "flavor_domains" in family.keys() else (),
            tuple(part.strip() for part in (family["culinary_functions"] or "").split(",") if part.strip()) if "culinary_functions" in family.keys() else (),
            family["texture_contribution"] or "" if "texture_contribution" in family.keys() else "",
            family["color_contribution"] or "" if "color_contribution" in family.keys() else "",
        )
    except sqlite3.Error:
        return None


def _apply_db_exceptions(rule, name, form_name, db_path):
    if not rule or not db_path:
        return rule
    try:
        with closing(sqlite3.connect(db_path)) as con:
            rows = con.execute(
                """SELECT e.field_name, e.override_value
                     FROM ko_ingredient_exceptions e
                     JOIN ingredients i USING (ingredient_id)
                    WHERE lower(i.name)=lower(?) AND e.verified=1
                      AND (e.form_name='' OR lower(e.form_name)=lower(?))
                      AND (e.method_name='' OR lower(e.method_name)=lower(?))
                    ORDER BY e.exception_id""",
                (name, form_name or "", rule.method),
            ).fetchall()
    except sqlite3.Error:
        return rule
    allowed = set(MethodRule.__dataclass_fields__)
    numeric_int = {"prep_minutes", "cook_minutes", "active_minutes"}
    updates = {}
    for field_name, value in rows:
        if field_name not in allowed or field_name in {"method", "forms"}:
            continue
        if field_name in numeric_int:
            value = int(value)
        elif field_name == "attention_load":
            value = float(value)
        updates[field_name] = value
    return replace(rule, **updates) if updates else rule


def ingredient_attributes(name, form_name="", db_path=None) -> dict[str, str]:
    """Return verified KO facts without teaching planner code ingredient names."""
    if not db_path:
        return {}
    try:
        with closing(sqlite3.connect(db_path)) as con:
            rows = con.execute(
                """SELECT a.attribute_name,a.attribute_value,a.form_name
                     FROM ko_ingredient_attributes a
                     JOIN ingredients i USING (ingredient_id)
                    WHERE lower(i.name)=lower(?) AND a.verified=1
                      AND (a.form_name='' OR lower(a.form_name)=lower(?))
                    ORDER BY CASE WHEN a.form_name='' THEN 0 ELSE 1 END""",
                (name, form_name or ""),
            ).fetchall()
        return {str(key): str(value) for key, value, _ in rows}
    except sqlite3.Error:
        return {}


def _resolve_behavior_uncached(name, role, form_name="", strategy="", db_path=None) -> ResolvedBehavior:
    codes, source = family_codes_for(name, role, form_name, db_path)
    # Meal role is contextual: beans may be today's protein and avocado may be
    # today's produce. Physical behavior follows the ingredient, not the slot.
    families = []
    for code in codes:
        family = FAMILY_LIBRARY.get(code)
        family = family or (_db_family(code, db_path) if source == "ckb_membership" else None)
        if family:
            families.append(family)
    primary = families[0] if families else None
    selected = None
    if primary:
        form_key = _key(form_name)
        strategy_key = _key(strategy)
        skillet_methods = {
            "saute", "bloom", "wilt", "saute_steam", "brief_heat",
            "warm", "reheat", "assemble",
        }
        if role == "foundation":
            skillet_methods.update({"simmer", "boil"})
        soup_methods = {
            "simmer", "braise", "saute", "saute_steam", "bloom", "wilt",
            "brief_heat", "reheat", "assemble",
        }
        casserole_methods = {"casserole", "roast", "bake", "reheat", "assemble"}
        if role == "foundation":
            # A casserole may legitimately require a separately hydrated
            # foundation before assembly. The planner must preserve that
            # prerequisite; accepting the method here is not permission to
            # place dry pasta or grain directly in the baking dish.
            casserole_methods.update({"boil", "simmer"})
        oven_braise_methods = {
            "oven_braise", "roast", "bake", "reheat", "assemble", "simmer",
            "saute", "saute_steam", "bloom", "wilt", "brief_heat",
        }
        braise_methods = {
            "braise", "simmer", "saute", "saute_steam", "bloom", "wilt",
            "brief_heat", "reheat", "assemble", "skillet",
        }
        grill_side_methods = {"simmer", "boil", "warm", "reheat", "saute", "assemble"}
        handheld_methods = {
            "skillet", "saute", "saute_steam", "brief_heat", "reheat",
            "warm", "assemble", "wilt",
        }
        method_candidates = list(primary.methods)
        if (
            strategy_key == "casserole"
            and role == "protein"
            and "large" in set(primary.physical_traits)
        ):
            # A whole bird or large roast can share an oven, but it cannot be
            # arranged as one component of a shallow integrated casserole.
            method_candidates = [
                item for item in method_candidates if item.method == "casserole"
            ]
        if (
            strategy_key == "handheld"
            and role == "foundation"
            and primary.code != "bread_wrap"
        ):
            # In the handheld structure the foundation is the wrapper. Beans,
            # rice, and potatoes can be fillings or sides, but cannot satisfy
            # the structural promise that the finished meal can be held.
            method_candidates = []
        if strategy_key == "handheld":
            method_candidates.sort(key=lambda item: item.method != "assemble")
        for candidate in method_candidates:
            form_matches = not form_key or not candidate.forms or any(value in form_key for value in candidate.forms)
            strategy_matches = not strategy_key or candidate.method == strategy_key or (
                strategy_key == "skillet" and candidate.method in skillet_methods
            ) or (
                strategy_key == "soup" and candidate.method in soup_methods
            ) or (
                strategy_key == "casserole" and candidate.method in casserole_methods
            ) or (
                strategy_key == "oven_braise" and candidate.method in oven_braise_methods
            ) or (
                strategy_key == "braise" and candidate.method in braise_methods
            ) or (
                strategy_key == "grill" and role == "foundation" and candidate.method in grill_side_methods
            ) or (
                strategy_key == "handheld" and candidate.method in handheld_methods
            )
            if form_matches and strategy_matches:
                selected = candidate
                break
        # Without a requested cooking environment, return the form's default.
        # With one, do not silently turn a braise into a quick skillet task.
        if selected is None and not strategy_key:
            for candidate in primary.methods:
                if any(value in form_key for value in candidate.forms):
                    selected = candidate
                    break
        if selected is None and not strategy_key and primary.methods:
            selected = primary.methods[0]
    reason = ""
    if primary and strategy and selected is None:
        reason = f"{primary.name} has no verified {strategy} method for {form_name or 'this form'}."
    selected = _apply_db_exceptions(selected, name, form_name, db_path)
    return ResolvedBehavior(
        name, role, form_name, primary, families[1:], selected, source, reason,
        ingredient_attributes(name, form_name, db_path),
    )


def _database_revision(db_path) -> tuple:
    """Return a cheap cache key that changes whenever the CKB changes.

    Render serves a read-mostly seed database, while the training tools and
    tests legitimately rewrite it.  Including the file revision gives the
    public planner a warm KO cache without making training changes stale.
    """
    if not db_path or str(db_path) == ":memory:":
        return ()
    revisions = []
    base = Path(db_path)
    for path in (base, Path(f"{base}-wal")):
        try:
            stat = path.stat()
            change_counter = b""
            if path == base and stat.st_size >= 28:
                with path.open("rb") as database_file:
                    database_file.seek(24)
                    change_counter = database_file.read(4)
            revisions.append((stat.st_mtime_ns, stat.st_size, change_counter))
        except OSError:
            revisions.append((0, 0, b""))
    return tuple(revisions)


@lru_cache(maxsize=8192)
def _resolve_behavior_cached(
    name, role, form_name, strategy, db_path, database_revision,
) -> ResolvedBehavior:
    return _resolve_behavior_uncached(
        name, role, form_name, strategy, db_path or None,
    )


def resolve_behavior(name, role, form_name="", strategy="", db_path=None) -> ResolvedBehavior:
    """Resolve KO behavior once per ingredient/form/method and CKB revision.

    Idea generation asks the same questions while comparing concepts,
    methods, schedules, and validation.  Previously every question reopened
    SQLite several times.  The resolved object contains immutable KO facts in
    normal planner use, so sharing it safely removes that repeated I/O.
    """
    path = str(db_path) if db_path else ""
    return _resolve_behavior_cached(
        str(name or ""), str(role or ""), str(form_name or ""),
        str(strategy or ""), path, _database_revision(path),
    )


def default_form_for(name, role="ingredient", db_path=None) -> str:
    """Return the conservative form assumed for a planned purchase.

    Empty forms previously matched every method, which could turn dry noodles
    into a ready-to-reheat casserole component. Defaults are family facts so
    the same rule protects every current and future member of that family.
    """
    behavior = resolve_behavior(name, role, db_path=db_path)
    family = behavior.primary_family
    if not family:
        return ""
    traits = set(family.physical_traits)
    if role == "protein":
        return "Cooked" if "ready-to-eat" in traits or "cooked" in traits else "Fresh Raw"
    if role == "vegetable":
        return "Fresh"
    if role == "foundation":
        if family.portion_basis == "cans":
            return "Canned"
        if traits & {"dry-starch", "dry-grain", "whole-grain"}:
            return "Dry"
        if "assembly" in traits or "ready-to-eat" in traits:
            return "Shelf-stable"
        if "vegetable" in traits:
            return "Fresh"
        return "Cooked"
    return "Shelf-stable"


def iter_family_seed_rows() -> Iterable[tuple]:
    for family in FAMILY_LIBRARY.values():
        yield (
            family.code, family.name, family.role, family.description,
            ",".join(family.physical_traits), family.portion_basis,
            family.portion_per_standard, family.portion_label,
            family.portion_rounding, int(family.stretchable),
            ",".join(family.flavor_domains), ",".join(family.culinary_functions),
            family.texture_contribution, family.color_contribution, 1,
        )


def seed_behavior_library(con):
    """Install current base-family knowledge; item exceptions remain untouched."""
    con.executemany(
        """INSERT INTO ko_behavior_families
           (family_code, family_name, role, description, physical_traits,
            portion_basis, portion_per_standard, portion_label,
            portion_rounding, stretchable, flavor_domains,
            culinary_functions, texture_contribution, color_contribution, verified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(family_code) DO UPDATE SET
             family_name=excluded.family_name, role=excluded.role,
             description=excluded.description, physical_traits=excluded.physical_traits,
             portion_basis=excluded.portion_basis,
             portion_per_standard=excluded.portion_per_standard,
             portion_label=excluded.portion_label,
             portion_rounding=excluded.portion_rounding,
             stretchable=excluded.stretchable,
             flavor_domains=excluded.flavor_domains,
             culinary_functions=excluded.culinary_functions,
             texture_contribution=excluded.texture_contribution,
             color_contribution=excluded.color_contribution,
             verified=excluded.verified""",
        list(iter_family_seed_rows()),
    )
    family_ids = dict(con.execute(
        "SELECT family_code, family_id FROM ko_behavior_families"
    ).fetchall())
    for family in FAMILY_LIBRARY.values():
        family_id = family_ids[family.code]
        for rule in family.methods:
            for form_name in (rule.forms or ("",)):
                con.execute(
                    """INSERT INTO ko_family_methods
                       (family_id, method_name, form_name, cooking_environment,
                        creates_environment, prep_minutes, cook_minutes,
                        active_minutes, attention_load, equipment_name,
                        add_stage, desired_outcome, handling_template,
                        instruction_template, doneness_cue, failure_mode,
                        recovery_hint, holdability, verification_required,
                        rest_minutes, rest_template, frozen_thaw_minutes,
                        frozen_thaw_equipment, frozen_thaw_template, verified)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                       ON CONFLICT(family_id,method_name,form_name) DO UPDATE SET
                         cooking_environment=excluded.cooking_environment,
                         creates_environment=excluded.creates_environment,
                         prep_minutes=excluded.prep_minutes,
                         cook_minutes=excluded.cook_minutes,
                         active_minutes=excluded.active_minutes,
                         attention_load=excluded.attention_load,
                         equipment_name=excluded.equipment_name,
                         add_stage=excluded.add_stage,
                         desired_outcome=excluded.desired_outcome,
                         handling_template=excluded.handling_template,
                         instruction_template=excluded.instruction_template,
                         doneness_cue=excluded.doneness_cue,
                         failure_mode=excluded.failure_mode,
                         recovery_hint=excluded.recovery_hint,
                         holdability=excluded.holdability,
                         verification_required=excluded.verification_required,
                         rest_minutes=excluded.rest_minutes,
                         rest_template=excluded.rest_template,
                         frozen_thaw_minutes=excluded.frozen_thaw_minutes,
                         frozen_thaw_equipment=excluded.frozen_thaw_equipment,
                         frozen_thaw_template=excluded.frozen_thaw_template,
                         verified=excluded.verified""",
                    (family_id, rule.method, form_name, rule.environment,
                     rule.creates_environment, rule.prep_minutes,
                     rule.cook_minutes, rule.active_minutes,
                     rule.attention_load, rule.equipment, rule.stage,
                     rule.desired_outcome, rule.handling_template,
                     rule.instruction_template, rule.doneness_cue,
                     rule.failure_mode, rule.recovery_hint, rule.holdability,
                     int(rule.verification_required), rule.rest_minutes,
                     rule.rest_template, rule.frozen_thaw_minutes,
                     rule.frozen_thaw_equipment, rule.frozen_thaw_template),
                )


def seed_behavior_memberships(con):
    """Classify known ingredients; new ingredients use this same table."""
    seed_behavior_library(con)
    family_ids = dict(con.execute(
        "SELECT family_code, family_id FROM ko_behavior_families"
    ).fetchall())
    ingredient_ids = {
        _key(name): ingredient_id
        for ingredient_id, name in con.execute("SELECT ingredient_id, name FROM ingredients")
    }
    # Rebuild only the memberships owned by this migration. Hand-trained rows
    # use different notes and are never removed.
    con.execute(
        "DELETE FROM ingredient_behavior_memberships WHERE notes='Initial behavior-family migration'"
    )
    for family_code, names in ASSIGNMENTS.items():
        for name in names:
            ingredient_id = ingredient_ids.get(_key(name))
            if ingredient_id is None:
                continue
            con.execute(
                """INSERT OR IGNORE INTO ingredient_behavior_memberships
                   (ingredient_id, family_id, form_name, priority, is_primary, notes, verified)
                   VALUES (?, ?, '', 100, 1, 'Initial behavior-family migration', 1)""",
                (ingredient_id, family_ids[family_code]),
            )

    attribute_rows = {
        "garlic": {
            "flavor_identity": "garlic", "quantity_basis": "pieces",
            "quantity_per_standard": "0.5", "quantity_label": "clove",
        },
        "garlic powder": {"flavor_identity": "garlic"},
        "onions": {"flavor_identity": "onion"},
        "onion powder": {"flavor_identity": "onion"},
        "basmati rice": {"pressure_minutes": "5", "pressure_cooked_elapsed_minutes": "25", "pressure_release_minutes": "10"},
        "white rice": {"pressure_minutes": "4", "pressure_cooked_elapsed_minutes": "25", "pressure_release_minutes": "10"},
        "jasmine rice": {"pressure_minutes": "4", "pressure_cooked_elapsed_minutes": "25", "pressure_release_minutes": "10"},
        "brown rice": {"pressure_minutes": "22", "pressure_cooked_elapsed_minutes": "32", "pressure_release_minutes": "10"},
        "wild rice": {"pressure_minutes": "28", "pressure_cooked_elapsed_minutes": "38", "pressure_release_minutes": "10"},
        "soy sauce": {"cuisine_affinity": "Chinese"},
        "tomato sauce": {"cuisine_affinity": "Italian"},
        "tomato paste": {"cuisine_affinity": "Italian"},
        "italian seasoning": {"cuisine_affinity": "Italian"},
        "chili powder": {"cuisine_affinity": "Mexican"},
        "cumin": {"cuisine_affinity": "Mexican"},
        "lemons": {
            "cuisine_affinity": "Mediterranean", "quantity_basis": "whole_count",
            "quantity_per_standard": "0.25", "quantity_label": "lemon",
        },
        "limes": {
            "cuisine_affinity": "Mexican,Mediterranean", "quantity_basis": "whole_count",
            "quantity_per_standard": "0.25", "quantity_label": "lime",
        },
        "scallions": {
            "quantity_basis": "prepared_cups", "quantity_per_standard": "0.125",
            "quantity_label": "cup",
        },
        "jalapenos": {
            "quantity_basis": "whole_count", "quantity_per_standard": "0.125",
            "quantity_label": "jalapeno",
        },
        "serranos": {
            "quantity_basis": "whole_count", "quantity_per_standard": "0.125",
            "quantity_label": "serrano",
        },
        "poblanos": {
            "quantity_basis": "whole_count", "quantity_per_standard": "0.25",
            "quantity_label": "poblano",
        },
        "avocado": {
            "quantity_basis": "whole_count", "quantity_per_standard": "0.25",
            "quantity_label": "avocado",
        },
        "black olives": {
            "quantity_basis": "prepared_cups", "quantity_per_standard": "0.125",
            "quantity_label": "cup",
        },
        "green olives": {
            "quantity_basis": "prepared_cups", "quantity_per_standard": "0.125",
            "quantity_label": "cup",
        },
        "pickles": {
            "quantity_basis": "prepared_cups", "quantity_per_standard": "0.125",
            "quantity_label": "cup",
        },
        "olive oil": {"cuisine_affinity": "Mediterranean"},
        "greek yogurt": {"cuisine_affinity": "Mediterranean"},
        "bbq sauce": {"cuisine_affinity": "BBQ"},
    }
    for name, attributes in attribute_rows.items():
        ingredient_id = ingredient_ids.get(_key(name))
        if ingredient_id is None:
            continue
        for attribute_name, attribute_value in attributes.items():
            con.execute(
                """INSERT INTO ko_ingredient_attributes
                   (ingredient_id,form_name,attribute_name,attribute_value,notes,verified)
                   VALUES (?,'',?,?, 'Initial KO attribute migration',1)
                   ON CONFLICT(ingredient_id,form_name,attribute_name) DO UPDATE SET
                     attribute_value=excluded.attribute_value,
                     notes=excluded.notes,
                     verified=excluded.verified""",
                (ingredient_id, attribute_name, attribute_value),
            )

    # These rows are the first durable, queryable expression of cross-KO
    # knowledge.  The marker makes schema refreshes idempotent without touching
    # future hand-trained rules.
    con.execute("DELETE FROM ko_relationship_rules WHERE rule_text LIKE '[SNS seed] %'")
    relationship_rows = (
        ("tough_meat", "balances_with", "citrus_finish", "[SNS seed] Bright acidity balances a rich long-cooked protein."),
        ("tough_meat", "supported_by", "aromatic_slow", "[SNS seed] Slow aromatics reinforce a braise without competing with it."),
        ("tough_meat", "supported_by", "sturdy_root", "[SNS seed] Dense roots can share the final part of a moist long cook."),
        ("stew_cut", "supported_by", "sturdy_root", "[SNS seed] Stew-size meat and sturdy roots suit the same moist-cooking structure."),
        ("poultry_piece", "supported_by", "aromatic_slow", "[SNS seed] Aromatics support poultry across skillet, soup, and bake routes."),
        ("poultry_piece", "supported_by", "mushroom", "[SNS seed] Mushrooms add savory depth while poultry remains the anchor."),
        ("poultry_piece", "supported_by", "tomato", "[SNS seed] Tomato adds moisture and acidity to poultry dishes."),
        ("ground_meat", "supported_by", "tomato", "[SNS seed] Tomato supplies moisture and acidity for browned ground meat."),
        ("ground_meat", "supported_by", "pepper", "[SNS seed] Peppers add sweetness, color, and structure to dispersed ground meat."),
        ("sausage", "balances_with", "cabbage", "[SNS seed] Cabbage provides a sturdy, less-rich counterpoint to sausage."),
        ("sausage", "supported_by", "pepper", "[SNS seed] Peppers complement sausage and hold their identity through staged cooking."),
        ("sausage", "supported_by", "tomato", "[SNS seed] Tomato gives sausage acidity and a sauce-building base."),
        ("tender_steak", "supported_by", "mushroom", "[SNS seed] Browned mushrooms reinforce a steak's savory flavor."),
        ("tender_steak", "balances_with", "citrus_finish", "[SNS seed] A restrained citrus finish can brighten a rich steak plate."),
        ("fish_fillet", "balances_with", "citrus_finish", "[SNS seed] Citrus brightens fish without requiring additional cooking."),
        ("fish_fillet", "supported_by", "fresh_herb", "[SNS seed] Fresh herbs add aroma without masking delicate fish."),
        ("shellfish_quick", "balances_with", "citrus_finish", "[SNS seed] Citrus gives quick-cooked shellfish a clean finish."),
        ("shellfish_quick", "supported_by", "aromatic_fast", "[SNS seed] Quick aromatics match shellfish's short cooking window."),
        ("pork_cut", "supported_by", "cabbage", "[SNS seed] Cabbage provides sturdy contrast beside a rich pork cut."),
        ("plant_protein", "supported_by", "tomato", "[SNS seed] Tomato supplies moisture and acidity to plant proteins."),
        ("plant_protein", "supported_by", "pepper", "[SNS seed] Peppers add sweetness and color to plant-protein meals."),
        ("legume", "supported_by", "tomato", "[SNS seed] Tomato adds acidity and cooking moisture to legumes."),
        ("prepared_legume", "supported_by", "aromatic_slow", "[SNS seed] Softened aromatics make prepared legumes taste integrated rather than merely added."),
        ("egg", "supported_by", "melting_cheese", "[SNS seed] Melting cheese adds richness and structure to cooked eggs."),
        ("egg", "supported_by", "tomato", "[SNS seed] Tomato provides brightness and moisture beside eggs."),
        ("tomato", "supported_by", "fresh_herb", "[SNS seed] Fresh herbs reinforce tomato's aroma at the finish."),
        ("tomato", "supported_by", "melting_cheese", "[SNS seed] Melting cheese softens tomato acidity and adds body."),
        ("cabbage", "balances_with", "acid_condiment", "[SNS seed] A measured acidic condiment brightens cooked cabbage."),
        ("cruciferous", "balances_with", "cultured_creamy", "[SNS seed] A tangy creamy finish softens a cruciferous vegetable's assertive edge."),
        ("winter_squash", "supported_by", "fresh_herb", "[SNS seed] Fresh herbs balance the sweetness of winter squash."),
        ("white_rice", "supported_by", "tomato_product", "[SNS seed] Rice can carry a measured tomato-based sauce."),
        ("pasta", "supported_by", "tomato_product", "[SNS seed] Pasta provides structure for a measured tomato sauce."),
    )
    for source, relationship, target, rule_text in relationship_rows:
        family_id = family_ids.get(source)
        if family_id:
            con.execute(
                """INSERT INTO ko_relationship_rules
                   (family_id,relationship_type,target_family_code,rule_text,priority,verified)
                   VALUES (?,?,?,?,100,1)""",
                (family_id, relationship, target, rule_text),
            )

    con.execute("DELETE FROM compatibility_rules WHERE reason LIKE '[SNS seed] %'")
    compatibility_rows = (
        ("tough_meat", "citrus_finish", "excellent", "[SNS seed] Brightness balances rendered richness."),
        ("tough_meat", "sturdy_root", "good", "[SNS seed] Both tolerate a staged moist cook."),
        ("stew_cut", "sturdy_root", "excellent", "[SNS seed] Their size and moist-cooking needs align well."),
        ("ground_meat", "tomato", "excellent", "[SNS seed] Moisture and acidity support browned meat."),
        ("ground_meat", "pepper", "good", "[SNS seed] Peppers add color and sweetness without competing with dispersed meat."),
        ("poultry_piece", "aromatic_slow", "good", "[SNS seed] Aromatics build a flexible savory base."),
        ("poultry_piece", "mushroom", "excellent", "[SNS seed] Both benefit from browning and share savory flavors."),
        ("poultry_piece", "tomato", "good", "[SNS seed] Tomato contributes moisture and acidity while poultry stays central."),
        ("sausage", "cabbage", "excellent", "[SNS seed] The vegetable tempers richness and holds its texture."),
        ("sausage", "pepper", "excellent", "[SNS seed] Sweet peppers and savory sausage are strong cooking partners."),
        ("sausage", "tomato", "good", "[SNS seed] Tomato balances richness and can become the meal's sauce."),
        ("tender_steak", "mushroom", "excellent", "[SNS seed] Their browned savory flavors reinforce one another."),
        ("tender_steak", "citrus_finish", "good", "[SNS seed] Restrained acidity brightens a rich steak."),
        ("fish_fillet", "citrus_finish", "excellent", "[SNS seed] Citrus adds brightness without extending delicate cooking."),
        ("fish_fillet", "fresh_herb", "excellent", "[SNS seed] Fresh herbs suit fish's delicate flavor and short cook."),
        ("shellfish_quick", "citrus_finish", "excellent", "[SNS seed] Citrus matches shellfish's quick-cooked freshness."),
        ("shellfish_quick", "aromatic_fast", "good", "[SNS seed] Both components fit the same short cooking window."),
        ("pork_cut", "cabbage", "good", "[SNS seed] Cabbage balances pork richness and remains structurally distinct."),
        ("plant_protein", "tomato", "good", "[SNS seed] Tomato adds moisture, acidity, and savory depth."),
        ("plant_protein", "pepper", "good", "[SNS seed] Peppers add sweetness, color, and texture."),
        ("legume", "tomato", "excellent", "[SNS seed] Tomato brings acidity and moisture to earthy legumes."),
        ("prepared_legume", "aromatic_slow", "good", "[SNS seed] Cooked aromatics integrate prepared beans into the meal."),
        ("egg", "melting_cheese", "excellent", "[SNS seed] Melted cheese complements eggs and adds structure."),
        ("egg", "tomato", "good", "[SNS seed] Tomato adds brightness and moisture to eggs."),
        ("tomato", "fresh_herb", "excellent", "[SNS seed] Fresh herbs reinforce tomato aroma."),
        ("tomato", "melting_cheese", "excellent", "[SNS seed] Cheese balances acidity and adds richness."),
        ("cabbage", "acid_condiment", "good", "[SNS seed] Acidity brightens cabbage's sturdy sweetness."),
        ("cruciferous", "cultured_creamy", "good", "[SNS seed] Tangy creaminess balances assertive cruciferous flavors."),
        ("winter_squash", "fresh_herb", "good", "[SNS seed] Herbal aroma counters squash sweetness."),
        ("white_rice", "tomato_product", "good", "[SNS seed] Rice readily carries a tomato-based sauce."),
        ("pasta", "tomato_product", "excellent", "[SNS seed] Pasta and tomato sauce form a coherent foundation."),
    )
    for source, target, rating, reason in compatibility_rows:
        source_id, target_id = family_ids.get(source), family_ids.get(target)
        if source_id and target_id:
            con.execute(
                """INSERT INTO compatibility_rules
                   (component_a_type,component_a_id,component_b_type,component_b_id,rating,reason,active)
                   VALUES ('behavior_family',?,'behavior_family',?,?,?,1)""",
                (source_id, target_id, rating, reason),
            )

    con.execute("DELETE FROM substitution_rules WHERE adjustment_notes LIKE '[SNS seed] %'")
    substitution_rows = (
        ("chicken broth", "vegetable broth", "good", "[SNS seed] Use the same volume; the result will be less poultry-forward."),
        ("chicken broth", "beef broth", "good", "[SNS seed] Use the same volume; expect a darker, beefier result."),
        ("beef broth", "chicken broth", "good", "[SNS seed] Use the same volume; the result will be lighter."),
        ("beef broth", "vegetable broth", "fair", "[SNS seed] Use the same volume and expect a less meaty result."),
        ("vegetable broth", "chicken broth", "good", "[SNS seed] Use the same volume when poultry flavor fits the meal."),
        ("vegetable broth", "beef broth", "fair", "[SNS seed] Use the same volume only when a darker meat flavor fits the meal."),
        ("butter", "olive oil", "good", "[SNS seed] Use the same volume; expect less dairy richness."),
        ("butter", "vegetable oil", "good", "[SNS seed] Use the same volume for cooking; the result will have less buttery flavor."),
        ("olive oil", "butter", "good", "[SNS seed] Use the same volume and keep the heat moderate to protect the milk solids."),
        ("olive oil", "vegetable oil", "good", "[SNS seed] Use the same volume; the result will have a more neutral flavor."),
        ("vegetable oil", "canola oil", "excellent", "[SNS seed] Use the same volume; both are neutral cooking oils."),
        ("canola oil", "vegetable oil", "excellent", "[SNS seed] Use the same volume; both are neutral cooking oils."),
        ("sour cream", "greek yogurt", "excellent", "[SNS seed] Stir in off heat to reduce the chance of splitting."),
        ("greek yogurt", "sour cream", "excellent", "[SNS seed] Use the same volume; the result will be slightly richer."),
        ("mayonnaise", "greek yogurt", "fair", "[SNS seed] Use in a cold spread or finish; expect more tang and less richness."),
        ("tomato sauce", "diced tomatoes", "good", "[SNS seed] Use the same volume and simmer longer for a smoother sauce."),
        ("diced tomatoes", "tomato sauce", "good", "[SNS seed] Use the same volume; the result will be smoother and less chunky."),
        ("tomato paste", "tomato sauce", "fair", "[SNS seed] Thin each tablespoon of paste with about three tablespoons of water."),
        ("lemons", "limes", "good", "[SNS seed] Use to taste; the flavor will be sharper and more floral."),
        ("limes", "lemons", "good", "[SNS seed] Use to taste; the flavor will be softer and more familiar."),
        ("white rice", "brown rice", "fair", "[SNS seed] Recalculate liquid and allow substantially more cooking time."),
        ("white rice", "quinoa", "good", "[SNS seed] Rinse first and use quinoa's package liquid and timing."),
        ("pinto beans", "black beans", "good", "[SNS seed] Use the same drained canned amount; expect a darker, earthier flavor."),
        ("pinto beans", "white beans", "good", "[SNS seed] Use the same drained canned amount; the result will be milder."),
        ("white beans", "chickpeas", "good", "[SNS seed] Use the same drained canned amount; expect a firmer texture."),
        ("garlic", "garlic powder", "fair", "[SNS seed] Use about 1/8 teaspoon garlic powder per fresh clove and add it with dry seasonings."),
        ("garlic powder", "garlic", "good", "[SNS seed] Use about one small minced clove per 1/8 teaspoon and cook it with the aromatics."),
        ("onions", "onion powder", "fair", "[SNS seed] Use about 1 teaspoon onion powder per small onion; the meal will lose fresh texture."),
        ("onion powder", "onions", "good", "[SNS seed] Use a small chopped onion and allow time to soften it before liquids join."),
        ("cornstarch", "all-purpose flour", "fair", "[SNS seed] Use roughly twice as much flour and cook it with fat before adding liquid."),
        ("spaghetti", "egg noodles", "good", "[SNS seed] Follow the replacement noodle's package timing and test before draining."),
        ("egg noodles", "spaghetti", "good", "[SNS seed] Follow the replacement pasta's package timing and test before draining."),
    )
    for original, substitute, quality, note in substitution_rows:
        original_id, substitute_id = ingredient_ids.get(original), ingredient_ids.get(substitute)
        if original_id and substitute_id:
            con.execute(
                """INSERT INTO substitution_rules
                   (original_type,original_id,substitute_type,substitute_id,quality,adjustment_notes)
                   VALUES ('ingredient',?,'ingredient',?,?,?)""",
                (original_id, substitute_id, quality, note),
            )
