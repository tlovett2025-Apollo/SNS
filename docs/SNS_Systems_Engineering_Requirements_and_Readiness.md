# Stock & Stir — Systems Engineering Requirements and Readiness Review

Date: 2026-07-18  
Inputs: `SNS_Regional_Sample_Pantries(1).xlsx`, `RqmtText.md`, and the available Deployment 3 code snapshot.

## Executive verdict

Stock & Stir is a credible **controlled-catalog early-access candidate**, but it is not yet proven production-ready for arbitrary combinations of every catalog ingredient.

The regional pantry audit is genuinely strong:

- 507 source rows across 11 regional sample pantries
- 139 distinct ingredient names
- 140 distinct ingredient/form inventory rows
- all 139 names resolve to the current ingredient catalog
- all 139 resolve to an operational behavior family
- no food-role item is completely without a public method
- the focused pantry and capability suites pass (14/14 tests)

However, those tests prove catalog resolution and representative operability—not complete culinary knowledge or universal orchestration. The current pairwise test deliberately rotates counterparts instead of testing the full Cartesian product, and only four public strategies receive whole-recipe axis testing. A green result therefore cannot yet mean “any permitted combination is sound.”

## Master pantry artifact

`SNS_All_Regional_Pantry_Items.csv` is an import-ready union of all actual pantry rows in the workbook.

Deduplication rules:

1. Shared staples are represented once rather than multiplied by 11 regions.
2. Materially different culinary forms remain separate records.
3. Form/storage/unit conventions were identical wherever duplicates occurred.
4. The maximum observed regional quantity was retained for the selected convention.
5. Regional provenance is retained in `notes`.
6. The 25 rows on the workbook’s **Expansion Candidates** sheet are not inventory rows and are not included in the import. They belong in the training backlog.

The output has 140 rows, safely below the current 500-row browser import limit. All quantities are positive and every unit is supported by the current importer.

## Requirements derived from RqmtText

Status terms:

- **Present** — visible in the current snapshot or directly covered by a passing test.
- **Partial** — some behavior exists, but the requirement is not complete or comprehensively tested.
- **Unverified** — may exist, but the available evidence does not establish it.
- **Missing/Deferred** — explicitly absent or deferred.

### Inventory and capture

| ID | Requirement | Acceptance criterion | Status | Priority |
|---|---|---|---|---|
| INV-001 | My Kitchen is inventory-only. | No meal-building or household-preference controls are embedded in inventory management. | Partial | P1 |
| INV-002 | Show only on-hand foods as permanent rows. | Zero-quantity/unowned catalog items appear only in Add to My Kitchen. | Present/verify mobile | P1 |
| INV-003 | Use compact editable rows. | Several items fit on a phone screen; details are collapsed. | Present/verify accessibility | P1 |
| INV-004 | Provide sticky save controls. | Desktop rail and mobile bottom action remain reachable during scrolling. | Unverified | P1 |
| INV-005 | Units are ingredient-specific. | Each ingredient exposes only valid practical units and conversions. | Partial; current front-end profile list is limited | P0 |
| INV-006 | Preserve uncommon package details. | Dates, package weight, opened state, and refrigeration-after-opening survive save/load. | Partial | P1 |
| INV-007 | Organize inventory by storage and culinary subgroup. | Fresh, Fridge, Freezer, Pantry, and Spices classifications match the stated taxonomy. | Partial | P1 |
| INV-008 | Spices remain physically Pantry but have a spice inventory group. | Storage and culinary group are independent fields. | Unverified | P1 |
| INV-009 | Typo-tolerant catalog search canonicalizes aliases. | Misspellings and variants resolve without creating duplicate identities. | Partial | P0 |
| INV-010 | CSV imports are atomic and reviewable. | Invalid rows do not partially replace inventory; unresolved names require confirmation. | Partial | P0 |
| CAP-001 | Barcode capture resolves to a complete canonical record. | Result includes identity, form, storage, quantity/unit defaults, package data, and confidence—not a generic item. | Partial/unverified | P0 |
| CAP-002 | Photo capture resolves to complete canonical records. | Every suggestion is reviewable; no photo is retained; imported rows use full KO defaults. | Partial; provider 429 path observed | P0 |
| CAP-003 | Recognition failure is resilient. | Timeouts/429/5xx use bounded retry, backoff, clear status, and manual fallback. | Missing/partial | P0 |

### Household, safety, and persistence

| ID | Requirement | Acceptance criterion | Status | Priority |
|---|---|---|---|---|
| HH-001 | Household Preferences is separate from inventory. | Dedicated member/preference model and screen. | Partial/unverified | P0 |
| HH-002 | Store member appetite and default meal participation. | Portion planning uses member-level defaults. | Unverified | P0 |
| HH-003 | Support tonight-only participation, guests, appetite, and exclusions. | Overrides affect one planning session without mutating defaults. | Missing/partial | P0 |
| SAFE-001 | Allergies and medical exclusions are non-overridable in normal flow. | No recipe can be generated or reopened with a hard conflict. | Unverified | P0 |
| SAFE-002 | Household exclusions require explicit warned override. | Override is recorded with user and timestamp. | Unverified | P0 |
| SAFE-003 | Dislikes/preferences are disclosed but overridable. | Ranking and final recipe disclose an override. | Unverified | P1 |
| SYNC-001 | Inventory and preferences use the authenticated household as source of truth. | Two devices converge after save/reload; no browser-only authoritative state. | Partial; production verification required | P0 |
| SYNC-002 | Row-level security isolates households. | Cross-household reads/writes fail in automated tests. | Unverified | P0 |
| SYNC-003 | Writes are idempotent and conflict-aware. | Retries do not duplicate inventory or feedback; concurrent edits are detected or merged predictably. | Unverified | P0 |

### Planning, compatibility, grocery, and recipe lifecycle

| ID | Requirement | Acceptance criterion | Status | Priority |
|---|---|---|---|---|
| PLAN-001 | Tonight’s constraints precede ingredient selection. | Meal, effort, time, eaters, and tonight exclusions are first. | Partial | P1 |
| PLAN-002 | Owned ingredient form is shown and reused. | No redundant form question; planner receives the saved form. | Present/partial | P0 |
| PLAN-003 | Protein roles are explicit. | Equal mains, supporting, stretching, and accent roles affect quantities and timing. | Deferred by source text | P2 |
| PLAN-004 | Ingredient selectors are owned-first. | Unowned catalog is behind Need something else. | Partial | P1 |
| GROC-001 | Selecting an unowned food immediately updates a visible grocery drawer. | Quantity and state remain synchronized with recipe choices. | Partial | P1 |
| GROC-002 | Grocery decisions include substitute, omission consequence, and plan impact. | Use substitute / Buy / Omit regenerates a valid plan. | Partial | P0 |
| COMP-001 | Compatibility failures are specific and actionable. | Message identifies the component, environment/structure conflict, and valid fixes. | Partial | P0 |
| COMP-002 | Modals are reserved for safety or deliberate exclusion override. | Routine incompatibilities remain inline. | Unverified | P1 |
| RECIPE-001 | Generated recipe is production validated before display. | No fake fallback; ingredient, quantity, timing, equipment, safety, and structure checks pass. | Partial | P0 |
| RECIPE-002 | Feedback stores exact recipe snapshot and provenance. | OK/NG, categories, note, build, candidate, ingredients, plan, user, and timestamp are queryable. | Present; end-to-end retention verification recommended | P0 |
| RECIPE-003 | Favorites preserve the exact generated recipe. | Reopening never silently regenerates different instructions. | Missing/Deferred | P1 |
| RECIPE-004 | Favorites support exact replay or adaptation. | Both paths re-run current safety/exclusion checks. | Missing/Deferred | P1 |

### Navigation and application shell

| ID | Requirement | Acceptance criterion | Status | Priority |
|---|---|---|---|---|
| UX-001 | Logged-in landing page is the application home. | Welcome/article/navigation screen is not inventory or builder. | Unverified | P1 |
| UX-002 | Persistent navigation covers the specified destinations. | Desktop rail and accessible mobile menu contain all named routes. | Unverified | P1 |
| UX-003 | Featured pantry content can rotate without API redesign. | Content source supports a small curated collection. | Unverified | P2 |

### Vegetable and ingredient behavior requirements

| ID | Requirement | Acceptance criterion | Status | Priority |
|---|---|---|---|---|
| KO-001 | Every ingredient has a canonical identity and aliases. | No unresolved or duplicate identity after CSV/photo/barcode/manual entry. | Present for 139 names; global aliases incomplete until proven | P0 |
| KO-002 | Every real pantry form has distinct behavior where needed. | Fresh/canned/frozen/dry/cooked states do not share unsafe generic instructions. | Partial | P0 |
| KO-003 | Vegetables know whether they cook well alone. | Solo steps occur only when the selected outcome and method are appropriate. | Partial | P0 |
| KO-004 | Vegetables know preferred companions and vessel-entry timing. | Shared-vessel plans preserve intended texture and component identity. | Partial | P0 |
| KO-005 | Meal structure controls component identity. | Layered bowls stay distinct; cooked-together meals may intentionally merge. | Partial | P0 |
| KO-006 | Intended outcomes are explicit. | Fresh, shape-retaining, softened, browned, and sauce-like outcomes have observable stop cues. | Partial | P0 |
| KO-007 | Form-specific exceptions are modeled. | Examples such as green vs ripe tomato and whole vs sliced okra select different handling. | Partial | P0 |
| KO-008 | Okra has dedicated moisture/slime/acid/breading behavior. | Fresh/frozen and dry-heat/stew routes are intentional and tested. | Partial/unverified | P0 |

## The Full Knowledge Contract

“Ingredient exists” and “ingredient is production-ready” must be separate states. Each ingredient/form becomes launch-ready only when all applicable fields below are complete and verified.

1. **Identity** — canonical name, aliases, spelling/case normalization, category, role eligibility.
2. **Forms and state transitions** — fresh, raw, frozen, canned, cooked, dried, opened, thawed, drained, rehydrated.
3. **Storage** — valid locations, opened-state rules, shelf/refrigeration guidance where applicable.
4. **Inventory units** — allowed units, singular/plural normalization, conversions, package assumptions, practical rounding.
5. **Portion model** — main/support/accent amounts by appetite and serving count.
6. **Preparation** — washing safety, trimming, thawing, draining, cutting geometry, form-specific handling.
7. **Method routes** — each public environment that is truly supported; unsupported routes remain hidden.
8. **Equipment fit** — owned equipment, capacity, vessel depth, batch/crowding, preheat and lid requirements.
9. **Timing** — active/passive time, overlap, entry point, rest/hold window, long-wait explanation.
10. **Safety** — minimum endpoint, cross-contamination, cooling/reheating, toxin/allergen hazards where applicable.
11. **Desired outcome** — target texture, moisture, browning, shape, aroma, and component identity.
12. **Observable stop cue** — sensory cue plus temperature where relevant.
13. **Failure modes and recovery** — overcooking, dryness, water release, curdling, scorching, toughness, unsafe undercook.
14. **Structure compatibility** — cooked together, composed plate, layered bowl, handheld, soup/stew, casserole.
15. **Relationships** — preferred companions, conflicts, sequencing dependencies, excessive-quantity rules.
16. **Cuisine fit** — appropriate seasoning directions without forcing a cuisine or sauce.
17. **Sauce behavior** — whether sauce is required, optional, generated from the dish, or inappropriate.
18. **Substitution and omission** — candidates, equivalence limits, quantity conversion, consequence, and plan rewrite.
19. **Grocery semantics** — required purchase quantity and how an owned amount reduces it.
20. **Provenance and tests** — knowledge source/version, verification status, regression recipes, OK/NG feedback links.

## Coverage model: what “all the other KOs” means

Hand-authoring every possible combination is impossible and unnecessary. The robust solution is verified rules plus a coverage matrix.

For every ingredient/form, test applicable intersections of:

`role × form × method × equipment × meal structure × companion family × sauce/cuisine × time/effort × serving scale × household constraint`

Use four layers:

1. **Axis tests** — every ingredient/form against every advertised public method.
2. **Pairwise tests** — every ingredient participates in every relevant pairwise dimension; high-risk pairs are exhaustive.
3. **Curated multi-component tests** — representative three-to-ten ingredient “kitchen sink” meals by structure and equipment.
4. **Property tests** — invariants such as no raw-protein late addition, no required ingredient omitted from list, no unsupported equipment, no negative time, and no allergy override.

The current rotating pairwise test is a good CI smoke layer, but it is not the final coverage layer.

## Production gates

### Gate 0 — build and deployment integrity

- A clean checkout installs all declared dependencies and imports every production module.
- All migrations apply in order to an empty database and to a production-like prior schema.
- API and web builds identify the same release.
- `/health` proves readiness, not only process liveness.
- Deployment smoke test exercises CORS and one authenticated API request.
- Missing-module failures such as the earlier `recipe_reports` incident are impossible through manifest/import tests.

### Gate 1 — catalog and inventory integrity

- 100% of the 140 master rows import without unresolved names.
- 100% preserve form, storage, quantity, and unit after save/reload on a second device.
- No case, spacing, plural, or known alias creates a duplicate identity.
- All ingredient-specific unit lists and conversions are verified.

### Gate 2 — knowledge completeness

- Every applicable Full Knowledge Contract field is complete.
- Every advertised method route is operational; every untrained route is hidden.
- Raw proteins and other hazardous foods have verified safety endpoints.
- Every form used by the sample pantries has a route-specific audit, not only a default-family audit.

### Gate 3 — orchestration and final validation

- Full axis matrix passes for every public method, including grill, braise, oven braise, slow cooker, and pressure cooker where exposed.
- Pairwise covering array passes for roles, forms, structures, and equipment.
- High-risk combinations are exhaustive.
- Every emitted recipe passes production validation; no generic fallback can reach users.
- Sauce is selected because the meal needs it—not because a template always creates one.

### Gate 4 — safety and household policy

- Allergy/medical exclusions are impossible to override through UI or API.
- Household exclusions and preference overrides follow the defined hierarchy.
- Saved/favorite recipes revalidate against current safety state.
- RLS and cross-household isolation tests pass.

### Gate 5 — reliability and observability

- Meal ideas meet a defined warm p95 latency target and a separately disclosed cold-start target.
- Photo/barcode provider 429/timeout/5xx paths have bounded retries and graceful fallback.
- Requests have correlation IDs; failures retain build ID, route, duration, and safe diagnostic context.
- OK/NG feedback is queryable and linked to reproducible recipe snapshots.
- Backup/restore, migration rollback, and incident runbooks are tested.

## Current test evidence and limitations

- Focused regional pantry + capability suites: **14 tests passed**.
- Broader available unit discovery: **121 tests passed**; one test module could not load because FastAPI was not installed in this analysis environment. That is an environment/dependency limitation, not a failing application assertion—but a clean test environment must eliminate it before Gate 0 passes.
- Method-bearing food roles in the pantry audit: 22 proteins, 46 vegetables, 17 foundations; 54 other ingredients/spices/condiments.
- Current route-resolution counts across food roles: skillet 77, handheld 63, braise 75, soup 72, casserole 71, oven braise 72, grill 54.
- These are route counts, not quality certificates.

## System engineer’s “not done yet” list

### P0 — blocks production confidence

1. Convert the Full Knowledge Contract into stored, queryable completeness fields and a CI gate.
2. Audit all 140 ingredient/form rows, not merely 139 default identities.
3. Expand whole-recipe matrix coverage to every public method/equipment/structure and add property invariants.
4. Finish ingredient-specific units and conversions for the full catalog.
5. Prove Supabase household synchronization, RLS isolation, idempotency, and multi-device convergence.
6. Complete allergy/exclusion policy enforcement end to end.
7. Remove forced/general sauce behavior and test sauce necessity and fit.
8. Harden photo/barcode capture against 429, timeout, partial response, and uncertain identity.
9. Add clean-checkout dependency/import, migration, CORS, and authenticated smoke gates to deployment.
10. Turn OK/NG feedback into a closed loop: triage status, reproduction, regression test, fix release, and resolution.

### P1 — required for a trustworthy public experience

1. Complete Household Preferences and tonight-only overrides.
2. Complete proactive grocery/substitution decisions.
3. Finish compact/mobile inventory UX and sticky controls.
4. Build exact-recipe favorites with replay/adapt flows.
5. Complete application home/navigation and accessibility testing.
6. Define and monitor latency/error SLOs.

### Explicitly deferred

- Multiple-protein role modeling
- Rotating content system beyond an initial static article
- Meal-completion advisor

Deferral is acceptable only if the public UI does not imply those capabilities are trained.

## Recommended next execution sequence

1. Import the master CSV into a dedicated test household using **Replace**, not a personal household using Merge.
2. Generate the 140-row Full Knowledge Contract audit and make missing fields fail CI.
3. Add exhaustive axis tests and a deterministic pairwise covering array.
4. Run regional scenario packs at very low, low, and high effort across all public methods.
5. Feed every NG report into a reproducible regression fixture; sample OK reports to detect false confidence.
6. Declare early access only after Gates 0–4 pass; declare general production only after Gate 5 SLOs hold during a real tester period.

The hard standard is not “the engine can produce a recipe.” It is: **the engine either produces a safe, structurally coherent, reproducible recipe for a trained route, or clearly refuses the route before the user commits to it.**
