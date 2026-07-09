Council Summary
Heat 5 — Multi-KO Timing

Objective

Teach every selected Knowledge Object to contribute timing information so the planner reasons about the meal rather than only the protein.

Completed

Multi-KO timing calculations
Protein timing
Vegetable timing
Foundation timing
Meal-level active time
Meal-level passive time
Meal-level attention
Recipe timing reflects calculated values
Smoke tests pass
UI timing contradiction removed
Architectural discoveries

These are the valuable part.

Discovery 1

A candidate can contain multiple KOs of the same type.

Today:

Protein
Vegetable
Foundation

Tomorrow:

Protein

Vegetable
Vegetable
Vegetable

Foundation

Technique

Equipment

Sauce

That's a much richer mental model.

Discovery 2

Elapsed meal time ≠ Active work.

Those are separate concepts.

Discovery 3

Recipes now contain at least two kinds of output.

Information

vs.

Actions

Eventually probably:

Summary
Steps
Knowledge Notes
Warnings
Substitutions
Discovery 4

Parallel cooking deserves its own Heat.

That was a genuine architectural discovery—not scope creep.