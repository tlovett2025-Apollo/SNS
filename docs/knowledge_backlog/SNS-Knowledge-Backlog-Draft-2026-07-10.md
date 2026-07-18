# SNS Knowledge Backlog

## KO Evolution

-   Replace remaining IngredientForm terminology with IngredientState.
-   Separate Ingredient State from Prep Form.
-   Add Strategy layer between State and Activities.
-   Publish desired outcomes (render fat, brown exterior, juicy
    interior, etc.).
-   Add failure detection and recovery guidance.

## Planner Intelligence

-   Limit recommended vegetables by meal shape.
-   Distinguish 'I have these' from 'Use all these'.
-   Rank ingredient compatibility.
-   Optimize color, texture, flavor, and cooking-time balance.

### Future: Meal Completion Advisor

-   Detect when a selected meal has no meaningful vegetable, foundation,
    or side and could be rounded out during an existing passive cooking
    window.
-   Offer compatible foundations or sides from My Kitchen, ranked by
    cuisine fit, exclusions, equipment, energy, active time, and
    holdability.
-   Weave an accepted side into the same cooking timeline instead of
    publishing a disconnected second recipe.
-   Preserve explicit user intent: a meat-forward meal is valid. Until
    this advisor is deliberately implemented, SNS takes the user's
    selections at face value and does not ask for or add a foundation,
    vegetable, or side.
-   Future structure validation may distinguish an intentionally
    meat-forward braise or plate from structures such as a layered bowl
    that ordinarily imply a foundation. This validation is deferred with
    the advisor and must not silently add food in the current release.

## Equipment Intelligence

-   Model whether equipment can safely transition Frozen Raw to Cooked.
-   Distinguish thaw-only equipment from cook-from-frozen equipment.
-   Recommend owned equipment when it better satisfies user goals.
-   Model kitchen lanes and human attention independently.

## Timing

-   Replace unrealistic fixed micro-times with calibrated estimates.
-   Consider activity classes (Instant, Quick, Short, Medium, Long,
    Passive).

## Cooking Science

-   Fat rendering.
-   Carryover cooking.
-   Browning vs caramelization.
-   Moisture management.
-   Resting science.

## UX

-   Developer activity graph visualization.
-   Developer kitchen lane visualization.
