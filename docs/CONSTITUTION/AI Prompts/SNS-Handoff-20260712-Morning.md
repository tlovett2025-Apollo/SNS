# SNS Handoff — Morning Restart

**Prepared:** July 11, 2026  
**Restart date:** July 12, 2026  
**Milestone:** Horizon D closed; teaching and inventory-interface work begins

## Repository State

- Horizon D Executive Chef loop was integrated, tested, committed, and pushed by Tracy.
- Do not roll back the Horizon D close.
- Begin by running the normal `goodmorning` workflow and confirming a clean working tree.

## Horizon D Status

Horizon D is accepted as architecturally complete. The proven loop is:

```text
Opportunity
→ Ingredient/Culinary Knowledge
→ Equipment Selection
→ Sauce Requirements
→ Have/Need Resolution
→ Activity Consolidation
→ Attention-Aware Scheduling
→ Printed Recipe
```

The regression meal remains:

**Chicken breast + mushrooms + asparagus + Swiss chard + Basmati rice — Chinese**

Current proof behavior includes:

- rice cooker selected as the preferred off-burner rice method;
- pressure cooker alternative modeled with pressurize/cook/natural-release phases;
- mushrooms browned first;
- chicken and vegetables overlap based on fractional attention;
- detailed ingredient preparation/cooking instructions;
- real simple stir-fry Sauce KO;
- grocery gaps and Have/Need status;
- schedule-derived time metrics;
- printed instructions rendered from the scheduled activity graph.

## First Correction Tomorrow

Consolidate final service.

The current prototype may extend the meal with separate actions for plating sides, waiting, slicing chicken, and serving chicken. Tracy judges the meal functionally complete around minute 33–34. Review whether the final actions can become one realistic service activity without violating chicken rest or food quality.

Do not reopen the entire planner architecture to fix this. Treat it as Activity Consolidation refinement.

## Primary New Goal: Inventory Interface Simulator

Build a point-and-click Streamlit interface that mimics the future production inventory UX and proves the interface between UX and engine.

### User experience

Display known kitchen items by category and let the user select what exists:

- proteins;
- fresh vegetables;
- foundations;
- canned goods;
- frozen foods;
- refrigerated foods;
- spices and seasonings;
- sauces and condiments;
- pantry/baking staples;
- equipment.

For selected items, support only useful state initially:

- Have / Don't have;
- Form: fresh, frozen, canned, cooked, dried;
- quantity;
- storage location;
- optional Use Soon flag.

Fresh ingredients should remain visually prominent because they are the main nightly variable.

### Architecture goal

The simulator must produce one structured payload that the engine consumes. The engine must not depend on Streamlit-specific state.

Suggested contract:

```json
{
  "fresh_ingredients": [
    {"name": "Chicken breast", "form": "Fresh Raw", "quantity": 2},
    {"name": "Mushrooms", "form": "Fresh", "quantity": 1}
  ],
  "pantry": [
    {"name": "Basmati rice", "quantity": 1},
    {"name": "Cornstarch", "quantity": 1}
  ],
  "condiments": [
    {"name": "Soy sauce", "quantity": 1}
  ],
  "equipment": [
    "Rice cooker",
    "Pressure cooker",
    "Four-burner stove"
  ],
  "energy": "Low",
  "budget": "Pantry Only"
}
```

The same contract must eventually accept data from the website, onboarding, pantry photographs, receipts, and other clients.

## Second New Goal: Teach the Original 250 Items

Expanding the original 250 CKB inventory items is now crucial.

Do not create hundreds of hard-coded Python KOs. Instead:

1. Define a structured teaching-data format.
2. Identify required knowledge-completeness fields.
3. Extend CKB Studio for batch import and validation.
4. Create the first curated teaching batch.
5. Load knowledge into the CKB.
6. Have runtime KOs read from CKB data.
7. Regression-test representative items before scaling.

Candidate knowledge fields:

- forms and storage;
- preparation instructions;
- methods and equipment compatibility;
- active/passive timing;
- fractional attention load and cadence;
- holdability and service timing;
- observable doneness;
- failure modes and recovery;
- flavor and sauce relationships;
- substitutions;
- cuisine opportunities;
- inventory and grocery behavior.

## Durable Decisions to Preserve

- Nightly required inputs: fresh ingredients, energy, budget.
- Cuisine, signature recipe, additional ingredients, and meal shape are optional intent.
- Energy modifies safe scheduling capacity, not physical food science.
- Household equipment and pantry should come from stored My Kitchen onboarding, not repeated nightly questions.
- Rice cooking preference: rice cooker, then pressure cooker, then honest stovetop fallback.
- A sauce name is not sauce knowledge; quantities and real instructions are required.
- Active/passive/total metrics must come from the final schedule.
- User instructions must come from the same schedule validated by the planner.
- Initial candidate display remains limited to the top 10.

## Avoid Tomorrow

- Do not start mass data entry before defining the teaching schema and validation rules.
- Do not redesign Horizons B–D because of minor feature corrections.
- Do not build Kitchen Scanner yet.
- Do not expand Chaos Kitchen.
- Do not begin broad website/API integration before the inventory payload contract is stable.

## Suggested Work Sequence

1. Run `goodmorning`; confirm clean repository.
2. Verify Horizon D regression output.
3. Consolidate final service into the realistic completion window.
4. Define inventory payload schema.
5. Build point-and-click Inventory Interface Simulator.
6. Prove payload → candidates → Have/Need → equipment → recipe.
7. Define teaching schema for the original 250.
8. Create and validate the first teaching batch.
9. Test, commit, push, make history, council minutes, and handoff.

## First Question Tomorrow

> What is the smallest inventory payload that completely describes the kitchen state needed by the Executive Chef without making the user maintain unnecessary data?
