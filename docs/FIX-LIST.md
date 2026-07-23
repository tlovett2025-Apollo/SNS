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

## Meal structure training

### [ ] Expand beyond the three current meal structures

Build My Meal currently exposes only Cooked Together, Composed Plate, and
Layered Bowl. Define additional common home-meal shapes and their orchestration
rules before adding them to the interface; do not present untrained shapes as
working choices.

## My Kitchen organization

### [ ] Offer storage and food-type views of the same inventory

Keep storage location as the default view because it answers “where is it?” and
supports putting food away. Add a `Storage | Food type` view switch backed by
the same inventory lots and edit state. The food-type view should regroup—not
duplicate—those lots into practical cooking categories such as proteins and
eggs, vegetables, fruit, grains and starches, dairy, sauces and condiments,
spices, baking and cooking basics, and prepared foods. Preserve each item's
storage-location label in the food-type view.

Priority: UX slice after the inventory form and Build My Meal scope contracts
are stable.

### [ ] Capture thickness and dimensions for whole cuts of meat

Weight determines portions, but thickness and shape often determine cooking
time. Add optional thickness and cut dimensions to inventory lots for roasts,
steaks, chops, and other whole cuts. Dry oven roasting and grilling should use
thickness as a primary timing input; covered braises should also consider
whether the meat is whole or cut into smaller pieces. Persist these dimensions
as structured inventory data rather than free-text recipe notes.

## Flavor Bank and plan-ahead cooking

### [ ] Preserve useful extras and deliberately prepare future components

Create a future-planning system that treats useful cooking byproducts, excess
prepared ingredients, and batch-cooked components as future inventory rather
than automatic waste.

Examples:

- Rendered chicken fat and suitable roast drippings become labeled, portioned,
  frozen flavor assets such as schmaltz.
- Excess freshly prepared pineapple can be frozen in practical 1/2-cup or
  1-cup portions for smoothies, stir-fries, sauces, or later meals.
- Lemons and other ingredients commonly bought in quantities larger than one
  meal needs can be portioned or preserved for future flavor use.
- Plan Ahead Days can cook beans in batches; cook, shred, and freeze chicken
  for tacos, burritos, casseroles, pot pie, soup, or household-approved pet-food
  toppers; and prepare other reusable meal components.

Architecture requirements:

- Store the resulting item as real inventory with identity, form, quantity,
  portion size, storage location, date, safe-storage window, and intended uses.
- Keep human-food and pet-food destinations explicit and separate.
- Suggestions must be optional, practical, and based on actual excess yield;
  the cooking plan must not assume leftovers that the selected quantity will
  not produce.
- Flavor preservation belongs to reusable Knowledge Objects and inventory
  transformations, not one-off recipe wording.

Priority: Planned future capability. Do not mix into the current recipe-
instruction correction slice.
