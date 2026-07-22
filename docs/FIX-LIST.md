# Stock & Stir Fix List

## Candidate generation

### [ ] Inventory-rich kitchen produces too few meal ideas

Observed 2026-07-22: **Give Me Meal Ideas** returned only **2 recipes** from a
kitchen containing approximately **145–154 inventory items**.

Expected: build and rank a healthy pool of distinct, valid meal directions. If
only a few survive, expose which eligibility, compatibility, validation, or
deduplication gates removed the rest. Add an inventory-rich regression fixture.

Priority: High. Handle in a dedicated candidate-generation vertical slice.

## Repository housekeeping

### [ ] Remove accidental delivery artifacts and organize Python source

In one dedicated housekeeping round:

- Inventory the SNS directory and verify generated, duplicate, release, backup,
  and accidentally extracted delivery files before removing unnecessary ones.
- Preserve authoritative source, tests, data, documentation, and deployment
  inputs.
- Move root-level Python modules into intentional package directories, update
  imports and launch paths, and run the complete test suite.
- Keep this commit separate from cooking-engine behavior changes.

The user has confirmed that this directory contains build material only and
authorized deletion of files verified to be unnecessary.
