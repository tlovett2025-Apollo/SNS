# Horizon D — Heat 1: Opportunity Discovery

## Purpose

Prove that SNS can observe the resources already present in a meal candidate and discover applicable culinary opportunities before those opportunities influence ranking, planning, or instructions.

## Files changed

- `culinary_opportunities.py` — new prototype Opportunity object, rules, and discovery function.
- `recipe_engine.py` — attaches discovered opportunities to every candidate and passes them into generated recipe output.
- `app.py` — adds a developer-only Opportunity Debug expander.
- `test_culinary_opportunities.py` — proves positive discovery, negative discovery, multi-resource discovery, debug flow, and unchanged scoring.

## Explicitly unchanged

- Candidate scoring and sort order
- Cooking planner behavior
- KO activity publication
- Human cooking instructions
- CKB schema and production data
- CKB Studio

## Prototype boundary

Opportunity rules are intentionally hard-coded for this architectural proof. A later Heat will define and migrate the validated knowledge structure into the Culinary Knowledge Base.

## Suggested checkpoint

After replacing the files and running the tests successfully:

```text
gitme Horizon D Heat 1 opportunity discovery
```
