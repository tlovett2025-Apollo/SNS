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



