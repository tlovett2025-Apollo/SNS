# Deployment 2: Safety and inventory contracts

Production baseline: `975478649628e2a6d74052949ea63661e2fa6f6b`

This deployment closes the second implementation package without changing the
Supabase schema. It can therefore ship as one normal API/static-site rollout.

## Release contract

- Every advertised ingredient/form route must pass 18 named KO safety gates:
  classification, form route, environment, equipment, timing, attention,
  stage, handling, operation, outcome, doneness, failure mode, recovery,
  holdability, portion model, form match, frozen handling, and raw-protein
  endpoint.
- All 140 distinct ingredient/form rows in the 11 regional sample pantries
  must resolve to a canonical inventory profile and an allowed unit.
- My Kitchen retrieves its unit choices from the server contract. The browser,
  barcode/photo capture, API persistence boundary, and recipe quantity engine
  therefore use the same rules.
- Legacy `item/items` rows migrate to the ingredient's canonical default unit.
  Unknown package weights remain unknown; they are never converted into a fake
  exact quantity.
- Weight-to-portion conversion is explicit. In particular, one pound of an
  intact piece-based protein represents four four-ounce standard portions.
- Impossible units are rejected before they enter the shared Supabase kitchen.

## Verification

Run from the repository root:

```text
python -m unittest discover
```

Expected result for this deployment: 150 tests pass. The suite includes all
140 regional pantry rows, every editable inventory contract, the 18 KO gates,
barcode normalization, Supabase save normalization, quantity conversions, and
the existing recipe/capability matrix.

After deployment, verify `/health`, open My Kitchen, and save one legacy item.
Confirm that the API and static site both report the new commit before testing
recipes.
