# CleanUpTasks.md

## Purpose

This file captures repository cleanup tasks that should happen later, when there is enough energy and they can be done safely. These are not urgent tonight.

The current priority remains:

1. Finish Horizon B engine intelligence.
2. Keep the repository usable.
3. Avoid risky refactors while tired.

---

## 1. Batch File Organization

### Current Status

Most `.bat` files have been moved into:

```text
tools/
```

This is good. The root directory should not become crowded with helper scripts.

### Desired Pattern

Keep the real scripts in:

```text
tools/
```

Create tiny root-level launcher scripts only for commands that are typed often.

These root scripts are called **micro-bats**.

Example:

```text
gitme.bat
```

should contain:

```bat
@echo off
call tools\gitme.bat
```

Example:

```text
runsns.bat
```

should contain:

```bat
@echo off
call tools\runsns.bat
```

### Tasks

- [ ] Confirm all helper `.bat` files live in `tools/`.
- [ ] Decide which commands deserve root-level micro-bats.
- [ ] Create root-level micro-bats only for frequently typed commands.
- [ ] Test each micro-bat from the SNS root directory.
- [ ] Commit the cleanup.

Suggested commit message:

```cmd
chore: organize developer batch scripts
```

---

## 2. Suggested Root Micro-Bats

Likely useful root-level commands:

```text
gitme.bat
runsns.bat
runckbs.bat
goodmorning.bat
gohome.bat
```

Optional later:

```text
goodnight.bat
cleanup.bat
new_release.bat
```

Do not create all of them unless they are actually useful.

---

## 3. Python File Organization

### Current Status

The root directory still contains many `.py` files.

This is acceptable for now.

Do **not** move Python files casually. Moving them will require import changes and testing.

### Current Recommendation

Defer Python reorganization until after Horizon B unless the root becomes unmanageable.

### Possible Future Structure

```text
sns/
  engine/
    recipe_engine.py
    cooking_planner.py
    ingredient_profiles.py
    technique_profiles.py

  data/
    database.py
    schema.py
    seed.py

  ui/
    app.py
    ckb_studio.py

tests/
  smoke_test.py
```

### Tasks

- [ ] Do not move Python files during tired cleanup.
- [ ] Create a future refactor heat for Python package organization.
- [ ] Before moving Python files, list all imports that will need updating.
- [ ] After moving Python files, run smoke tests and launch both apps.

Suggested future commit message:

```cmd
refactor: organize Python modules into package structure
```

---

## 4. Documentation Folder Structure

### Desired Structure

```text
docs/
  constitution/
    CONSTITUTION.md
    README.md
    minutes/

  architecture/
    Architecture.md
    CKB.md
    KnowledgeObjects.md
    TimelineEngine.md

  business/
    Pricing.md
    Marketing.md
    Launch.md

  requirements/

  testing/
```

### Tasks

- [ ] Create `docs/constitution/`.
- [ ] Create `docs/constitution/minutes/`.
- [ ] Add `docs/constitution/README.md`.
- [ ] Decide whether existing architecture docs should move into `docs/architecture/`.
- [ ] Do not move existing docs until ready to update links/references.

---

## 5. Constitution README

Create:

```text
docs/constitution/README.md
```

Suggested contents:

```markdown
# Stock & Stir Constitution

This folder contains the institutional memory of Stock & Stir.

Council Minutes are permanent historical records. They preserve the reasoning behind major product, architecture, business, UX, and roadmap decisions.

CONSTITUTION.md is the living document that reflects the current official philosophy, architecture, business model, terminology, and long-term direction of SNS.

Future engineers, contributors, executives, investors, and AI assistants should read the Constitution before making architectural or strategic decisions.
```

---

## 6. Council Minutes

### Desired Pattern

Council Minutes should be saved in:

```text
docs/constitution/minutes/
```

Suggested naming pattern:

```text
council-meeting-001.md
council-meeting-002.md
council-meeting-003.md
```

Alternative date-based pattern:

```text
2026-07-08-council-001.md
```

Pick one pattern and use it consistently.

### Tasks

- [ ] Choose final naming pattern.
- [ ] Move current vision/history extracts into the minutes folder.
- [ ] Rename `vision-*` files later if desired.
- [ ] Preserve original meeting-minute content; do not over-edit old minutes.
- [ ] Build the living Constitution from the minutes later.

---

## 7. Constitution / Current Plan Document

### Purpose

The Constitution is not the same as the minutes.

Minutes are historical records.

The Constitution is the current official plan.

### Tasks

- [ ] Create first `CONSTITUTION.md`.
- [ ] Merge the major decisions from existing minutes.
- [ ] Remove duplicates.
- [ ] Preserve nuance and reasoning.
- [ ] Organize by:
  - Mission
  - Product Philosophy
  - Architecture
  - Business Model
  - Free vs Premium
  - UX Principles
  - Marketing
  - CKB / KOs
  - Roadmap
  - Naming Standards
  - Open Questions

---

## 8. Git Discipline for Cleanup

Cleanup should be committed separately from engine work.

Do not mix:

```text
Multi-KO Timing
```

with:

```text
folder cleanup
```

Suggested cleanup commits:

```cmd
chore: organize developer batch scripts
docs: add constitution folder structure
docs: add cleanup task list
```

---

## 9. Do Not Do While Tired

Avoid these when fatigued:

- Moving Python files.
- Renaming many files at once.
- Changing imports.
- Editing `.gitignore`.
- Deleting folders.
- Combining cleanup with engine logic.
- Large refactors.
- Anything involving database migration.

Safe tired tasks:

- Write notes.
- Add docs.
- Create checklists.
- Make one tiny micro-bat.
- Run `git status`.

---

## 10. Immediate Next Action

When ready, add this file to the repo:

```cmd
git add CleanUpTasks.md
git commit -m "docs: add cleanup task list"
git push
```

If `gitme.bat` is available and working, it can be used instead.


tools/prompts/

makehistory.md   <---  this is started.  use as example. >
makeconstitution.md
makehandoff.md