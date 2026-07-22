# Flavor Identity

SNS treats a named cuisine direction as a cooking contract, not title copy.
The contract lives in `flavor_identity.py` and is consumed before candidate
ranking and again when the planner assigns jobs to selected extras.

Each identity declares:

- its canonical name and sauce profile;
- capability groups that provide minimum identity evidence;
- signature seasonings and compatible accents;
- substitutions that are known to preserve that identity; and
- provenance for later CKB migration.

Ingredient KO affinity has three outcomes: aligned, neutral, or conflicting.
Neutral ingredients remain available because most proteins, vegetables, fats,
and staples travel across cuisines. A conflicting pantry extra is explicitly
omitted before ranking rather than quietly stirred into the meal. A substitute
is accepted only when it is trained for that identity or has no conflicting KO
affinity.

Round 3 launches nine systems: Comfort Food, Italian, Mexican, Mediterranean,
BBQ, Cajun, Chinese, Indian, and Kid-Friendly. Adding another system is a data
operation as long as its sauce profile and ingredient KOs already exist.

