\# Stock \& Stir Change Log

# Stock & Stir (SNS)

## v5 Beta 2D - Repair Build 2

### Milestone
- Admin CRUD subsystem stabilized.
- Repair Build 2 passed all regression tests.
- Smoke test passed.
- Project placed under Git version control.
- Repository structure established.
- Ready to begin Ingredient Wave 1.

### Known Enhancements
- Multi-ingredient recipe support.
- Hide ingredient IDs in admin screens.
- Sauce editor lookup dropdowns.
- Expand vegetable metadata.

\## ADDED 2026-06-29 — Build v000.1

\## Milestone
\The first end-to-end data flow was successfully demonstrated.

\Ingredient entered:
\Chicken
\Ingredient promoted to Protein.
\Build Dinner correctly discovered Chicken through the normalized schema.
\This is the first successful execution of the Stock & Stir data model.

\### Added 20260929-1200
\- Created new SNS project structure.
\- Added initial Streamlit app.
\- Added SQLite schema creation.
\- Added starter seed data.
\- Added ingredient/component entry screens.
\- Added first simple Build Dinner screen.


\### Project Decision

SNS replaces the old WFD recipe-first approach.

\### Reason

The product is a dinner decision engine, not a recipe database.

\### Known Issues
\- Decision engine is placeholder only.
\- Grocery list is placeholder only.
\- No edit/delete screens yet.


## 2026-07-02 — Architectural Decision (Pending Beta 2C Approval)

### Decision
Prep Minutes and Cook Minutes no longer belong to Ingredient State.

### Reason
Preparation and cooking time depend on the cooking Technique, not the state of the ingredient.
A single ingredient state (for example, Raw Chicken Breast) may be grilled, pan fried,
air fried, baked, or sous vide, each with different timings.

### Impact
- Ingredient State references a Default Technique.
- Technique will own Prep Minutes and Cook Minutes.
- Recipe generation derives timing from Technique.
