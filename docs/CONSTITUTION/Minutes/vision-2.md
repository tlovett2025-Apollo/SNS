# vision-2.md --- Stock & Stir Engineering Council History

## Mission

### Decision / Idea

Stock & Stir (SNS) is not a recipe application. It is a cooking
knowledge and decision engine whose primary purpose is to help people
confidently turn the ingredients they already own into a meal.

**Reasoning** The project's value is reducing decision fatigue rather
than collecting recipes. Future features should be evaluated against
this mission.

**Expected Long-Term Impact** Provides a durable North Star for
prioritizing architecture, features, and business decisions.

------------------------------------------------------------------------

## Product Philosophy

### Incremental Engineering

**Decision / Idea** Build SNS through small, testable, incremental
changes with immediate validation and frequent checkpoints.

**Reasoning** Small changes isolate regressions, simplify debugging, and
improve maintainability.

**Expected Long-Term Impact** Supports sustainable long-term
development.

### Documentation Philosophy

**Decision / Idea** Documentation explains why, not merely what.

**Reasoning** Code explains implementation; documentation preserves
engineering intent.

**Expected Long-Term Impact** Retains institutional knowledge.

------------------------------------------------------------------------

## Architecture Decisions

### Layer Responsibilities

**Decision / Idea** - The planner coordinates. - Knowledge Objects
know. - The database stores. - The UI presents.

**Reasoning** Each layer owns one responsibility.

**Expected Long-Term Impact** Reduces duplication and keeps architecture
modular.

### Single Source of Truth

**Decision / Idea** Every cooking fact has one authoritative home.

**Reasoning** Duplicated knowledge eventually diverges.

**Expected Long-Term Impact** Maintains consistency at scale.

### Knowledge Objects

**Decision / Idea** Adopt the permanent architectural term Knowledge
Objects (KOs).

**Reasoning** Represents intelligent domain entities rather than
implementation details.

**Expected Long-Term Impact** Provides stable terminology.

------------------------------------------------------------------------

## Knowledge Base Evolution

### Ingredient Knowledge Objects

**Decision / Idea** Ingredients progressively become intelligent KOs
that understand their own cooking behavior.

**Reasoning** Cooking knowledge belongs with the ingredient.

**Expected Long-Term Impact** Supports scalable planning, substitutions,
and reasoning.

### Timing Intelligence

**Decision / Idea** Ingredient KOs should describe preparation time,
active time, passive time, attention requirements, holdability, and
cooking behavior.

**Reasoning** These are intrinsic ingredient properties.

**Expected Long-Term Impact** Enables accurate planning and workload
estimation.

### Ingredient Forms

**Decision / Idea** Support multiple ingredient forms (fresh raw, frozen
raw, cooked, etc.).

**Reasoning** Ingredient behavior changes with state.

**Expected Long-Term Impact** Improves planning accuracy.

------------------------------------------------------------------------

## User Experience Decisions

### Effort Transparency

**Decision / Idea** Present active time, passive time, and attention
requirements.

**Reasoning** Users benefit from understanding workload, not just
elapsed time.

**Expected Long-Term Impact** Better support for users with limited time
or energy.

------------------------------------------------------------------------

## Roadmap Decisions

1.  Build the planning engine.
2.  Expand Knowledge Object intelligence.
3.  Introduce Ingredient Forms.
4.  Improve effort scoring.
5.  Add educational content.

**Reasoning** Build the reasoning engine before teaching content.

------------------------------------------------------------------------

## Business Organization

### Team Roles

-   CEO: Lynsey
-   Senior Project Engineer: Tracy
-   Chief Knowledge Engineer: Chad G.P.T. the Magnificent

**Reasoning** Clear ownership improves decision making.

------------------------------------------------------------------------

## Lessons Learned

Small, isolated engineering changes with immediate testing produce a
maintainable product and simplify diagnosis of regressions.

------------------------------------------------------------------------

## Open Questions

-   Representation of Ingredient Forms.
-   KO-based effort scoring.
-   Coordination among multiple KOs.
-   Integration of educational content with KOs.
