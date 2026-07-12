# CKB Comprehensive Training Corpus

This folder contains two deliberately different sets of files.

## `next_import` — use these with the current trained CKB

Load these four files through CKB Studio in numerical order:

1. `Wave010_IngredientForms_Remaining.csv` — 420 rows
2. `Wave011_IngredientStates_Remaining.csv` — 303 rows
3. `Wave012_KOProfiles_Remaining.csv` — 124 rows
4. `Wave013_KOActivities_Remaining.csv` — 516 rows

For each file: select its matching Import Type, Browse, Validate, review the
preview, and Import only after validation succeeds. CKB Studio creates a backup
before every import.

These files exclude the knowledge already loaded through Waves 005–009.

## `master` — canonical recovery/reference corpus

The master files contain the complete corpus, including the first training set:

- 432 ingredient Forms
- 306 ingredient states
- 129 selectable KO profiles
- 539 KO activities
- 8 audited alpha-gal safety corrections

Do not import the master files into the current CKB: strict validation will
correctly report existing rows. They exist for review, version control, recovery,
and rebuilding a new CKB from a clean catalog.

## Coverage

All 251 active catalog ingredients receive purchasable Form knowledge. Supporting
ingredients such as dairy, fruit, spices, oils, sauces, and herbs receive truthful
state knowledge without pretending to be standalone meal components. Verified
proteins, vegetables, and foundations receive complete KO profiles and cooking
activities with named vessels/equipment.
