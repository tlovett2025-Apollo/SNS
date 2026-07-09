# Stock & Stir History — Chapter 8
## Engineering Council Minutes: Repair Build Stabilization, Pricing Split, Mobile-First Admin Design, and Git Milestone

**Project:** Stock & Stir (SNS)  
**Chapter File:** vision-8.md  
**Scope:** Durable project history extracted from the council discussion.  
**Purpose:** Preserve long-term decisions, reasoning, and expected impact for future engineers, executives, investors, and AI assistants.

---

## 1. Mission Evolution

### Decision / Idea: Stock & Stir exists to reduce the daily mental burden of deciding what to cook.
**Reasoning:**  
During this discussion, the team repeatedly returned to the idea that SNS is not merely a recipe app. Traditional recipe apps help users find recipes, but they still leave the household with the core decision burden: what can we make, with what we have, at the energy level we have today? SNS should solve the “4:00 PM problem” by converting pantry data, user constraints, and household preferences into actionable dinner decisions.

**Expected Long-Term Impact:**  
This mission statement should guide product design and marketing. Features should be judged by whether they reduce decision fatigue and make real household cooking easier. Recipe generation is a vehicle; decision relief is the product.

---

### Decision / Idea: SNS should serve real households, including low-energy users, chronic illness households, budget-conscious cooks, and people managing food inventory.
**Reasoning:**  
The discussion reinforced that SNS is being built from lived household complexity: health constraints, fatigue, money constraints, pantry realities, and imperfect cooking conditions. This gives SNS a defensible niche compared with aspirational cooking apps designed around beautiful recipes rather than usable meals.

**Expected Long-Term Impact:**  
Future features should not drift toward glossy food-media conventions at the expense of utility. SNS should remain grounded in practical, household-scale cooking.

---

## 2. Product Philosophy

### Decision / Idea: The code is not the product; the knowledge system is the product.
**Reasoning:**  
The team recognized that modern AI-assisted development makes it possible to build software scaffolding quickly, but the durable intellectual property is not the CRUD interface or generated code. The IP is the food model: ingredients, foundations, states, energy levels, substitutions, exclusions, compatibility, pantry logic, and the reasoning that makes meal recommendations feel useful.

**Expected Long-Term Impact:**  
SNS should invest heavily in the Cooking Knowledge Base (CKB). The application shell may change over time, but the structured culinary intelligence is the strategic asset.

---

### Decision / Idea: Build the smallest sellable product that solves one real problem well.
**Reasoning:**  
The team acknowledged that the complete SNS vision will take time, but an MVP may be sellable much sooner if it reliably answers “What can I make tonight?” A limited product can be valuable if expectations are framed properly, especially as a Founding Member Beta.

**Expected Long-Term Impact:**  
SNS can move to market earlier without pretending to be complete. This supports iterative validation, user feedback, and early revenue while preserving the larger roadmap.

---

### Decision / Idea: Testing and admin reliability must come before mass data entry.
**Reasoning:**  
The team paused ingredient population after discovering that admin component editing was not yet stable. Entering hundreds or thousands of ingredients into an unstable maintenance interface would create cleanup burden and corrupt confidence in the data.

**Expected Long-Term Impact:**  
Data quality depends on admin workflow quality. SNS should never scale knowledge entry faster than the tools can safely maintain that knowledge.

---

## 3. Architecture Decisions

### Decision / Idea: Lookup tables should be used for repeatable, high-value controlled vocabularies.
**Reasoning:**  
The team identified that fields with many repeatable values should not be hardcoded or left as unconstrained text forever. Examples include ingredient states, equipment types, cooking methods, foundations, categories, sauces, cuisines, energy levels, and prep forms. Lookup tables allow SNS to add values such as raw, steamed, grilled, roasted, freeze-dried, rehydrated, smoked, or sous vide without schema redesign.

**Expected Long-Term Impact:**  
Lookup-table architecture makes the CKB extensible, maintainable, and safer for nontechnical data entry. It also supports future mobile-friendly UI patterns and consistent ranking logic.

---

### Decision / Idea: High-volume selection fields should not rely on giant dropdowns.
**Reasoning:**  
The team recognized that SNS is ultimately destined for phone use. Large ingredient lists will be unusable on mobile if presented only as long dropdowns. A better pattern is search plus A–Z grouping plus common/recent items.

**Expected Long-Term Impact:**  
Mobile-first selection design will make SNS usable at scale. Ingredient selection should support quick search, alphabetical browsing, category browsing, and recently used/common-first ordering.

---

### Decision / Idea: Dropdown controls must support keyboard selection correctly.
**Reasoning:**  
A significant usability problem was observed: scrolling to “Swiss Chard” and pressing Enter selected the first item, such as “Arugula,” because the highlighted/visible item was not treated as the active selection. The expected behavior is standard keyboard interaction: arrow or scroll to an item, visibly highlight it, press Enter, and commit that item.

**Expected Long-Term Impact:**  
Efficient keyboard entry is essential for building the CKB. This matters both for internal admin speed and future power-user workflows.

---

### Decision / Idea: Component maintenance should follow one consistent CRUD pattern.
**Reasoning:**  
The team initially discovered a Foundation editor issue, then realized the root problem applied across component tables. Proteins, vegetables, foundations, ingredient states, ingredient aliases, equipment, and sauces should all support the same maintenance pattern: add, browse, select, edit, save, delete or safe-delete, and reload verification.

**Expected Long-Term Impact:**  
A consistent CRUD pattern reduces training burden, improves data quality, and prevents table-specific maintenance gaps. This became the core stabilization milestone before Ingredient Wave 1.

---

### Decision / Idea: Human-readable names should be shown instead of raw numeric IDs in normal admin screens.
**Reasoning:**  
The database must preserve IDs internally, but users do not think in terms of ingredient ID numbers. Screens showing both ingredient name and ingredient ID were judged unnecessarily cluttered. IDs may remain useful in developer/debug mode, but normal admin mode should emphasize readable labels.

**Expected Long-Term Impact:**  
Cleaner admin screens reduce data-entry errors and make SNS easier for nontechnical maintainers such as future content editors or support staff.

---

### Decision / Idea: Duplicate protection must be case-insensitive and user-practical.
**Reasoning:**  
The team observed that `Test_Foundation` and `Test_foundation` could be added as separate records. Although technically different strings, they represent the same user intent. Duplicate protection should prevent near-identical canonical records caused by capitalization or simple spelling differences where reasonable.

**Expected Long-Term Impact:**  
Cleaner canonical data improves search, aliases, recommendation logic, and user trust. Duplicate canonical objects should be prevented early rather than cleaned later.

---

### Decision / Idea: Multi-component selection is a real architectural requirement, but not a Release 1 blocker.
**Reasoning:**  
The current recipe builder uses one protein, one vegetable, and one foundation. The team recognized that real cooking often uses multiple vegetables and sometimes multiple proteins: chicken and sausage, peppers and onions, mirepoix, beef and beans, shrimp and sausage. However, redesigning the schema and candidate engine now would delay the first ingredient wave.

**Expected Long-Term Impact:**  
SNS should evolve from single-component slots to component lists. The future model should support 1..N proteins, 0..N vegetables, and optionally 0..N foundations, while preserving the current modular ingredient architecture.

---

## 4. Business Decisions

### Decision / Idea: SNS should have two product tiers: generic recipe generation and customized pantry-aware service.
**Reasoning:**  
The team defined a clear pricing split:
- Approximately **$5/month** for generic recipe generation without personal inventory.
- Approximately **$10/month** for personalized inventory management, pantry-aware meal suggestions, and related features.

This split creates an easy entry point while reserving the deeper pantry magic for the higher-value tier.

**Expected Long-Term Impact:**  
The $5 tier lowers adoption friction. The $10 tier captures users who want SNS to manage their actual household food and recommendations. This is a clean value ladder: generic help versus customized kitchen intelligence.

---

### Decision / Idea: Recommended tier language should describe benefit rather than generic “Basic/Premium.”
**Reasoning:**  
The team preferred names such as:
- **SNS Recipes** for the $5 generic tier.
- **SNS Pantry** or **SNS Pantry+** for the $10 customized tier.

The user should understand the difference instantly without reading a dense comparison table.

**Expected Long-Term Impact:**  
Benefit-based naming improves conversion and reduces support confusion. Users immediately know whether they are buying recipe ideas or pantry-aware intelligence.

---

### Decision / Idea: SNS may be sellable as a Founding Member Beta before the full vision is complete.
**Reasoning:**  
The team considered whether SNS could be sold within a very short timeframe. The conclusion was that the complete vision will not be ready, but a useful MVP could be offered if it solves the core dinner-decision problem and is framed honestly as an early beta.

**Expected Long-Term Impact:**  
This creates a path to early validation and revenue without overpromising. It also encourages a customer-feedback loop before building every planned feature.

---

### Decision / Idea: SNS is proprietary.
**Reasoning:**  
The user explicitly decided that SNS is not open source. The project should remain privately owned, with no open-source license granted. Lynsey may help sell or operate the business, but ownership is intended to remain with the user unless later changed deliberately.

**Expected Long-Term Impact:**  
All repository, licensing, and business decisions should assume proprietary software. Public release, licensing, code sharing, or transfer of ownership must be treated as deliberate legal/business decisions, not defaults.

---

## 5. User Experience Decisions

### Decision / Idea: SNS should be mobile-first even while the current build is desktop/browser-first.
**Reasoning:**  
The user identified that the final product is destined for a phone. Admin and user workflows should anticipate small screens, finger selection, and reduced tolerance for long forms or unwieldy dropdowns.

**Expected Long-Term Impact:**  
Mobile-first thinking should influence all high-volume interaction patterns, especially ingredient selection, recipe building, pantry entry, and inventory lookup.

---

### Decision / Idea: High-volume ingredient selection should support A–Z grouping.
**Reasoning:**  
For long lists like vegetables, the team liked the pattern of tapping a letter, such as C, and then seeing cauliflower, carrots, celery, cabbage, etc. This was judged friendlier on a phone than a massive dropdown.

**Expected Long-Term Impact:**  
Alphabetical grouping can become a core SNS selection pattern for ingredients, foundations, and other large lookup sets.

---

### Decision / Idea: Search + A–Z + common/recent items is the preferred future selection pattern.
**Reasoning:**  
No single navigation method will fit every user. Search helps users who know the name. A–Z helps browsing. Common/recent items speed repeated household tasks.

**Expected Long-Term Impact:**  
This selection model will reduce friction, especially during pantry setup and recipe generation.

---

### Decision / Idea: Admin tools should be simple enough for repeated data entry and future nontechnical maintainers.
**Reasoning:**  
The user’s quality engineering background led to testing from the perspective of operator fatigue, repetition, and real-world use. If a workflow is irritating after five records, it will be intolerable after 1,200.

**Expected Long-Term Impact:**  
SNS admin design should prioritize repetitive-task ergonomics. A future editor should be able to maintain the CKB without fighting the interface.

---

## 6. Marketing Ideas

### Decision / Idea: Target users of existing recipe and meal-planning apps.
**Reasoning:**  
The team concluded that SNS should target people who have already shown they want recipe help. Competitor-adjacent users have demonstrated willingness to download, subscribe, or change cooking habits. SNS marketing should answer “why switch?”

Potential target audiences include users of meal-planning, grocery-list, and recipe apps such as Mealime, Paprika, AnyList, Samsung Food/Whisk, BigOven, SideChef, Plan to Eat, and similar products.

**Expected Long-Term Impact:**  
Competitor-aware marketing can reach users already in-market rather than trying to create demand from scratch.

---

### Decision / Idea: SNS should position itself as pantry-first, energy-aware, budget-aware, and designed for real households.
**Reasoning:**  
The strongest differentiators identified were:
- Pantry-first instead of recipe-first.
- Energy-aware cooking.
- Budget-aware meal suggestions.
- Equipment-aware recommendations.
- Modular recipes.
- Inventory management.
- Freeze-dried pantry support.
- Real household practicality instead of food-photography aspirations.

**Expected Long-Term Impact:**  
These differentiators should shape ads, landing pages, onboarding, and app-store messaging.

---

### Decision / Idea: A central marketing line remains: “Stop asking ‘What’s for dinner?’ Open SNS and we’ll tell you what you can make.”
**Reasoning:**  
This phrase directly addresses the daily pain point and avoids abstract feature language. It frames SNS as decision relief rather than a recipe database.

**Expected Long-Term Impact:**  
This may become a core brand message or campaign anchor.

---

### Decision / Idea: SNS should market differently to distinct communities while keeping one core product.
**Reasoning:**  
Different groups experience the dinner problem differently:
- Busy families.
- Chronic fatigue or autoimmune households.
- Budget-conscious households.
- Freeze-drying and long-term food storage enthusiasts.
- Empty nesters.
- Seniors.
- New cooks.
- Meal preppers.

The underlying app can remain the same while messaging changes.

**Expected Long-Term Impact:**  
Segmented marketing will allow SNS to speak directly to user pain without fragmenting the product.

---

## 7. Knowledge Base Evolution

### Decision / Idea: Vegetable metadata needs future expansion.
**Reasoning:**  
The current vegetable component fields support basic testing but are not enough for long-term recommendation intelligence. Future vegetable attributes may include:
- Common cooking method.
- Raw/cooked suitability.
- Water content.
- Bitterness level.
- Softens well.
- Good roasted.
- Good steamed.
- Good in soup.
- Good in skillet.
- Strong/mild flavor.
- Child-friendly.
- Freeze-dry suitability.
- Rehydration quality.

**Expected Long-Term Impact:**  
Richer vegetable metadata will make SNS better at texture, cooking method, energy ranking, substitutions, and child/family suitability.

---

### Decision / Idea: Animal source terminology should distinguish meat type from animal source.
**Reasoning:**  
The team noted that “Beef” is meat from a cow and “Pork” is meat from a pig. If the field is called animal source, values should be animals such as cow, pig, chicken, turkey, sheep, goat, deer, rabbit, duck, goose, fish, or shellfish. If the values are beef/pork/chicken, the field should be renamed to meat type or protein type.

**Expected Long-Term Impact:**  
Accurate terminology improves data integrity and future rules, including dietary restrictions, cultural constraints, allergen handling, and animal-source logic.

---

### Decision / Idea: Sauce metadata should eventually use dropdowns and controlled values.
**Reasoning:**  
The sauce editor passed functional testing but lacked dropdowns. Sauce-related fields such as sauce family, dairy status, heat level, thickness, flavor profile, or energy level should use controlled vocabularies where practical.

**Expected Long-Term Impact:**  
Structured sauce metadata will support better flavor-system reasoning and more consistent recipe generation.

---

### Decision / Idea: Ingredient aliases should map common language to canonical ingredients.
**Reasoning:**  
The team clarified the meaning of canonical: the official internal record, not the alphabetically first term. Aliases such as hamburger, minced beef, chickpeas/garbanzo beans, scallions/green onions, and powdered sugar/confectioners sugar should point to one canonical ingredient.

**Expected Long-Term Impact:**  
Alias architecture enables flexible user input while preserving clean internal data. Users can type familiar words without fragmenting the CKB.

---

## 8. Future Features

### Decision / Idea: Multi-component recipe inputs should support real cooking combinations.
**Reasoning:**  
Many real meals use more than one vegetable or protein. Examples include fajitas, mirepoix, red beans and rice, surf and turf, soups, stews, casseroles, and skillet meals. The current 1+1+1 model is a valid Release 1 simplification, not the final meal model.

**Expected Long-Term Impact:**  
Future SNS recipe candidates should be built from component lists rather than single slots, enabling more realistic and flexible meal generation.

---

### Decision / Idea: Developer mode versus normal admin mode may be useful.
**Reasoning:**  
Raw IDs are useful for debugging but not for normal data entry. A future developer/admin toggle could show technical fields only when needed.

**Expected Long-Term Impact:**  
This would preserve debugging capability without cluttering the everyday admin interface.

---

### Decision / Idea: Techniques can be deferred as long as the system clearly marks them as deferred.
**Reasoning:**  
The team debated whether the Technique subsystem should be built before the first ingredient wave. The conclusion was that techniques feel important, but they are a smaller, more stable table than ingredients and do not need to block ingredient entry if the UI accurately says deeper technique mapping comes later.

**Expected Long-Term Impact:**  
This preserves roadmap discipline. SNS should not overbuild less urgent subsystems before the data foundation exists.

---

## 9. Naming Decisions

### Decision / Idea: The current project remains Stock & Stir, abbreviated SNS.
**Reasoning:**  
All current documents, repository work, test plans, and build references use Stock & Stir / SNS. This name now has project history and emotional momentum.

**Expected Long-Term Impact:**  
SNS should remain the technical shorthand across code, docs, tests, and internal project management.

---

### Decision / Idea: Cooking Knowledge Base remains CKB.
**Reasoning:**  
The team continues to frame the database as a knowledge base rather than merely storage. This distinction matters because the CKB contains structured culinary reasoning.

**Expected Long-Term Impact:**  
The CKB should be treated as durable intellectual property and maintained with more rigor than ordinary app data.

---

### Decision / Idea: Product tiers should likely use SNS Recipes and SNS Pantry/SNS Pantry+.
**Reasoning:**  
These names describe user benefit directly and avoid vague tier language.

**Expected Long-Term Impact:**  
Tier naming should reinforce the $5 generic versus $10 customized split.

---

## 10. Roadmap Decisions

### Decision / Idea: Repair Build 2 established “Admin CRUD Stable” as a major milestone.
**Reasoning:**  
The team reached a point where smoke tests passed and manual CRUD regression passed. The remaining issues were categorized as enhancements rather than blockers. Stable admin maintenance was required before knowledge population could begin.

**Expected Long-Term Impact:**  
This milestone marks the transition from infrastructure-building to knowledge-building.

---

### Decision / Idea: Ingredient Wave 1 should follow admin stabilization.
**Reasoning:**  
Once admin CRUD is stable, the next priority is feeding the CKB. The team identified Ingredient Wave 1 as the next major phase, likely beginning with 150–300 ingredients before scaling toward 1,200.

**Expected Long-Term Impact:**  
The product’s visible intelligence will begin to grow. Ingredient waves should be treated as knowledge releases, not mere data entry.

---

### Decision / Idea: The proposed build sequence is Admin CRUD Stabilization → Ingredient Wave 1 → Technique System → Compatibility Rules → Recipe Authoring.
**Reasoning:**  
This order prioritizes the highest-risk/highest-volume area first: ingredient data and component maintenance. Techniques matter, but the team judged them less urgent than stable data entry and initial knowledge population.

**Expected Long-Term Impact:**  
This sequence reduces rework and prevents the project from stalling on secondary subsystems before the CKB has enough substance to drive recommendations.

---

### Decision / Idea: A beta sale or Founding Member Beta may be possible soon if positioned honestly.
**Reasoning:**  
The team recognized that “sellable” does not mean “finished.” If SNS can reliably solve the dinner-decision problem for early users, it can potentially be offered as a beta product with clear expectations and feedback channels.

**Expected Long-Term Impact:**  
The business may begin learning from real users sooner than originally imagined.

---

## 11. Lessons Learned

### Decision / Idea: AI-assisted development can make software construction feel unexpectedly achievable, but product judgment remains the scarce resource.
**Reasoning:**  
The user reflected that building SNS had begun to feel surprisingly “easy.” The team distinguished code generation from product invention. A generic developer could build screens, but they would not automatically understand foundations, energy-aware cooking, pantry logic, food states, substitutions, or the lived household problem SNS solves.

**Expected Long-Term Impact:**  
SNS should preserve the human-authored reasoning behind the domain model. That reasoning is a core asset and should be documented continuously.

---

### Decision / Idea: The user’s quality engineering background is a strategic advantage.
**Reasoning:**  
The user naturally tested for operator fatigue, repetitive data-entry burden, UI confusion, and whether workflows survive real use. This led to identifying pattern-level problems such as incomplete component CRUD rather than isolated bugs.

**Expected Long-Term Impact:**  
SNS should continue using formal QA thinking: smoke tests, manual regression, repair builds, defect logs, and versioned test plans.

---

### Decision / Idea: The project crossed from “Can this be built?” to “How do we build it well?”
**Reasoning:**  
By the end of the council discussion, SNS had a working app, stable admin editor, smoke tests, regression process, documentation, Git repository, and release history. This changed the project’s emotional and technical posture.

**Expected Long-Term Impact:**  
Future work should assume SNS is a real software project, not an experiment. Planning should become increasingly product-management-oriented.

---

### Decision / Idea: Stabilization before scale prevents future pain.
**Reasoning:**  
The team avoided entering large ingredient waves until CRUD maintenance was stable. This avoided the common software trap of building on unstable foundations.

**Expected Long-Term Impact:**  
This lesson should apply to all future scaling moments: user accounts, subscriptions, inventory, recipe catalogs, mobile UI, and personalization.

---

## 12. Open Questions

### Open Question: How soon should SNS begin accepting paying beta users?
**Reasoning:**  
The team believes something may be sellable soon, but the exact threshold remains unresolved. Required business infrastructure may include onboarding, feedback/reporting, privacy policy, terms of use, payment flow, and support expectations.

**Expected Long-Term Impact:**  
The answer will shape whether the first launch is a free beta, paid beta, founding member program, or limited private pilot.

---

### Open Question: When should multi-component recipe architecture be implemented?
**Reasoning:**  
The need is real, but not urgent enough to block Ingredient Wave 1. The timing should depend on how soon the 1+1+1 model limits real user value.

**Expected Long-Term Impact:**  
This will eventually affect schema, UI, recipe candidate generation, ranking, and shopping list logic.

---

### Open Question: How deeply should Technique architecture be modeled?
**Reasoning:**  
Techniques were deferred, but the future system will need to know cooking methods, equipment, energy cost, active/passive time, and method compatibility. The team has not yet decided how granular this should be.

**Expected Long-Term Impact:**  
Technique modeling will influence recipe generation quality, energy-aware recommendations, equipment filtering, and instruction generation.

---

### Open Question: What is the minimum legal/business setup before selling?
**Reasoning:**  
The user decided SNS is proprietary, but payment collection, terms, privacy, support, and ownership structure may still require deliberate planning.

**Expected Long-Term Impact:**  
This will affect launch risk, brand trust, and operational readiness.

---

### Open Question: How should milestone databases be preserved?
**Reasoning:**  
The team decided the working database does not need to live in Git, but milestone database snapshots may be worth preserving outside normal source control or in controlled release folders.

**Expected Long-Term Impact:**  
Database snapshot strategy will become important as the CKB grows and data loss becomes more costly.

---

## 13. Durable Council Record

This council session marked a major transition in Stock & Stir’s evolution.

Before this chapter, much of the effort centered on whether the application could function. During this chapter, the team stabilized admin CRUD, validated the repair build, formalized pricing tiers, clarified proprietary ownership, identified mobile-first lookup requirements, and prepared to begin serious CKB population.

The most important durable conclusion is that SNS is not simply an app that stores recipes. It is a structured cooking knowledge system designed to reduce decision fatigue for real households. The next phase is not merely “entering ingredients.” It is teaching Stock & Stir the language of food.
