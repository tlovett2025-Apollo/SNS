"""Composable behavior-family intelligence for Stock & Stir Knowledge Objects.

An ingredient inherits an operational family, optional trait families, form
rules, and finally ingredient-specific exceptions.  The planner consumes the
resolved behavior; it does not invent ingredient science from the ingredient
name.
"""

from dataclasses import dataclass, field, replace
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


@dataclass(frozen=True)
class BehaviorFamily:
    code: str
    name: str
    role: str
    description: str
    physical_traits: Tuple[str, ...]
    methods: Tuple[MethodRule, ...]
    relationship_traits: Tuple[str, ...] = ()


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

    @property
    def family_codes(self):
        return [family.code for family in [self.primary_family, *self.trait_families] if family]


def method(
    name, forms, environment, creates, prep, cook, active, attention,
    equipment, stage, handling, instruction, outcome, cue, failure, recovery,
    holdability="fair",
):
    return MethodRule(
        name, tuple(forms), environment, creates, prep, cook, active, attention,
        equipment, stage, handling, instruction, outcome, cue, failure,
        recovery, holdability,
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
            "Evenly browned, moist crumbles.", "The center of the thickest clump reaches the ingredient's safe temperature.",
            "Large clumps can brown outside while remaining undercooked inside.",
            "Break apart large clumps and continue cooking; add sauce if it becomes dry.", "fair",
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
            "Cut {name} into even pieces when appropriate; thaw before browning.",
            "Brown {name} in batches, add enough liquid for a braise, cover, and cook gently until fork-tender.",
            "Fork-tender meat with connective tissue softened into the cooking liquid.",
            "A fork enters easily and the meat yields without springing back.",
            "A short hot cook leaves the meat safe but unpleasantly tough.",
            "Add liquid, cover, lower the heat, and continue until tender.", "excellent",
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
            "Trim and peel {name} as needed, then cut into even pieces.",
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
            "Scrub or peel {name} as appropriate and cut into small, even pieces.",
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
        ), READY_REHEAT),
        ("dry-versus-canned-critical", "can-stretch-protein"),
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
            "Sear {name} without moving it until well browned and it releases readily; turn once, cook to the chosen doneness, then rest before slicing.",
            "A deeply browned exterior and the requested interior doneness.",
            "Use an instant-read thermometer: about 125–130°F medium-rare or 135–140°F medium before a short rest; follow household safety needs.",
            "Turning too early prevents browning; cooking only by the clock can over- or undercook a thick steak.",
            "Lower the heat if the crust darkens too quickly; rest and serve a more-done steak with sauce.", "fair",
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
        ), READY_REHEAT), ("rest-required",),
    ),
    "ready_protein": BehaviorFamily(
        "ready_protein", "Ready-to-eat protein", "protein",
        "A cooked or canned protein needing preparation and gentle reheating, never recooking.",
        ("ready-to-eat", "form-sensitive"), (READY_REHEAT,), ("late-entry",),
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
        ), READY_REHEAT), ("joins-aromatics",),
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
            "Evenly rendered bacon at the chosen tenderness or crispness.", "Fat is rendered and the meat is deeply colored without blackened edges.",
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
        ), READY_REHEAT), ("oven-required", "rest-required"),
    ),
})


ASSIGNMENTS = {
    "ground_meat": {"ground beef", "ground chicken", "ground turkey"},
    "tough_meat": {"beef stew meat", "chuck roast", "beef brisket", "pork shoulder"},
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
    "sweet_kernel": {"corn", "peas"},
    "artichoke": {"artichokes"},
    "tough_meat": ASSIGNMENTS["tough_meat"] | {"corned beef"},
    "citrus_finish": {"lemons", "limes"},
    "quinoa": {"quinoa"},
    "corn_porridge": {"grits", "polenta"},
    "soft_potato": {"mashed potatoes"},
    "crisp_potato": {"french fries", "hash browns", "roasted potatoes"},
    "baked_potato": {"baked potatoes"},
})


def _db_family_codes(name, form_name, db_path) -> list[str]:
    if not db_path:
        return []
    try:
        con = sqlite3.connect(db_path)
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
        con.close()
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
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        family = con.execute(
            "SELECT * FROM ko_behavior_families WHERE family_code=? AND verified=1",
            (family_code,),
        ).fetchone()
        if not family:
            con.close()
            return None
        rows = con.execute(
            """SELECT * FROM ko_family_methods
               WHERE family_id=? AND verified=1
               ORDER BY family_method_id""",
            (family["family_id"],),
        ).fetchall()
        con.close()
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
        ) for row in rows)
        return BehaviorFamily(
            family["family_code"], family["family_name"], family["role"],
            family["description"],
            tuple(part.strip() for part in (family["physical_traits"] or "").split(",") if part.strip()),
            methods,
        )
    except sqlite3.Error:
        return None


def _apply_db_exceptions(rule, name, form_name, db_path):
    if not rule or not db_path:
        return rule
    try:
        con = sqlite3.connect(db_path)
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
        con.close()
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


def resolve_behavior(name, role, form_name="", strategy="", db_path=None) -> ResolvedBehavior:
    codes, source = family_codes_for(name, role, form_name, db_path)
    # Meal role is contextual: beans may be today's protein and avocado may be
    # today's produce. Physical behavior follows the ingredient, not the slot.
    families = []
    for code in codes:
        family = _db_family(code, db_path) if source == "ckb_membership" else None
        family = family or FAMILY_LIBRARY.get(code)
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
        casserole_methods = {"roast", "bake", "reheat", "assemble", "simmer"}
        for candidate in primary.methods:
            form_matches = not form_key or not candidate.forms or any(value in form_key for value in candidate.forms)
            strategy_matches = not strategy_key or candidate.method == strategy_key or (
                strategy_key == "skillet" and candidate.method in skillet_methods
            ) or (
                strategy_key == "soup" and candidate.method in soup_methods
            ) or (
                strategy_key == "casserole" and candidate.method in casserole_methods
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
    return ResolvedBehavior(name, role, form_name, primary, families[1:], selected, source, reason)


def iter_family_seed_rows() -> Iterable[tuple]:
    for family in FAMILY_LIBRARY.values():
        yield (
            family.code, family.name, family.role, family.description,
            ",".join(family.physical_traits), 1,
        )


def seed_behavior_library(con):
    """Install reusable family knowledge without overwriting trained edits."""
    con.executemany(
        """INSERT OR IGNORE INTO ko_behavior_families
           (family_code, family_name, role, description, physical_traits, verified)
           VALUES (?, ?, ?, ?, ?, ?)""",
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
                    """INSERT OR IGNORE INTO ko_family_methods
                       (family_id, method_name, form_name, cooking_environment,
                        creates_environment, prep_minutes, cook_minutes,
                        active_minutes, attention_load, equipment_name,
                        add_stage, desired_outcome, handling_template,
                        instruction_template, doneness_cue, failure_mode,
                        recovery_hint, holdability, verified)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (family_id, rule.method, form_name, rule.environment,
                     rule.creates_environment, rule.prep_minutes,
                     rule.cook_minutes, rule.active_minutes,
                     rule.attention_load, rule.equipment, rule.stage,
                     rule.desired_outcome, rule.handling_template,
                     rule.instruction_template, rule.doneness_cue,
                     rule.failure_mode, rule.recovery_hint, rule.holdability),
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
