# CKB to KO Architecture

## Principle

Knowledge belongs in the CKB.

Python contains reasoning, orchestration, and algorithms.

Python should not become the long-term repository of cooking knowledge.

## Current Prototype

Current hardcoded Knowledge Objects live in `ingredient_profiles.py`.

Examples:

- `SWISS_CHARD`
- `CHICKEN_BREAST`

These are prototype KOs used to prove planner behavior.

They are not the permanent storage model.

## Stable Interface

The planner should ask for cooking knowledge through one stable function:

```python
profile = get_ingredient_profile(name, role)