# Meal Orchestration

Round 4 gives the finished meal its own contract above ingredient and component
execution. `meal_orchestration.py` describes eight meal shapes and audits the
real scheduled activities produced by the cooking planner.

The orchestration report records:

- the service and component rule for the selected meal shape;
- physical equipment lanes used by the plan;
- continuous, intermittent, launch-and-check, and passive attention windows;
- work that may safely overlap on different equipment;
- holding time between component readiness and service; and
- any overlapping reservations of the single cook's attention.

Intermittent attention is deliberately interlaceable. A pan that needs periodic
stirring does not reserve the cook for its entire elapsed time. Its launch and
attention minutes remain exclusive, while the remaining process window may
overlap an oven, another burner, or a quick retrieval task. Continuous work
remains exclusive.

Candidate generation publishes this report after the resource-constrained lane
schedule is built. The public API can therefore explain why two processes may
overlap and can fail closed if a future scheduler creates an actual attention
conflict.

