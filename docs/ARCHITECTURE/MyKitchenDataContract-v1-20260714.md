# Stock & Stir — My Kitchen Data Contract v1

**Status:** Architecture decision for implementation  
**Date:** 2026-07-14  
**Scope:** Household inventory, equipment, meal requests, candidate meals, cost metadata, cold/no-cook meals, and batch-prepared inventory

## 1. Purpose

This contract defines the stable boundary between the public Stock & Stir website, household data, the Culinary Knowledge Base (CKB), and the cooking planner.

The immediate goal is to connect the existing website to the existing planner without freezing Stock & Stir into its current ingredient set or hot-meal assumptions. API v1 must be usable now and expandable later for:

- hundreds of additional ingredients;
- cold and no-cook meals;
- hot and cold sandwiches;
- green, grain, pasta, bean, and composed salads;
- batch cooking and reusable prepared ingredients;
- “feed four for $5, $10, or $25” discovery;
- household-specific equipment, preferences, and skill support.

The contract does not assert that all of these capabilities are trained in the current engine. It reserves stable, explicit places for them so later training is additive rather than a breaking API redesign.

## 2. Governing Decisions

### 2.1 Separate household facts from culinary knowledge

The household owns records such as “two cans of tuna in the pantry” and “four cups of cooked beans in the freezer.” The CKB owns facts such as how tuna behaves, what roles mayonnaise can fill, and whether kale and lettuce can safely share planning logic.

### 2.2 Food, equipment, and skill are separate record types

My Kitchen may display them in one product area, but they must not share an inventory table or pretend to be interchangeable objects.

### 2.3 Ingredient Family is not Specific Ingredient Identity

Families organize browsing, search, substitution, and knowledge inheritance. Specific ingredients drive planning when culinary behavior differs.

Examples:

- `leafy_greens` is a family.
- `spinach`, `kale`, `swiss_chard`, and `romaine_lettuce` are specific ingredients.
- `beans` is a family.
- `cannellini_beans_canned` and `black_beans_dry` are specific ingredient/forms with materially different preparation requirements.

### 2.4 Broad families proceed only when planning-safe

A family may be stored or submitted without a specific ingredient only when the CKB marks `planning_safe_as_family: true`. The default is false.

`Fresh Greens` is not planning-safe as a universal ingredient. The UI may use it as a category heading, but it must not silently become an inventory ingredient.

### 2.5 Cost does not create culinary compatibility

The engine first determines whether a meal is culinarily valid. Cost may then filter, rank, or label valid candidates.

Cost must never make incompatible ingredients become a meal merely because their prices fit a target.

### 2.6 Batch cooking creates inventory

Batch cooking is not merely a large recipe. It consumes household inventory and produces one or more reusable prepared inventory lots with their own quantity, storage location, preparation state, and dates.

### 2.7 API clients must tolerate additive vocabulary

The website must display or safely fall back when it receives a future `meal_shape`, `serving_temperature`, `preparation_mode`, or ingredient role it does not yet recognize. New enum values are additive and must not crash old clients.

## 3. Conceptual Model

| Entity | Owner | Purpose |
|---|---|---|
| Ingredient Family | CKB | Browsing, inheritance, substitution grouping |
| Specific Ingredient | CKB | Culinary identity used by the planner |
| Ingredient Form | CKB | Fresh raw, frozen, cooked, canned, dried, prepared, etc. |
| Household Inventory Lot | Household | What is available, how much, where, and in what state |
| Equipment Record | Household | Available cooking capacity and constraints |
| Household Profile | Household | Preferences, restrictions, skill, serving defaults, locality |
| Meal Request | Transaction | What the household wants right now |
| Meal Candidate | Planner | A valid possible meal and its metadata |
| Meal Plan | Planner | Selected meal, activities, timing, equipment, and outputs |
| Preparation Batch | Household/Planner | Inputs consumed and reusable inventory outputs produced |
| Price Observation | Pricing data | Place- and date-qualified package price estimate |

## 4. Ingredient Identity

### 4.1 Ingredient Family

Required fields:

```json
{
  "family_id": "leafy_greens",
  "display_name": "Leafy greens",
  "parent_family_id": "vegetables",
  "planning_safe_as_family": false,
  "specific_selection_required": true,
  "active": true
}
```

Rules:

- A family is not a purchasable or countable household item by default.
- A family may contain other families.
- A family may provide inherited defaults, but specific knowledge overrides them.
- The UI may initially show families as collapsible category streams.
- Selection of an unsafe family opens its specific ingredients rather than adding the family to inventory.

### 4.2 Specific Ingredient

Required and extensible fields:

```json
{
  "ingredient_id": "spinach",
  "family_id": "leafy_greens",
  "display_name": "Spinach",
  "default_storage": "fridge",
  "supported_forms": ["fresh_raw", "frozen", "cooked"],
  "culinary_roles": ["leafy_base", "vegetable", "sandwich_green"],
  "active": true
}
```

`culinary_roles` describes what an ingredient may do in a meal grammar. Roles may include:

- `protein`
- `binder`
- `crunch`
- `acid`
- `pickle_relish`
- `carrier`
- `bread_wrap`
- `leafy_base`
- `sandwich_green`
- `spread`
- `cheese`
- `sauce`
- `foundation`
- `vegetable`
- `aromatic`
- `garnish`

Roles are not mutually exclusive and are not a substitute for KO knowledge.

### 4.3 Ingredient Form

The existing core Forms remain valid:

- `fresh_raw`
- `frozen`
- `cooked`
- `canned`

API v1 must permit additive forms needed by future data, including:

- `dry`
- `prepared`
- `leftover`
- `thawed`
- `refrigerated_packaged`

The CKB determines which forms are valid for each specific ingredient.

## 5. Household Inventory Lot

An inventory lot represents a household quantity with a shared identity, form, storage location, and origin.

```json
{
  "inventory_lot_id": "inv_01J2TUNA01",
  "household_id": "hh_demo",
  "ingredient_id": "tuna_canned",
  "family_id": "fish",
  "form": "canned",
  "quantity": {
    "value": 2,
    "unit": "can",
    "approximate": false
  },
  "storage_location": "pantry",
  "quantity_band": "some",
  "opened": false,
  "origin": "purchased",
  "prepared_batch_id": null,
  "acquired_on": null,
  "prepared_on": null,
  "use_by": null,
  "notes": null,
  "version": 1
}
```

### 5.1 Quantity policy

The contract supports both broad household quantity bands and exact quantities:

- `a_little`
- `some`
- `plenty`
- exact quantity when the household chooses to provide it

Exact inventory bureaucracy is not required for initial use. Exact quantity becomes more valuable for batch cooking, cost calculations, and planned leftovers.

### 5.2 Origin

Allowed initial values:

- `purchased`
- `prepared_batch`
- `meal_leftover`
- `manual`
- `unknown`

Origin supports traceability without mixing the inventory lot with a recipe or batch record.

### 5.3 Inventory mutation

Inventory changes must be versioned or transaction-safe. A meal plan must not silently consume inventory merely because it was displayed. Consumption occurs only when a household confirms preparation or manually edits inventory.

## 6. Equipment Record

```json
{
  "equipment_id": "eq_rice_cooker_1",
  "household_id": "hh_demo",
  "equipment_type": "rice_cooker",
  "display_name": "Rice cooker",
  "quantity": 1,
  "capacity": {
    "value": 6,
    "unit": "cup_cooked"
  },
  "capabilities": ["cook_rice", "hold_warm"],
  "available": true,
  "notes": null
}
```

Equipment records may describe burners, oven, microwave, pressure cooker, slow cooker, air fryer, blender, rice cooker, and later tools. Planner capacity comes from equipment records, not a hard-coded universal kitchen.

## 7. Household Profile Boundary

The household profile may contain:

- default servings;
- dietary restrictions and allergies;
- dislikes and texture requirements;
- cooking skill/comfort;
- desired teaching level;
- energy and accessibility defaults;
- locality for price and tax estimates;
- assumed staples policy.

Skill belongs here, not in food inventory. A household member profile may later override household defaults.

Example locality:

```json
{
  "country": "US",
  "region": "AR",
  "postal_code": "71909",
  "grocery_tax_rate": 0.025,
  "tax_rate_source": "household_confirmed"
}
```

Tax rates are configurable household/locality data. They are never hard-coded as one national assumption.

## 8. Meal Classification

Meal classification requires three separate axes.

### 8.1 Meal shape

Initial vocabulary:

- `plate`
- `bowl`
- `soup`
- `stew`
- `casserole`
- `sandwich`
- `wrap`
- `salad`
- `snack_plate`
- `batch_preparation`

Meal shape answers: **What kind of assembled eating experience is this?**

### 8.2 Serving temperature

- `cold`
- `room_temperature`
- `warm`
- `hot`
- `mixed`

Serving temperature answers: **At what temperature is the completed meal intended to be eaten?** It does not prove whether heat was used during preparation.

### 8.3 Preparation mode

- `no_cook`
- `assembly_only`
- `cooked`
- `mixed`
- `cook_then_chill`
- `reheat_and_assemble`

Preparation mode answers: **What kind of work creates the meal?**

Examples:

| Meal | Shape | Serving temperature | Preparation mode |
|---|---|---|---|
| Cold turkey sandwich | sandwich | cold | assembly_only |
| Grilled turkey and cheese | sandwich | hot | cooked |
| Meatball sub | sandwich | hot | reheat_and_assemble |
| Green salad with canned chicken | salad | cold | assembly_only |
| Pasta salad | salad | cold | cook_then_chill |
| Warm spinach and white bean salad | salad | warm | cooked |

## 9. Meal Grammar and Completeness

Meal grammar defines roles that must or may be filled for a meal shape. It prevents ingredient possession from being mistaken for meal completeness.

Illustrative tuna salad grammar:

```json
{
  "grammar_id": "mixed_protein_salad",
  "required_role_groups": [
    {"any_of": ["protein"]},
    {"any_of": ["binder", "dressing"]}
  ],
  "recommended_role_groups": [
    {"any_of": ["crunch"]},
    {"any_of": ["acid", "pickle_relish", "mustard"]}
  ],
  "service_options": [
    {"any_of": ["bread_wrap", "cracker", "leafy_base", "bowl"]}
  ]
}
```

Tuna plus celery fills `protein` and `crunch`, but does not automatically form a complete tuna salad. The engine may:

1. find a valid household substitute for the missing functional role;
2. offer a short shopping list;
3. offer a different valid meal;
4. explain that no complete match is currently available.

It must not fabricate compatibility or silently omit structurally necessary roles.

## 10. Cost Contract

### 10.1 Three cost views

Stock & Stir must distinguish:

1. **Consumed cost** — estimated value of the quantities used.
2. **Shop-today cost** — estimated cost of packages the household still needs to buy, treating usable inventory as already owned.
3. **Full-basket cost** — estimated cost of buying every required package from an empty kitchen.

This distinction makes “What can I make with what I have?” and “Feed four for $25” both honest and useful.

### 10.2 Cost estimate object

```json
{
  "currency": "USD",
  "servings": 4,
  "consumed_cost": 17.84,
  "shop_today": {
    "subtotal": 21.09,
    "estimated_tax": 0.53,
    "total": 21.62
  },
  "full_basket": {
    "subtotal": 24.58,
    "estimated_tax": 0.61,
    "total": 25.19
  },
  "tax_rate": 0.025,
  "tax_rate_source": "household_confirmed",
  "price_region": "US-AR-71909",
  "priced_on": "2026-07-14",
  "confidence": "medium",
  "assumptions": ["salt and cooking oil treated as household staples"]
}
```

### 10.3 Cost filtering rule

The candidate engine follows this order:

1. Determine culinary validity and household safety.
2. Calculate cost estimates for valid candidates.
3. Apply an explicit maximum-cost filter when requested.
4. Rank remaining candidates using relevant non-cost and optional cost preferences.

The legacy `budget` score should be retired or translated at the API boundary. The durable concept is `cost_estimate` plus an explicit `cost_filter`.

### 10.4 Price limitations

Every estimate should retain region, date, source, and confidence when known. Package prices and taxes vary. A price estimate is not a promise that a particular store will charge exactly that amount.

## 11. Batch Cooking and Prepared Inventory

### 11.1 Batch preparation request

Batch preparation may be requested directly or suggested as part of weekly planning.

```json
{
  "mode": "batch_preparation",
  "target": {
    "ingredient_id": "ground_beef",
    "output_form": "cooked",
    "input_quantity": {"value": 5, "unit": "lb"}
  },
  "portion_plan": [
    {"quantity": {"value": 1, "unit": "lb"}, "storage_location": "fridge"},
    {"quantity": {"value": 3, "unit": "lb"}, "storage_location": "freezer"}
  ]
}
```

### 11.2 Preparation Batch record

```json
{
  "prepared_batch_id": "batch_01J2BEEF01",
  "household_id": "hh_demo",
  "status": "completed",
  "prepared_on": "2026-07-14",
  "input_lots": [
    {
      "inventory_lot_id": "inv_raw_beef",
      "quantity_consumed": {"value": 5, "unit": "lb"}
    }
  ],
  "outputs": [
    {
      "ingredient_id": "ground_beef",
      "form": "cooked",
      "quantity": {"value": 1, "unit": "lb"},
      "storage_location": "fridge",
      "use_by": "2026-07-18"
    },
    {
      "ingredient_id": "ground_beef",
      "form": "cooked",
      "quantity": {"value": 3, "unit": "lb"},
      "storage_location": "freezer",
      "use_by": null
    }
  ],
  "yield_note": "Output quantity is estimated after cooking loss.",
  "source_meal_plan_id": null
}
```

### 11.3 Batch rules

- Batch inputs and outputs use ordinary ingredient identities and Forms.
- A completed batch creates new inventory lots with `origin: prepared_batch`.
- Input consumption and output creation must occur in one transaction.
- Output quantity may differ from input quantity because of draining, trimming, evaporation, or absorption.
- Portions may be split across fridge and freezer.
- A regular meal may also produce planned reusable leftovers.
- Food-safety dates and thaw/reheat behavior belong to CKB knowledge, not hard-coded UI rules.
- The household confirms batch completion before inventory changes.

This structure supports pots of beans, browned ground beef, cooked chicken, rice, sauces, roasted vegetables, and future prep-ahead components.

## 12. API v1

The HTTP path names below are recommended. Existing internal function names may remain temporarily behind adapters.

### 12.1 Household kitchen

- `GET /api/v1/households/{household_id}/kitchen`
- `POST /api/v1/households/{household_id}/inventory-lots`
- `PATCH /api/v1/households/{household_id}/inventory-lots/{inventory_lot_id}`
- `DELETE /api/v1/households/{household_id}/inventory-lots/{inventory_lot_id}`
- `PUT /api/v1/households/{household_id}/equipment`
- `PATCH /api/v1/households/{household_id}/profile`

### 12.2 Meal discovery and planning

- `POST /api/v1/meal-candidates` — durable replacement/adapter target for `GetRecipeList`
- `POST /api/v1/meal-plans` — durable replacement/adapter target for `GetRecipe`

The request sends stable IDs and household context. Display names may be included for convenience but are not identifiers.

### 12.3 Batch preparation

- `POST /api/v1/batch-plans`
- `POST /api/v1/batch-plans/{batch_plan_id}/complete`

Completion is the inventory mutation boundary.

## 13. Example GetRecipeList Request and Response

### Request

```json
{
  "api_version": "1.0",
  "household_id": "hh_demo",
  "servings": 4,
  "energy": "low",
  "available_inventory_lot_ids": [
    "inv_tuna_2cans",
    "inv_celery",
    "inv_spinach",
    "inv_mustard"
  ],
  "meal_preferences": {
    "allowed_shapes": ["sandwich", "salad", "bowl", "plate"],
    "allowed_serving_temperatures": ["cold", "room_temperature", "warm", "hot"],
    "maximum_active_minutes": 20
  },
  "cost_filter": {
    "cost_view": "shop_today",
    "maximum_total": 25.00,
    "currency": "USD"
  }
}
```

### Response

```json
{
  "api_version": "1.0",
  "request_id": "req_01J2MEAL01",
  "candidates": [
    {
      "candidate_id": "cand_lemon_shrimp_beans",
      "title": "Lemon-Dill Shrimp over White Beans and Spinach",
      "meal_shape": "bowl",
      "serving_temperature": "warm",
      "preparation_mode": "cooked",
      "servings": 4,
      "energy": "low",
      "total_minutes": 28,
      "active_minutes": 16,
      "passive_minutes": 12,
      "attention": 4,
      "effort": 4,
      "score": 87,
      "uses_inventory_lot_ids": ["inv_spinach"],
      "missing_items": [
        {
          "ingredient_id": "shrimp_raw",
          "display_name": "Shrimp",
          "required": true,
          "estimated_package_price": 12.50
        },
        {
          "ingredient_id": "lemon",
          "display_name": "Lemon",
          "required": true,
          "estimated_package_price": 1.95
        },
        {
          "ingredient_id": "cannellini_beans_canned",
          "display_name": "Canned white beans",
          "required": true,
          "estimated_package_price": 1.70
        },
        {
          "ingredient_id": "fresh_dill",
          "display_name": "Fresh dill",
          "required": false,
          "estimated_package_price": 1.95
        }
      ],
      "cost_estimate": {
        "currency": "USD",
        "servings": 4,
        "shop_today": {
          "subtotal": 18.10,
          "estimated_tax": 0.45,
          "total": 18.55
        },
        "tax_rate": 0.025,
        "price_region": "US-AR-71909",
        "confidence": "medium"
      },
      "capability_status": "supported"
    }
  ],
  "notices": []
}
```

`capability_status` may be `supported`, `experimental`, or `not_yet_trained`. This permits the API vocabulary to precede complete engine training without misleading the website or user.

## 14. Fresh Greens Decision Table

| Specific ingredient | Typical useful forms | Heat behavior | Raw use | Planner distinction required |
|---|---|---|---|---|
| Spinach | fresh raw, frozen, cooked | Wilts rapidly | Common in salads/sandwiches | Yes |
| Kale | fresh raw, cooked | Tougher; longer cooking | Usually benefits from cutting/massaging | Yes |
| Swiss chard | fresh raw, cooked | Stems and leaves cook differently | Possible but distinct | Yes |
| Romaine lettuce | fresh raw | Poor general cooking substitute | Common salad/sandwich base | Yes |
| Iceberg lettuce | fresh raw | Primarily crisp/raw | Common for crunch | Yes |
| Arugula | fresh raw, lightly wilted | Wilts rapidly | Peppery salad/sandwich green | Yes |
| Collard greens | fresh raw, cooked | Usually long-cooking | Limited/specialized raw use | Yes |

Decision: **Fresh Greens remains a UI category/family, never a universal cooking ingredient.** The household selects a specific green before it enters planning inventory.

## 15. Mobile My Kitchen Wireframe Decision

The mobile page uses independently collapsible streams rather than four permanently expanded grids.

Order:

1. Persistent search/add field
2. Selected-item summary with count and quick removal
3. Pantry stream
4. Fridge stream
5. Freezer stream
6. Fresh stream
7. Equipment stream
8. Continue to Make a Meal

Within each storage stream:

- show collapsible ingredient families;
- show selected quantities/forms inline;
- search across all streams;
- open a family to select specific ingredients;
- never force single-select behavior;
- keep equipment visually distinct from food;
- keep skill/profile questions out of inventory streams.

The selected-item summary prevents users from repeatedly reopening categories merely to confirm what they chose.

## 16. Proposed Persistence Changes

Exact migration syntax must be written against the actual repository schema. The logical changes are:

1. Add or formalize `ingredient_families`.
2. Link each specific ingredient to a family.
3. Add family planning-safety flags.
4. Add supported Forms and culinary-role relationships.
5. Add household inventory lots rather than a browser-only selected list.
6. Add household equipment records.
7. Add household profile/locality and skill fields separately.
8. Add preparation batches with input and output rows.
9. Add regional, dated price observations or a pricing-provider boundary.
10. Add meal candidate/plan fields for shape, serving temperature, preparation mode, and cost estimate.

No database migration should be guessed without the checked-out project and its current tests.

## 17. Compatibility and Rollout

### Phase 1 — Contract and adapters

- Preserve current planner behavior.
- Return the new fields for currently supported hot meals.
- Translate legacy `GetRecipeList` and `GetRecipe` calls through API v1 adapters.
- Mark untrained capabilities accurately.

### Phase 2 — Website vertical slice

- Persist My Kitchen household data.
- Call the real candidate and plan endpoints.
- Display current supported meals end to end.
- Conduct visual testing with the initial four-person review group.

### Phase 3 — Focused culinary expansion

- Train cold/no-cook activities and meal grammars.
- Add sandwich and salad families.
- Add functional-role substitutions.
- Add cost filtering and shopping-list estimates.
- Add batch-plan generation and inventory outputs.

### Phase 4 — Ingredient expansion

- Import the next ingredient wave only after the vertical slice and contracts are stable.
- Prefer focused, testable waves over an undifferentiated 500-row load.
- Validate family assignment, Forms, roles, KO behavior, and aliases with each wave.

## 18. Deferred Acceptance-Test Deliverable

A coordinated human acceptance-test suite will be created when the website vertical slice is ready. It will divide scenarios among Tracy, Lynsey, Lynsey’s mother, and Annmarie and provide a common result-reporting format.

It is deliberately deferred now so tests describe a working interface rather than a moving architecture target.

## 19. Definition of Done for Data Contract v1

The contract is implemented when:

- household inventory persists outside browser-only session state;
- food, equipment, and skill/profile records are separate;
- unsafe broad families cannot masquerade as specific ingredients;
- current hot meals pass through versioned API endpoints;
- meal responses include shape, temperature, and preparation mode;
- cost metadata can be absent without breaking the client;
- batch outputs can be represented as new household inventory lots;
- old clients tolerate new additive values;
- existing regression tests remain green;
- website users can complete Inventory → Candidates → Meal Plan using the current CKB.

## 20. Immediate Engineering Order

1. Attach the current clean repository version.
2. Map this contract onto the actual database and API code.
3. Implement only the schema fields and adapters needed for the vertical slice.
4. Keep cold meals, pricing intelligence, and batch execution behind capability flags until trained.
5. Run the complete regression suite.
6. Connect and visually test the public My Kitchen workflow.

This order protects the working Horizon D engine while preventing the public integration from becoming a dead-end contract.
