# Stock & Stir Human–AI Development Case Study Log

## Purpose

This is the evidence ledger for a possible future case study about how Tracy Lovett used ChatGPT as a persistent engineering collaborator to develop Stock & Stir from product concept into a functioning business and software system.

The eventual story must be grounded in dated artifacts and observable outcomes. It should not imply that AI independently created Stock & Stir. Tracy retains product authority, domain judgment, architectural responsibility, acceptance authority, and business ownership. AI assists with analysis, implementation, documentation, testing, and procedural execution.

## Working Thesis

Stock & Stir demonstrates a human–AI development model in which an experienced technical leader uses AI to reduce procedural and cognitive burden without surrendering control of the code, architecture, product intent, or quality standard.

The distinguishing feature is not AI-generated code by itself. It is the complete operating system around the collaboration:

- durable architectural decisions and governance;
- domain knowledge supplied and corrected by a human expert;
- implementation spanning code, tests, hosting, documentation, finance, and product design;
- real-world acceptance testing converted into reusable system behavior;
- source-level provenance and reproducible build identification;
- human review that rejects technically plausible but practically incorrect output;
- repeated recovery from deployment, integration, and tooling failures.

## Evidence Sources

- Git history, commit identifiers, branches, and tagged releases
- Build provenance identifiers and source-file fingerprints
- Automated tests and regression cases
- Printable manual test plans and completed test records
- Engineering Council minutes, decision logs, handoffs, and constitution documents
- Render deployment events, health checks, and performance measurements
- Screenshots of real product behavior
- Expense ledger and infrastructure decisions
- Training waves and Culinary Knowledge Base audit records
- Dated case-study entries below

Never store passwords, API keys, payment information, private tokens, or other credentials in case-study evidence.

## Evidence Entry Format

Each material entry should preserve:

1. **Date and phase**
2. **Situation** — what was being attempted
3. **Human observation or contribution** — what Tracy noticed, knew, rejected, or decided
4. **AI contribution** — analysis, implementation, documentation, testing, or procedural support
5. **Decision and authority** — who made the consequential decision
6. **Artifacts** — files, commits, builds, tests, screenshots, or deployment records
7. **Outcome** — measurable result, including failures
8. **Why it matters** — relevance to the human–AI collaboration model
9. **Publication status** — public, anonymize, private, or permission required

## Dated Evidence

### 2026-07-15 — Build-Level Test Provenance

**Situation:** Live manual testing could not reliably distinguish which combination of Python, HTML, CSS, JavaScript, configuration, and candidate inputs produced a recipe.

**Human observation or contribution:** Tracy requested a small, unobtrusive build number on generated pages so test results could be tied to the exact product version and configuration.

**AI contribution:** Implemented deterministic source fingerprints, Git metadata, runtime configuration capture, API exposure, recipe-page presentation, and automated tests. Produced a printable manual test checklist centered on build identity.

**Decision and authority:** Tracy established traceability as a release requirement and chose to keep the information visually subordinate to the cooking experience.

**Artifacts:** `build_provenance.py`, API and public-site integration, `SNS_Current_Manual_Test_Checklist.docx`, build `SNS-79e85d2129d5`, commit `67a314ab0b75`.

**Outcome:** Screenshots and defect reports could be assigned to an exact deployed build. A later screenshot immediately proved that an observed scheduling problem came from the previous release rather than an undeployed correction.

**Why it matters:** The collaboration added formal configuration control instead of relying on conversational memory or visual similarity.

**Publication status:** Public after repository and screenshot review.

### 2026-07-15 — Mobile-to-Laptop Engineering Continuity

**Situation:** Work began while Tracy was using a phone and later moved back to the laptop, where she wanted direct contact with the code and architecture.

**Human observation or contribution:** Tracy explicitly rejected becoming separated from her code, architectural reasoning, and prior decisions. She chose the laptop as the engineering environment and the phone as a secondary communication surface.

**AI contribution:** Prepared changed-files-only transfer packages, preserved repository-relative paths, guided Git reconciliation, and helped recover from conflicts and OneDrive interference.

**Decision and authority:** Tracy determined the working model and required that AI assistance strengthen rather than replace her relationship with the system.

**Artifacts:** Git rebase records, conflict-resolution package, deployment commits, and conversation screenshots.

**Outcome:** Work moved between devices without recreating the project. Conflicting remote work was integrated rather than overwritten.

**Why it matters:** This is an example of AI functioning as continuity infrastructure while the human remains the engineer of record.

**Publication status:** Public; redact local usernames and private paths if necessary.

### 2026-07-15 — Unscripted Ground-Beef Acceptance Test

**Situation:** Tracy generated a meal from 1.5 pounds of frozen ground beef, onions, white rice, broth, milk, spices, a microwave, skillet, and pressure cooker.

**Human observation or contribution:** Tracy identified that the displayed plan serialized work unnecessarily. During microwave defrosting, the cook could finish vegetable and sauce preparation. She also required explanations for deliberate waiting, readable substep breaks, correct inventory checks for spices, and meaningful package-versus-measure quantities.

**AI contribution:** Traced attention lanes, dependencies, just-in-time targets, ingredient requirements, storage forms, and public rendering. Modified the planner so general preparation could occupy the released-attention portion of defrosting while preserving the safety dependency that thawed meat should proceed promptly to cooking. Added missing-inventory visibility and regression tests.

**Decision and authority:** Tracy supplied the practical cooking and workflow judgment. The AI translated that judgment into general scheduling rules and tests rather than hard-coding one recipe.

**Artifacts:** Ground-beef screenshots; `cooking_planner.py`; `planner_voice.py`; `recipe_engine.py`; `api_service.py`; public-site files; automated frozen-ground-beef regression case; commit beginning `f0d0a4f01b90`.

**Outcome:** Remaining preparation moved inside the microwave window. Intentional slack explained the pressure-cooker critical path. The total remained 39 minutes because rice and natural release controlled the finish, but unnecessary human-idle sequencing was removed.

**Why it matters:** This captures the central Stock & Stir model: domain expertise from lived cooking practice becomes reusable scheduling intelligence through human–AI engineering.

**Publication status:** Public; family anecdotes require Tracy's permission before publication.

### 2026-07-15 — Provenance Feature Creates a Performance Failure

**Situation:** Moving from My Kitchen to a generated meal began taking minutes. Wi-Fi signal strength and the laptop were initially plausible causes.

**Human observation or contribution:** Tracy reported the real perceived delay instead of accepting it as normal and considered environmental causes such as RF conditions.

**AI contribution:** Timed live endpoints separately. `GetRecipeList` completed in approximately eight seconds; `GetRecipe` produced no response within 60 seconds. Inspection showed provenance traversing Render's complete `.venv`, including thousands of installed dependency files. The correction pruned virtual environments, package directories, caches, build output, and `node_modules` before traversal.

**Decision and authority:** The team retained provenance but corrected its source boundary. Declared dependencies remain represented through `requirements.txt`; installed build artifacts are excluded.

**Artifacts:** Live timing records, build `SNS-48fbb0b449bf`, commit `f0d0a4f01b90`, `build_provenance.py`, `test_build_provenance.py`, performance-fix package.

**Outcome:** Local provenance collection covered 57 project source files in approximately 0.037 seconds instead of walking an entire deployed environment.

**Why it matters:** The AI-authored feature caused a production performance defect; human observation exposed it, and measured diagnosis corrected it. A publishable case study should preserve failures as well as successes.

**Publication status:** Public after final live performance verification.

### 2026-07-15 — Infrastructure Becomes a Product Decision

**Situation:** Free Render cold starts and limited CPU distorted performance testing shortly before beta readiness.

**Human observation or contribution:** Tracy questioned whether continuing to tolerate the free environment was rational when the product was approaching launch.

**AI contribution:** Distinguished Render's workspace plan from its service instance types and recommended upgrading only `sns-api` to the $7/month Starter instance while leaving the static site and Hobby workspace unchanged.

**Decision and authority:** Tracy authorized the hosting expense and maintained a new repository expense ledger.

**Artifacts:** Render plan screenshots; `docs/finances/expenses.md`; Render pricing and deployment records.

**Outcome:** Infrastructure spending became an explicit, documented readiness decision rather than an accidental subscription.

**Why it matters:** The collaboration extends beyond code generation into evidence-based business and operational decisions.

**Publication status:** Public; financial totals may be included only with Tracy's approval.

### 2026-07-15 — Nightly Handoff Becomes Project-Record Maintenance

**Situation:** The original nightly prompt extracted durable project history and requested a next-day handoff, but it returned the historical record to Tracy as a Word or `vision-CHANGE.md` artifact for manual storage. Later repository templates expanded the number of possible documentation outputs, increasing the same filing risk.

**Human observation or contribution:** Tracy recognized that the handoff process itself was recreating administrative and cognitive burden. She proposed that nightly closeout should document the day's experiences directly in the permanent Project Records and then create only the restart handoff.

**AI contribution:** Audited the actual original prompt and the later repository templates, preserved the original requirement to retain each decision's reasoning and long-term impact, and converted the nightly workflow into in-place Project Records maintenance followed by one concise engineering handoff.

**Decision and authority:** Tracy established that documentation should be stored by the system during closeout rather than delivered to her as a filing task.

**Artifacts:** Original nightly history-extraction prompt; `docs/CONSTITUTION/AI Prompts/SNS-TEMPLATE_NightlyHandoff-v2.md`; case-study and expense ledgers; future dated handoffs.

**Outcome:** The canonical workflow now updates only records that genuinely changed, preserves verified evidence, creates one restart document, and avoids ZIP output unless files must be transferred between workspaces.

**Why it matters:** The human–AI operating model was redesigned around reducing procedural load while increasing institutional memory and traceability.

**Publication status:** Public.

## Metrics Worth Preserving

- Calendar time from concept to first live end-to-end transaction
- Number of automated and manual tests by milestone
- Defects first identified by human observation versus automated checks
- Defects introduced by AI-generated changes and how they were detected
- Deployment count, failed deployments, and recovery time
- Number of Culinary Knowledge Base training records and audited corrections
- Time from a real cooking observation to a generalized regression-tested rule
- Infrastructure and tooling cost through beta and launch
- Number of durable architectural decisions captured in writing
- Performance before and after significant corrections

## Publication Guardrails

- Preserve failures, uncertainty, reversals, and disagreements; do not manufacture a frictionless success story.
- Distinguish Tracy's domain knowledge and decisions from AI implementation assistance.
- Verify every date, build, commit, cost, and test count against source artifacts before publication.
- Never publish credentials, private repository information, customer data, medical information, or family details without explicit permission.
- Obtain permission before using personal anecdotes, names, screenshots containing identifying information, or direct quotations intended for publication.
- Describe the state of the product accurately: prototype, controlled beta, paid beta, or production launch.

## Next Entry Template

### YYYY-MM-DD — Event Title

**Situation:**

**Human observation or contribution:**

**AI contribution:**

**Decision and authority:**

**Artifacts:**

**Outcome:**

**Why it matters:**

**Publication status:**
