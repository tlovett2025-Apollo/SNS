# Stock & Stir Engineering Council Minutes

**Meeting date:** July 11, 2026  
**Record type:** Permanent architectural, product, and strategy history  
**Milestone:** Horizon D — Executive Chef Loop Closure

## Executive Finding

Stock & Stir is now formally understood as a **Culinary Decision Engine**, not a recipe application. During Horizon D, the Council proved the first complete decision loop: observe the kitchen, identify meal opportunities, apply ingredient and culinary knowledge, choose equipment, recognize inventory gaps, consolidate work into human kitchen activities, schedule around equipment and attention, and produce an actionable recipe.

This milestone does not mean the system knows every ingredient, sauce, appliance, or cuisine. It means the architecture now knows **how to think from kitchen state through dinner**. The next program is therefore education at scale rather than continued reinvention of the brain.

---

## Mission

### Decision / Idea

Stock & Stir exists to help ordinary people turn the food and equipment already available in their homes into affordable, nourishing, achievable meals. Its central value is not access to recipes; it is access to the judgment of an experienced executive chef who understands the household's kitchen, constraints, energy, and opportunities.

### Reasoning

Experienced cooks do not begin with a fixed recipe. They observe resources and recognize possibilities: mushrooms create a browning opportunity; leftover chicken creates a quick-meal opportunity; oatmeal may create an economy opportunity. Users need this judgment more than another library of instructions.

### Expected long-term impact

SNS can serve people who are tired, budget-constrained, inexperienced, food-insecure, or simply overwhelmed by the daily dinner decision. Product development, marketing, and knowledge acquisition should be judged by whether they improve the executive chef's understanding of the kitchen and its people.

---

## Product Philosophy

### 1. The product begins with resources, not recipes

**Decision / Idea:** Meals are generated from kitchen state and user intent rather than retrieved as static recipes.

**Reasoning:** The same ingredients produce different opportunities depending on time, equipment, forms, energy, preferences, and desired cuisine. A recipe-first model hides these relationships and forces the user to adapt to the recipe.

**Expected long-term impact:** SNS remains modular, pantry-aware, and capable of creating appropriate meals from changing household conditions.

### 2. Simplicity at the surface requires intelligence underneath

**Decision / Idea:** Nightly required input should remain limited to fresh ingredients, current energy, and budget. Cuisine, signature recipes, additional ingredients, and meal shape are optional intent that regenerates the candidate list.

**Reasoning:** A well-configured household profile already knows equipment, pantry, freezer, refrigerator, spices, restrictions, preferences, skill, and household size. Repeated interrogation creates fatigue and defeats the product's purpose.

**Expected long-term impact:** The UX can remain calm and accessible while the engine performs sophisticated decisions using stored context.

### 3. Energy is an operating constraint

**Decision / Idea:** Energy must alter safe human-attention capacity and planning behavior, not merely candidate ranking.

**Reasoning:** Cooking duration and human effort are different. Chicken may occupy a pan for twelve minutes while requiring only brief periodic checks. At low energy, fewer overlapping checks are safe; at extremely low energy, SNS should favor assembly, reheating, dump-and-start methods, fewer pans, and equipment-assisted cooking.

**Expected long-term impact:** SNS can create genuinely achievable plans for disabled, ill, exhausted, or overwhelmed users rather than presenting nominally easy recipes that exceed their functional capacity.

### 4. Honest feasibility over wishful planning

**Decision / Idea:** Time and equipment feasibility must be evaluated before presenting an opportunity as practical.

**Reasoning:** At 4:00 p.m., a crockpot opportunity for an imminent dinner no longer exists. A rice meal behaves differently with a rice cooker, pressure cooker, three-burner stove, or two-burner stove. The ingredients may be unchanged while the opportunity changes.

**Expected long-term impact:** SNS will protect user trust by refusing or downgrading impossible plans and offering equipment-appropriate alternatives.

---

## Architecture Decisions

### 1. Separation of intelligence by ownership

**Decision / Idea:** SNS uses distinct layers with single responsibilities:

- **Executive Chef / Opportunity Engine:** observes resources and identifies what is possible or advantageous.
- **Cooking Knowledge Base:** stores durable culinary facts and relationships.
- **Knowledge Objects:** own ingredient-specific self-knowledge.
- **Sauce and flavor knowledge:** owns requirements, quantities, preparation, and finishing logic for flavor systems.
- **Equipment Profiles:** own appliance-specific phases, capacity, timing, and attention behavior.
- **Equipment Manager:** selects the best available execution method.
- **Activity Consolidator:** translates ingredient activities into work a cook actually performs.
- **Planner:** schedules the resulting work against equipment and human-attention capacity.
- **Instruction renderer:** prints the actual scheduled plan rather than constructing a separate fictional recipe.

**Reasoning:** Menu judgment, ingredient behavior, equipment behavior, and scheduling logic are different forms of knowledge. Mixing them produces duplication, brittle rules, and contradictions.

**Expected long-term impact:** Each layer can be educated, tested, expanded, and replaced independently without destabilizing the whole system.

### 2. Activity Consolidation

**Decision / Idea:** KOs may publish ingredient activities, but the planner must consume consolidated **kitchen activities**.

**Reasoning:** A cook does not experience five isolated ingredient-prep timelines. The cook gathers, launches long-lead work, completes mise en place, manages cooking windows, finishes sauce, and plates. Ingredient-level scheduling produced inflated time and unnatural instructions.

**Expected long-term impact:** Plans become shorter, calmer, more realistic, and easier to teach.

### 3. Launch prep before general mise en place

**Decision / Idea:** Long-lead components are prepared and started before general prep; remaining mise en place occurs during passive cooking.

**Reasoning:** Rice, baked potatoes, casseroles, roasts, and other long processes determine dinner completion time. Preparing everything before starting them wastes the most valuable overlap window.

**Expected long-term impact:** Required lead time is reduced without increasing human effort.

### 4. Attention is fractional, not Boolean

**Decision / Idea:** Activities require an attention load or cadence rather than a simple `busy/not busy` designation.

**Reasoning:** Equipment may be occupied continuously while the cook uses only seconds per minute to check or turn food. Treating the entire cooking window as exclusive human labor falsely serialized the kitchen.

**Expected long-term impact:** SNS can interleave safe activities, scale concurrency by energy, and identify the human—not merely the burner—as a constrained resource.

### 5. Equipment changes the activity graph

**Decision / Idea:** Equipment selection is upstream of scheduling and may replace the activity graph.

**Reasoning:** Rice cooker, pressure cooker, and stovetop rice are not identical activities assigned to different labels. A pressure cooker includes loading, pressurization, pressure cooking, and natural release. A rice cooker provides off-burner passive cooking. Stovetop rice occupies a burner and adds monitoring load.

**Expected long-term impact:** Equipment becomes a genuine planning input, allowing honest comparison of time, attention, and capacity.

### 6. Burner capacity includes type and mental penalty

**Decision / Idea:** Future stove profiles should record burner count, size/output, cookware fit, accessibility, and attention cost.

**Reasoning:** Third and fourth burners may be smaller or lower-output, but no universal 65% rule applies. A small rear burner may suit simmering rice, yet the pot still occupies capacity and remains mentally monitored.

**Expected long-term impact:** SNS will model actual household kitchens rather than an abstract number of identical burners.

### 7. Inventory is a formal engine contract

**Decision / Idea:** UX surfaces provide a structured kitchen payload; the decision engine remains independent of whether data came from Streamlit, a website, onboarding, a receipt, or an image scanner.

**Reasoning:** The system needs a stable interface between user experience and culinary intelligence. UI redesign should not require rewriting the cooking engine.

**Expected long-term impact:** Multiple input methods can coexist and evolve while preserving one source of engine truth.

---

## Business Decisions

### One paid product

**Decision / Idea:** Stock & Stir will be one complete paid product, targeted at approximately $10 per month or $100 per year, rather than maintaining a pantry-free edition and multiple artificial tiers.

**Reasoning:** Household memory and inventory are not premium decorations. Without them, the executive chef is blind. Maintaining separate reduced products would consume development and support resources while weakening the central value.

**Expected long-term impact:** Simpler product positioning, simpler engineering, clearer customer value, and focus on acquiring committed users rather than supporting a large nonpaying population.

### Value proposition

**Decision / Idea:** Position SNS as renting an executive chef for roughly twenty-seven cents per day.

**Reasoning:** Customers are not paying for recipes. They are paying for daily decision-making based on their food, equipment, energy, budget, and preferences.

**Expected long-term impact:** Marketing can communicate differentiated value without competing against free recipe sites.

---

## User Experience Decisions

### 1. My Kitchen onboarding

**Decision / Idea:** First-use configuration should teach SNS the household through organized tabs: equipment, pantry, freezer, refrigerator, spices, diet, preferences, skill, and household size.

**Reasoning:** Asking once during onboarding is fundamentally different from asking the same questions every evening.

**Expected long-term impact:** Personalized decisions with minimal nightly cognitive burden.

### 2. Point-and-click inventory simulator

**Decision / Idea:** The next interface should simulate the future UX-to-engine inventory contract using point-and-click selection from known items.

**Reasoning:** Before the website is complete, the team needs proof that structured inventory, fresh ingredients, equipment, energy, and budget can flow into the engine and change opportunities, grocery gaps, and timelines.

**Expected long-term impact:** A reusable contract for the future website, mobile interface, onboarding, pantry scanner, and testing harness.

### 3. Have/Need clarity

**Decision / Idea:** Optional intent may reveal near-match meals. When a user chooses “Make this recipe,” SNS must distinguish items already available from missing items and produce a grocery list containing only the gaps.

**Reasoning:** Users should never be told to buy food already in their kitchen, nor should the system pretend a cuisine can be produced without its required flavor ingredients.

**Expected long-term impact:** Greater trust, reduced waste, and a direct bridge from decision to shopping.

### 4. Actual schedule as the recipe

**Decision / Idea:** User-facing instructions must be rendered from the final activity schedule.

**Reasoning:** Earlier systems generated one timeline for debugging and a different generic recipe for users, causing contradictions. The cook should see the same execution the planner validated.

**Expected long-term impact:** Internally consistent timing, equipment, attention, sauce, and service instructions.

---

## Knowledge Base Evolution

### Ingredient KOs became actionable culinary teachers

**Decision / Idea:** KOs must own preparation, observable cooking gates, attention load, holdability, failure modes, recovery guidance, and service behavior—not merely ingredient names and durations.

**Reasoning:** “Sauté mushrooms for six minutes” is inferior to knowledge that mushrooms should be placed in an uncrowded layer, left undisturbed until moisture evaporates and the bottom browns, then turned and browned further.

**Expected long-term impact:** Instructions build cooking confidence and remain useful across meal shapes.

### Proof ingredient knowledge captured

The Horizon D regression established detailed knowledge for chicken breast, mushrooms, asparagus, Swiss chard, and rice. Important durable examples include:

- Mushrooms: quick cleaning without soaking; trim only dry stem ends; slice approximately 1/4 inch; brown uncrowded and undisturbed; season after browning.
- Swiss chard: stems are edible; separate stems and leaves; cook stems first; add leaves later with a small amount of liquid; finish with salt and acid; serve promptly.
- Asparagus: trim woody ends; whole or bite-size; sauté and optionally steam briefly; finish bright green and crisp-tender.
- Chicken breast: remove membrane and desired fat; do not rinse raw chicken; even thickness; season; brown; check periodically; verify 165°F; rest before slicing.
- Rice: long-lead foundation; launch before general prep; equipment-specific execution.

### Sauce KOs

**Decision / Idea:** Sauce names are insufficient. Sauce knowledge must include ingredients, quantities, substitutions, preparation, cooking, thickening, timing, equipment, inventory requirements, and finishing judgment.

**Reasoning:** “Measure and mix simple stir-fry sauce” is circular and unusable unless the system knows what the sauce is.

**Expected long-term impact:** Cuisine selection becomes a real culinary transformation rather than a label.

### Teaching the original 250 items

**Decision / Idea:** Expanding the original 250 inventory items is a critical next program. Knowledge should be loaded through a structured, validated CKB teaching format rather than manually encoded as hundreds of Python objects.

**Reasoning:** The architecture is proven; breadth now depends on disciplined data acquisition. Manual object creation will not scale and will make corrections difficult.

**Expected long-term impact:** Batch education, CKB Studio import, consistent validation, and gradual replacement of prototype hard-coded profiles with database-owned knowledge.

---

## Future Features

### Kitchen Scanner

**Decision / Idea:** Use photographs of pantry shelves, refrigerator, freezer, spice cabinet, stove, and counter to accelerate onboarding. Users review and correct recognized items before acceptance.

**Reasoning:** Manual entry of hundreds of kitchen items is a major adoption barrier.

**Expected long-term impact:** Faster onboarding and more complete kitchen knowledge.

### Receipt-based inventory updates

**Decision / Idea:** Future receipt capture may add purchased inventory; simple decrement actions can record use.

**Reasoning:** Inventory loses value if maintaining it requires excessive labor.

**Expected long-term impact:** More accurate household state and better recurring recommendations.

### Missing Opportunity reports

**Decision / Idea:** The Opportunity Engine should eventually identify which inexpensive pantry additions unlock the greatest number or quality of meals.

**Reasoning:** Helping households build flexible pantries creates durable food security rather than solving only tonight's dinner.

**Expected long-term impact:** Pantry-development guidance, budget-aware shopping, and a distinctive long-term customer benefit.

---

## Naming Decisions

- **Stock & Stir:** the single product.
- **CKB / Cooking Knowledge Base:** durable culinary knowledge store.
- **KO / Knowledge Object:** ingredient-specific knowledge owner.
- **Executive Chef / Opportunity Engine:** observes the kitchen and recognizes possibilities.
- **Activity Consolidator:** converts ingredient activities into human kitchen work.
- **Equipment Manager:** selects and applies equipment-owned execution graphs.
- **Equipment Profile:** appliance-specific timing, capacity, and behavior.
- **Sauce KO:** structured sauce requirements and behavior.
- **My Kitchen:** unified household configuration and inventory concept.
- **Kitchen Scanner:** future image-assisted onboarding capability.
- **Forms:** ingredient condition/form terminology.

---

## Roadmap Decisions

### Horizon B

Ingredient self-knowledge: what each component knows about itself.

### Horizon C

Orchestration: how the planner coordinates knowledgeable components.

### Horizon D

Executive Chef loop: observe opportunities and carry the selected meal through equipment, inventory, flavor, consolidated activities, attention-aware planning, and usable instructions.

### Horizon D close condition

The regression meal demonstrated the complete loop with opportunity discovery, detailed ingredient knowledge, equipment selection, a real sauce object, Have/Need resolution, attention-aware lanes, schedule-derived metrics, and recipe rendering from the actual schedule.

### Next program: teaching and interface simulation

After minor Horizon D service consolidation, work moves to:

1. Point-and-click inventory simulator.
2. Stable UX-to-engine kitchen payload.
3. Expansion of the original 250 inventory items.
4. Structured teaching format and validation.
5. CKB Studio batch import.
6. Representative regression testing before broad loading.

---

## Lessons Learned

### 1. Apparent planner failures often reveal missing semantic layers

Ingredient-level activity scheduling initially appeared to be a timing problem. The deeper issue was that cooks perform kitchen activities, not ingredient activities. Adding more planner rules would have hidden the missing consolidation layer.

### 2. Debug views can reveal architecture only when ownership is visible

Separating raw KO activities from consolidated Kitchen Lanes made it possible to see whether knowledge, consolidation, or scheduling was wrong.

### 3. Percent utilization can hide sequencing failures

Two burners may each show reasonable total utilization while one sits idle early and the human lane becomes the real bottleneck. Minute-by-minute lane drawings are therefore a valuable design and validation tool.

### 4. Binary attention produces false serialization

Treating a twelve-minute chicken cook as twelve minutes of exclusive human labor created unrealistic schedules. Equipment occupancy and human attention must be modeled separately.

### 5. A capability is not integrated until the UX supplies its data

Backend recognition of a rice cooker did not affect the application until household equipment actually flowed into candidate generation. Presence of a function is not proof of end-to-end behavior.

### 6. Labels are not knowledge

Naming “simple stir-fry sauce” did not create a sauce. Complete knowledge requires ingredients, quantities, process, inventory implications, and cooking behavior.

### 7. Service is also an activity-consolidation problem

Separate plate-sides, wait, slice, and serve steps can overstate completion time. The final service sequence should eventually consolidate into the smallest realistic action window.

### 8. The project did not change direction; it discovered its direction

The early recipe engine was necessary scaffolding. Removing assumptions revealed the Culinary Decision Engine already implicit in the original vision.

---

## Open Questions

1. What final CKB schema should represent ingredient activities, attention cadence, observable gates, equipment compatibility, failure modes, and recovery?
2. How should energy levels scale safe concurrent attention without falsely changing physical cook time?
3. How should the planner represent brief distributed checks rather than concentrating attention at the beginning of an activity window?
4. How should service activities be consolidated so a functionally complete meal is not extended by artificial sequential plating steps?
5. What burner attributes are needed beyond count: output class, diameter, position, accessibility, cookware interference, or simmer stability?
6. Which pantry staples may ever be assumed available, and which must always be verified?
7. How should quantities and consumption update inventory after a recipe is made?
8. What minimum knowledge completeness is required before one of the original 250 items is considered production-ready?
9. How should near-match meals be ranked when they require purchases?
10. How should sauce and flavor KOs scale quantities by servings and support substitutions?

---

## Closing Record

Horizon D established that Stock & Stir can think from opportunity through dinner. The Council accepts the Executive Chef loop as architecturally proven. Remaining corrections are feature refinement and education, not evidence that the central design is missing.

The next era begins with a stable kitchen-data contract and disciplined teaching of the CKB.
