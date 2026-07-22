# Household Fit and Safety

Round 6 separates non-negotiable safety from preference strength.
`household_fit.py` compiles the household record before recipe generation.

The precedence order is:

1. allergies, medical/religious exclusions, and “never include” are hard gates;
2. dietary constraints compile into the same hard-exclusion boundary;
3. “usually avoid” remains legal but receives a strong ranking penalty; and
4. favorite cuisines or ingredients improve ranking only among safe meals.

Safety groups expand before generation. Shellfish includes shrimp and other
crustaceans/mollusks; peanut, dairy, egg, fish, soy, wheat/gluten, sesame, pork,
and alpha-gal groups have explicit launch expansions. A group label is never
left for a recipe title matcher to interpret later.

Person records may carry their own allergies and exclusions. When tonight's
people are supplied, only those people are compiled into the meal gate. Without
a tonight-specific selection, all saved household people remain in scope.

Every scored candidate carries a household-fit audit showing hard blocks,
avoid matches, favorite matches, preference adjustment, and people in scope.
Preference scoring cannot offset or weaken a safety block.

