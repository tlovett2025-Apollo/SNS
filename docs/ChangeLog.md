\# Stock \& Stir Change Log

\## ADDED 2026-06-30 - Build V000.2-4
\ V000.2&3 added updates to teh meal type attribute. Upon further design, the 
\ Mealtype catagory was removed.  A new build that is more user focused is included 
\ in v000.4.  
\ Version 4 transforms Stock & Stir from a recipe prototype into a trainable 
\ culinary knowledge engine.
\
\Not prettier.
\
\Not fancier.
\
\Smarter.
\
\It becomes easier to teach, easier to maintain, and more capable of making decisions for the \user instead of asking the user to make decisions for it.
\
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

## 2026-07-06

### Major Architecture Milestone

- Renamed the primary database to the Cooking Knowledge Base (CKB).
- Established the CKB as a first-class platform component rather than an implementation detail.
- Created the first version of CKB Studio (formerly DBPop) to safely import and validate knowledge into the CKB.
- Added long-term metadata fields to the ingredients schema to support validation, QA, and future expansion.
- Successfully imported the first production ingredient wave into the CKB using CKB Studio.