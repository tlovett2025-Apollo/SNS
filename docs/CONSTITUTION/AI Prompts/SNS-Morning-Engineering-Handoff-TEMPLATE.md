# SNS Morning Engineering Handoff Template

> Use this document at the end of an SNS engineering session. Replace every bracketed field. Remove sections that truly do not apply. The objective is to let a new engineering chat understand the project, request the correct files, and begin safely without reconstructing the prior day from scratch.

---

# STOP — Read Before Coding

Do not write code immediately.

First understand:

1. What Horizon or program is active?
2. What was proven today?
3. What remains unresolved?
4. Which responsibilities belong to the CKB, Knowledge Objects, planner, UI, and database?
5. What files are actually required for the next change?

The fastest way to waste a session is to solve yesterday’s problem after the architecture has moved.

---

# Good Morning

- Coffee
- Power drink
- Water
- Run `goodmorning`

---

# Session Identification

- **Handoff date:** [YYYY-MM-DD]
- **Prepared after session:** [YYYY-MM-DD]
- **Repository:** [repository/path]
- **Branch:** [branch]
- **Current build/version:** [build]
- **Last commit:** [commit hash and message]
- **Working tree at shutdown:** [clean / describe expected changes]
- **Current Horizon or program:** [Horizon C / Release / Launch / etc.]
- **Current Heat or major change:** [name]

---

# Current Mission

[One concise paragraph stating what the active engineering work is intended to accomplish and why it is currently the highest-value work.]

---

# Product Mission Reminder

Stock & Stir exists to help ordinary people confidently prepare affordable, nourishing meals from food they already have.

SNS is not merely a recipe application. It is a cooking knowledge and decision engine intended to reduce dinner anxiety, cognitive load, waste, and kitchen failure.

---

# Current Product Direction

- **Current edition/release target:** [Pantry Edition / other]
- **Primary users:** [food-insecure households, low-energy users, beginners, ordinary families, etc.]
- **Current business boundary:** [Free / Basic / Premium implications]
- **Relevant product rule:** [example: Premium begins when SNS remembers the household.]

---

# Durable Decisions From This Session

Record only decisions that should still matter years from now.

## Architecture

- [Decision]
- [Reason]
- [Consequence]

## Product / UX

- [Decision]
- [Reason]
- [Consequence]

## Terminology

- [Official term and what it means]

## Deferred but Preserved

- [Backlog item]
- [Why it matters]
- [Why it was deferred]

---

# What Was Completed

## Completed capabilities

- [Capability]
- [Capability]

## Tests actually run

- [Command]
- [Result]

Do not state that tests passed unless they were executed.

## Git checkpoint

- [Commit]
- [Push status]
- [Working-tree status]

---

# Current Behavior

Describe what the system does now in concrete terms.

Example:

```text
User selects:
Protein + Protein State + Vegetables + Foundation + constraints

Candidate Engine:
Ranks meal shapes

Knowledge Objects:
Publish state-aware activities

Planner:
Builds dependencies and kitchen lanes

UI:
Displays recipe instructions and developer diagnostics
```

Include one representative output when useful.

---

# Current Architecture Map

## Runtime and data flow

```text
CKB / SQLite database
        ↓
database.py / schema.py / seed.py
        ↓
ingredient_profiles.py and other Knowledge Object layers
        ↓
recipe_engine.py
        ↓
cooking_planner.py
        ↓
app.py
```

## Primary Python files

### `app.py`
**Responsibility:** Streamlit user interface and developer diagnostic presentation.

**May contain:**
- inputs
- candidate selection
- state selectors
- display formatting
- debug expanders

**Must not become:**
- permanent cooking-knowledge storage
- timeline reasoning engine
- ingredient behavior repository

### `recipe_engine.py`
**Responsibility:** Candidate generation, ranking, candidate assembly, and recipe-result construction.

**May contain:**
- meal-shape strategies
- ranking rules
- candidate metadata
- calls into KOs and planner

**Must not become:**
- permanent ingredient cooking knowledge
- detailed scheduling engine

### `cooking_planner.py`
**Responsibility:** Orchestration.

**May contain:**
- activity dependency handling
- activity graph construction
- kitchen-lane assignment
- human-attention constraints
- meal-level sequencing
- timeline rendering

**Must not invent:**
- ingredient-specific cooking facts
- ingredient-specific valid states or techniques

### `ingredient_profiles.py`
**Responsibility:** Prototype Knowledge Object behavior until knowledge moves into the CKB.

**May contain:**
- ingredient states
- state-specific activities
- desired outcomes
- fallback profiles
- KO activity publication

**Long-term direction:** Cooking knowledge moves into the CKB; Python remains the reasoning and orchestration layer.

### `database.py`
**Responsibility:** Database access helpers and safe persistence operations.

### `schema.py`
**Responsibility:** SQLite schema creation and evolution.

### `seed.py`
**Responsibility:** Initial and controlled seed loading.

### `ckb_studio.py`
**Responsibility:** Administrative CKB import, validation, backup, and maintenance tools.

### Tests
**Responsibility:** Prove architectural ownership and prevent regression.

Examples:
- `test_ko_activities.py`
- smoke-test scripts
- schema/data-integrity tests

---

# Data Architecture

## Runtime source of truth

The runtime source of truth is the **CKB SQLite database**, currently:

```text
data/ckb_seed_001.db
```

## Spreadsheet role

Spreadsheets such as `.xlsx` or `.csv` are authoring, review, bulk-entry, and import/export tools.

They are not the runtime intelligence engine.

Expected data workflow:

```text
Human-maintained spreadsheet
        ↓ validate/import
CKB SQLite database
        ↓ query
Python reasoning and orchestration
        ↓
SNS application
```

Future packaged SNS code will therefore generally include:

- Python source files
- tests
- schema/migrations
- controlled seed/import files
- SQLite CKB database or a reproducible method to build it

An `.xlsx` workbook may remain the easiest human-facing master-entry surface, but it should not replace the normalized CKB runtime database.

---

# Files Most Likely Needed Next Session

Future Chad should request only the files relevant to the next task.

## Always attach

- This handoff
- Latest Council Minutes relevant to the active Horizon
- Current Knowledge Backlog, if the task touches deferred concepts
- `git status`

## Attach for planner/timeline work

- `cooking_planner.py`
- `ingredient_profiles.py`
- `recipe_engine.py`
- `app.py`
- relevant tests

## Attach for CKB/schema work

- `schema.py`
- `database.py`
- `seed.py`
- `ckb_studio.py`
- relevant import workbook or CSV
- database schema output or test database when needed

## Attach for UI-only work

- `app.py`
- the engine file supplying the affected result
- screenshot of current behavior
- relevant tests

## Attach for candidate/ranking work

- `recipe_engine.py`
- `ingredient_profiles.py`
- `app.py`
- candidate-related tests

## Attach the database only when necessary

Provide the SQLite database when the problem depends on:

- actual current rows
- schema inspection
- imports
- seed integrity
- aliases
- real candidate data
- migration testing

Do not attach the database merely for isolated Python architecture work.

---

# Current Risks and Guardrails

## Guardrails

- Knowledge belongs in the CKB.
- Knowledge Objects own ingredient knowledge.
- The planner orchestrates.
- The database stores.
- The UI presents.
- State, prep form, technique, strategy, and equipment are distinct concepts.
- Small changes are preferred.
- Tests run before delivery and commit.
- Unknown ingredients must retain safe generic fallback behavior.
- Do not add new customer decisions when existing inputs can imply the answer.
- Energy and time should drive scheduling behavior rather than adding a separate optimization-mode selector.
- All reasonable mise en place occurs before heat unless a specific ingredient or technique requires just-in-time prep.

## Current risks

- [Terminology drift]
- [Knowledge hardcoded in planner]
- [Unrealistic timing]
- [State/technique mismatch]
- [Document drift]
- [Other]

---

# Known Imperfections That Are Not Today’s Scope

List visible flaws that could distract the next session but should not redirect it.

- [Example: generic KO timings remain unrealistic]
- [Example: ingredient selection currently assumes every selected vegetable must be used]
- [Example: equipment-aware thawing is not implemented]

---

# Tomorrow’s Mission

## Primary task

[One narrowly defined engineering outcome.]

## Definition of done

- [Observable behavior]
- [Tests]
- [Expected files changed]
- [Expected debug evidence]

## Do not do

- [No refactor]
- [No API work]
- [No unrelated cleanup]
- [No new documentation artifacts]

---

# Recommended Opening Investigation

Before editing code:

1. Read this handoff.
2. Inspect the listed current files.
3. Confirm `git status`.
4. Run the existing relevant tests.
5. Reproduce the current behavior.
6. State the smallest vertical slice.
7. Only then edit code.

---

# End-of-Day Workflow

```text
Develop
→ Test
→ Discuss and validate behavior
→ gitme / commit / push
→ SNS Documentation Extraction
→ Save generated documentation in existing folders
→ Prepare next handoff
→ goodnight
```

No new documentation type should be created unless the existing documentation architecture genuinely cannot hold the information.

---

# Handoff Summary

- **Where we are:** [one paragraph]
- **Why it matters:** [one paragraph]
- **What happens next:** [one paragraph]
- **What must not be forgotten:** [one paragraph]
