# SNS Council Minutes Draft -- 2026-07-10

## Durable Architecture Decisions

### State precedes technique

An ingredient's **state** (Fresh Raw, Frozen Raw, Cooked, Leftover,
Freeze Dried, etc.) is a first-class concept. State determines which
techniques are valid and what activity graph a Knowledge Object may
publish.

### Activity graphs precede timelines

Knowledge Objects publish dependency-aware activities. The planner
converts those activity graphs into kitchen timelines.

### State changes activities, not just timing

Changing from Fresh Raw to Frozen Raw or Cooked may produce a completely
different activity graph rather than simply adjusting durations.

### Planner responsibility

The planner chooses among valid strategies and techniques based on user
goals, available time, energy, and equipment. It should never invent
cooking knowledge.

### Cooking knowledge

Desired cooking outcomes belong in the CKB and KOs, including rendered
fat/skin where appropriate, browning, safe temperature, resting, and
juicy finished texture.

### Human-centered philosophy

The planner should recommend, not silently change, techniques.
Recommendations should explain why they help the user achieve their
goal.

### Emerging architecture

State → Available Strategies → Chosen Strategy → Activities → Activity
Graph → Kitchen Lanes → Timeline
