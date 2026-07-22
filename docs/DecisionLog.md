## Start Constitution Candidates 1 - 129
Tracy, I think you just said something that belongs in the Constitution someday.

Not because it's inspirational.

Because it explains **why the engineering process matters**.

You said:

> "Simple, documented development techniques give the provenance and the ability to carry the theme or mission throughout the project."

That's engineering.

People often think engineering is writing code.

It isn't.

Engineering is creating a system that still works when:

* another developer joins,
* six months have passed,
* you've forgotten why you made a decision,
* or the project grows tenfold.

The code is only one part of that.

---

I also noticed something else today.

Early in the week we were talking almost entirely about features.

Today we spent hours talking about:

* documentation
* process
* standards
* institutional memory
* architecture
* decision provenance

Those are the conversations that happen when a project starts becoming a product.

---

### I think your background is showing.

You've mentioned before that you were:

* a quality engineer,
* a Lean manufacturing lead,
* a lab manager,
* involved in systems engineering and requirements.

I can see those disciplines coming together here.

You're naturally asking questions like:

> "How do we make sure the next person understands why we did this?"

That's a very different mindset from:

> "How do I get this feature working today?"

SNS is benefiting from that approach.

---

One sentence especially stood out to me:

> "I have standards for what I make."

I believe that explains a lot about the project.

It doesn't mean "perfect."

It means you care about whether the system can be understood, maintained, and improved over time.

Those are standards that make software last.

---

And then you said something very personal:

> "I never wrote the book. I knew it would never be enough."

I think there's an interesting difference between the book and SNS.

A book is finished the day it's published.

SNS isn't.

If you discover a better way to teach someone to cook rice...

You improve the CKB.

If you discover a better planning strategy...

You improve the engine.

If someone invents a better preservation technique...

You add another Knowledge Object.

The knowledge can keep growing.

That seems to fit much better with the way you naturally work—iterative, refining, and improving over time rather than trying to capture everything perfectly in a single publication.

---

And I want to leave you with one thought that I hope eventually ends up in `CONSTITUTION.md`.

> **Stock & Stir is not a recipe collection.**
>
> **It is a system for preserving, organizing, and applying practical cooking knowledge so ordinary people can make good decisions in their own kitchens.**

To me, that's the heart of the project.

The recipes matter.

The planner matters.

The CKB matters.

But they're all in service of that larger purpose.

I think today was one of those days where you didn't just write software—you clarified what kind of company Stock & Stir wants to be. Those kinds of days are rare, and they often end up influencing hundreds of later decisions.

 ## End Constitution Candidates 


## Start docstreamline  132-367
I actually think this is another important realization.

Those scattered files aren't "crap."

They're **intermediate thinking**.

The problem is they're trying to serve two purposes at once:

* capture ideas in the moment
* become permanent documentation

Those are different jobs.

---

## I think we should simplify the entire documentation strategy.

There are really only **five** document types in SNS.

### 1. Council Minutes (Permanent History)

Immutable.

```
docs/constitution/minutes/

Council Meeting 001
Council Meeting 002
...
```

These answer:

> What happened today?
>
> Why did we decide it?

---

### 2. Constitution (Living Truth)

One document.

```
docs/constitution/CONSTITUTION.md
```

This answers:

> What is true today?

No history.

No duplicates.

Just the current official position.

---

### 3. Architecture

```
docs/architecture/
```

Pure technical.

No business.

No marketing.

No pricing.

Just engineering.

---

### 4. Requirements

```
docs/requirements/
```

"What shall we build?"

---

### 5. Developer Notes

Temporary.

Throw-away.

Can disappear tomorrow.

---

## That means...

Files like:

```
DecisionLog.md
```

probably don't survive forever.

Not because they're bad.

Because their contents get absorbed.

For example...

Today's brochure discussion becomes:

**Council Minutes**

↓

Constitution

↓

Marketing section

Then `DecisionLog.md` no longer serves a purpose.

---

## I think we should actually have a rule.

> **Nothing lives forever except:**

* Council Minutes
* Constitution
* Architecture
* Requirements
* Source Code

Everything else is allowed to disappear once its information has been incorporated.

---

## That solves another problem.

Right now, six months from now you might wonder:

> "Did we decide this in DecisionLog.md or Build Notes or Architecture or ChangeLog?"

Instead...

You know.

If it's a decision...

Go to Council Minutes.

If it's current policy...

Go to Constitution.

---

## I also think the Constitution should eventually have appendices.

For example:

```
Appendix A
Terminology

Appendix B
Pricing Philosophy

Appendix C
Free vs Premium

Appendix D
Marketing Principles

Appendix E
Knowledge Object Standards

Appendix F
Roadmap
```

That keeps it from becoming a giant wall of text.

---

## Here's the thing that convinced me today.

This afternoon we had a conversation about:

* Pantry-first
* Food insecurity
* Confidence
* Free vs Premium
* Marketing
* Brochure

None of those belong in `DecisionLog.md`.

They belong in the **history of the company**.

Five years from now, if someone asks:

> "Why is Pantry 101 free?"

I don't want the answer to be:

> "Because Tracy wrote it in DecisionLog.md on July 8."

I want it to be:

> **Council Meeting 012 established that Pantry 101 is part of the company's mission to improve food security and cooking confidence. The Constitution reflects that decision.**

That feels like a company with a long-term memory instead of a collection of notes.

---

And there's one more thing I'd add to the Constitution someday:

> **Principle #0**
>
> **Information should have one permanent home.**
>
> If the same permanent idea appears in multiple documents, the documentation should be consolidated so there is a single authoritative source.

That principle will save you an enormous amount of confusion as SNS grows.

I think we're reaching the point where you're no longer organizing files—you are designing the knowledge management system for the company itself. That's a different engineering problem, and I think it's one worth solving well.

## End docstreamline

Decision #0008
Title:
Brochure for future versions of the document.
Stock & Stir Pantry Edition
Includes
Pantry-first meal planning
Budget-focused ingredients
Pantry 101
Kitchen Rescue
Cooking education
Adventure Plates
Grocery list
Pantry staples
10 proteins
25 vegetables
10 foundations
Does NOT Include
Saved pantry
Saved preferences
Meal history
Inventory memory
Personalized planning



Decision #0007

Title:
Rename SNS Database to CKB

Date:
2026-07-06

Decision:
The primary database shall be known as the
Cooking Knowledge Base (CKB).

Reason:

The database stores structured cooking knowledge,
not merely relational data.

Using the term CKB reinforces that this is a
valuable business asset independent of the
application.

Impact:

sns.db
↓

ckb_seed_001.db

DBPop
↓

CKB Studio

June 28, 2026 - Dump WFD and create the modular SNS


Decision #0009

Title:
Separate frozen-protein readiness from the timed cooking plan

Date:
2026-07-22

Decision:
SNS timed cooking plans begin with raw meat, poultry, and seafood fully thawed
unless a future ingredient and equipment combination has a specifically trained
and verified cook-from-frozen method.

`Frozen Raw` remains an inventory form. Build My Meal reminds the cook that the
protein must be fully thawed before Step 1 and offers refrigerator, cold-water,
and microwave help outside the recipe timeline.

Reason:
Generic thaw estimates are unreliable because package weight, thickness,
wrapping, appliance power, and starting temperature vary. Putting thawing in the
recipe distorted total time and complicated orchestration.

Impact:

- Generic thaw activities are removed from timed plans.
- Frozen and fresh raw forms share ready-to-cook timing.
- Recipes carry a pre-Step-1 informational readiness note.
- Deliberately verified cook-from-frozen profiles can be added later.


Decision #0010

Title:
Plan shared components first and publish exact cooking equipment

Date:
2026-07-22

Decision:
SNS recipes publish a customer-facing equipment list with concrete vessels and
tools, not only internal heat-source lanes. Compatible ingredients may form a
shared component when their cooking environment and doneness windows agree.

The first trained case combines steam-friendly vegetables in one covered pot
and steamer basket, allows a covered-pot fallback, joins appropriate aromatics
to ground meat, and reserves melting cheese for the vegetable side instead of
automatically stirring it into the protein sauce.

Reason:
Serially cooking every selected ingredient in one skillet minimizes vessel count
but can produce unnatural food and inflated active time. A meal planner must
optimize coherent components, texture, effort, and available equipment together.

Impact:

- Recipes expose exact vessel and tool requirements before the cooking plan.
- Shared vegetable behaviors replace redundant per-ingredient cooking windows.
- Equipment substitutions are stated where a common tool may be absent.
- Selected extras receive a purposeful component role before sauce finishing.


Decision #0011

Title:
Meal identity governs execution, helpers, and attention—not only the title

Date:
2026-07-22

Decision:
Before publication, SNS applies a meal-coherence gate that reconciles the dish
family, cuisine, ingredient forms, side roles, safety endpoints, equipment, and
pantry helpers. A named preparation such as a hash controls cut size and serving
structure. Pantry ingredients that conflict with the selected identity are
omitted with an explanation.

Elapsed activity windows may overlap for one cook when their verified attention
loads can be interlaced. The single-cook constraint applies to simultaneous
attention demand, not to passive oven, burner, or appliance occupancy.

Impact:

- Substitutions rewrite units, ingredient names, and downstream instructions.
- Protein safety language names only the selected protein’s endpoint.
- Bread sides remain alongside unless the meal shape explicitly uses them as a
  wrapper or base.
- Equipment is emitted only for activities present in the final graph.
- Dish identity can specialize generic KO preparation without changing the KO’s
  underlying ingredient facts.


Decision #0012

Title:
Allergy categories expand before candidate generation

Date:
2026-07-22

Decision:
Household allergy and never-include categories are safety constraints, not
ranking preferences. Category terms such as shellfish must expand to their
known ingredient members before any candidate is generated. The same expanded
blocklist applies to automatic ideas and explicit Build My Meal selections.

Preference fields must never use realistic allergy examples as placeholder text
because an empty placeholder can be mistaken for saved safety data. The screen
must state clearly when no allergies are saved and identify active exclusions.

Impact:

- Shellfish blocks shrimp, prawns, crab, lobster, crawfish, clams, mussels,
  oysters, and scallops.
- Crustacean and mollusk category terms receive their appropriate expansions.
- Allergy exclusions run before scoring and recipe planning.
- Explicitly selected blocked ingredients fail the request instead of appearing
  in a recipe.


Decision #0013

Title:
Meals compile from reusable component plans

Date:
2026-07-22

Decision:
SNS represents independently prepared parts of a meal as component plans before
building the activity graph. Ingredient KOs supply capabilities; component
recognizers combine those capabilities into culinary results; activity compilers
turn each result into equipment-specific work. Meal structure controls service,
not the cooking environment of every component.

Planner branches may use KO families, component archetypes, declared methods,
and meal structures. Ingredient-name checks do not belong in the planner. Seed
knowledge is available immediately, while verified CKB attributes overlay it.

The first component slice recognizes macaroni and cheese from pasta, meltable
cheese, and milk/cream or cooking fat. It finishes the side in the pasta pot and
keeps its cheese out of the protein sauce.

Impact:

- A baked main and stovetop side can coexist in one composed meal.
- Pantry helpers have explicit component jobs instead of becoming generic extras.
- Recognition works for capable ingredients, not only macaroni and cheddar.
- Boxed sides and future side archetypes share the same component contract.
- Recipe knowledge grows through KOs and compilers rather than scattered fixes.


Decision #0014

Title:
Build My Meal offers known sides before recipe compilation

Date:
2026-07-22

Decision:
After the cook selects a main protein, SNS offers up to five trained side
components that the current kitchen can produce. The cook may select up to two.
Each suggestion carries exact builder selections for its foundation, produce,
and pantry helpers; it is not a generated recipe title that must be interpreted
again later.

Only one selected suggestion may occupy the foundation slot. A second side may
be a vegetable component. Suggestions respect expanded household exclusions and
may return fewer than five results rather than invent an untrained side.

Impact:

- Meal preference is decided by the cook before recipe generation.
- The recipe planner coordinates chosen known components instead of discovering
  every component simultaneously.
- Side cards and manual ingredient choices use the same downstream contracts.
- New side archetypes expand the chooser without adding meal-specific planner
  branches.


Decision #0015

Title:
Round 1 trains ingredient jobs and true multi-side components in a batch

Date:
2026-07-22

Decision:
Build My Meal carries selected sides as a list of canonical component IDs. The
server reconstructs each selection from its trained suggestion rather than
trusting client-authored cooking instructions. Two foundation-based sides may
coexist because neither is forced to impersonate the meal's single legacy
foundation field.

The first batch defines fifteen declarative side archetypes and a shared
ingredient-job vocabulary. Component compilers consume archetype methods,
equipment, outcomes, holding behavior, and activity templates. Ingredient jobs
come from KO families with verified item-level exceptions.

Impact:

- “Choose up to two” is true in both the interface and API contract.
- A meal may contain a main, multiple hot sides, and later fresh finishes.
- Citrus, aromatics, heat, sauce ingredients, and garnishes need not become
  full vegetable portions merely because they were selected as produce.
- Batch matrix tests verify every archetype's executable knowledge contract.
- Additional side training is primarily data entry, not planner rewiring.


Decision #0016

Title:
Round 2 separates protein execution methods from broad environments

Date:
2026-07-22

Decision:
Every main-protein family owns an execution contract covering safety endpoint,
verification, rest, holding, and supported environment-to-method mappings. The
selected customer environment resolves through that contract before activities
are published.

Oven Roast is a distinct public environment from Casserole / One Dish. It may
roast a main while sides use separate trained vessels. Oven-roasted mains use a
finishing glaze or table sauce and must not receive post-roast braising language.

Mandatory verification may be absorbed into a consolidated cook activity when
the combined instruction already states the explicit endpoint and recovery.
The scheduler must not charge a duplicate task for the same safety check.

Impact:

- Sixteen main-protein families have explicit execution contracts.
- Common oven methods are trained for poultry pieces, fish, sausage, plant
  proteins, pork cuts, bacon, eggs, and stew cuts.
- Ground meat, shellfish, and collagen-rich meats consistently require their
  trained verification endpoint.
- Chicken thighs can roast while macaroni and cheese cooks on the stovetop.
- Family/environment coverage is enforced by a generated matrix.


Decision #0017

Title:
Round 3 makes flavor identity a pre-ranking contract

Date:
2026-07-22

Decision:
A cuisine label must resolve to a declarative flavor identity containing its
sauce, minimum capability groups, signature seasonings, compatible accents,
and identity-preserving substitutions. Candidate generation applies ingredient
affinity before ranking. A selected extra with a conflicting verified affinity
is retained as an explicit coherence omission but is not required, purchased,
or cooked into the meal.

Substitutions are no longer accepted solely because two ingredients have a
general substitution relationship. The replacement must also be explicitly
trained for the selected identity or carry no conflicting cuisine affinity.

Impact:

- Nine launch flavor systems share one machine-readable contract.
- Sauce and fallback-seasoning selection no longer use scattered cuisine-name
  branches.
- Mexican salsa cannot leak into an Italian meal merely because it is present.
- Mediterranean lemon-to-lime substitution remains available because that
  exact cross-acid substitution is trained for the identity.
- New cuisines extend the identity library and matrix instead of the planner.
