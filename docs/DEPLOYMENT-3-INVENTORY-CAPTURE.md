# Deployment 3 · Reviewed inventory capture

This release adds phone-first barcode and pantry-photo entry to My Kitchen.
Both routes create an editable draft. Nothing enters the signed-in household's
Supabase kitchen until the cook checks the rows and selects **Add selected to
My Kitchen**.

## Render setting

Add `OPENAI_API_KEY` as a secret environment variable on `sns-api`. The
Blueprint declares the variable with `sync: false`, so the secret is never
committed to Git. `SNS_PANTRY_VISION_MODEL` defaults to `gpt-5-mini` and may be
changed without a code release.

The API still starts safely when the key is absent. Barcode entry continues to
work, and photo entry gives a friendly configuration message instead of
changing the pantry.

## Data boundaries

- Barcode and photo endpoints require a signed-in Supabase session.
- The user JWT reads only that household's current kitchen through RLS.
- Photos are resized in the browser, sent with OpenAI response storage
  disabled, and are not written to Supabase or the SNS filesystem.
- Recognition results are matched against the versioned SNS ingredient and
  alias catalog, deduplicated, and returned as review rows.
- Only confirmed rows use the existing `sync_my_kitchen` RPC.
- No Supabase migration is required for this deployment.

## Smoke test after Render finishes

1. Sign in on a phone and open **My Kitchen**.
2. Scan a grocery barcode, review the draft, and add it.
3. Refresh on another signed-in device and confirm the item appears once.
4. Photograph a small pantry shelf, edit one draft row, leave one unchecked,
   and add the selected rows.
5. Refresh and confirm only the selected rows were saved.
6. Deny camera permission once and confirm manual barcode entry remains usable.

## Automated verification

Run from the repository root:

```text
python -m pytest -q test_*.py
```

Expected result for this release: 216 tests and 730 subtests passed. The single
Starlette/httpx compatibility warning is pre-existing and non-failing.
