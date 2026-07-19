# Deployment 3: combination matrix and mandatory release gates

Production baseline: `bf689e0` (`Harden pantry quantity form and safety contracts`)

## What this deployment closes

- Whole-kitchen replacement is idempotent when aliases collapse to the same
  canonical ingredient. The API and Supabase independently coalesce equal
  inventory states before insert.
- The public launch catalog is exercised through a deterministic pairwise
  orchestration matrix rather than a small set of happy-path recipes.
- High-risk boundaries explicitly cover frozen raw protein, canned protein and
  vegetables, dry casserole foundations, raw poultry, fish, grill equipment,
  one serving, seven servings, and twelve servings.
- Fresh sausage, kielbasa, and shrimp no longer receive conditional thawing
  chatter in grill instructions.
- Every Render build runs the release gates after dependency installation.
  A failing gate prevents the new deployment from becoming live.
- GitHub Actions runs the same gates on every pull request and every push to
  `main`, and retains the machine-readable JSON report as a build artifact.

## Release command

Run from the repository root:

```text
python tools/run_release_gates.py
```

The command writes `test-results/release-gate-report.json` and exits nonzero
when any gate fails. A quick matrix-only diagnostic is also available:

```text
python tools/run_release_gates.py --matrix-only
```

## Passing baseline

The completed implementation passes:

- 139 launch-catalog knowledge cases;
- 251 pairwise recipe-orchestration cases;
- 5 named boundary/high-risk recipes; and
- 155 automated unit/integration/contract tests.

Total: **550 passing cases, zero failures**.

## Manual acceptance after rollout

1. Open `/health` and confirm `status` is `ok`.
2. Import the 140-row combined pantry and save it twice. Both saves must
   succeed; the second save must not add duplicate rows.
3. Put `ribeye` and `Ribeye steak` in one import with the same form, storage,
   and unit. Confirm My Kitchen shows one canonical row with the summed amount.
4. Sign in on desktop and phone with the same account. Confirm both devices
   display the same saved kitchen after refresh.
5. Generate the five boundary recipes represented in `BOUNDARY_CASES` in
   `release_matrix.py`, then mark each recipe **OK** or **NG** in Recipe Review.
6. Generate any additional recipes that interest you. OK reports are useful:
   they establish which combinations were reviewed and found acceptable, while
   NG reports identify the exact recipe/build for engineering review.

## Remaining human gate

The automated matrix proves that trained routes open, respect safety and form
contracts, assign every selected ingredient a job, and survive final recipe
validation. It cannot prove taste or desirability. The planned 5–7 day soak,
with OK/NG recipe feedback, remains the final human acceptance gate.

