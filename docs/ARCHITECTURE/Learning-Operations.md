# Learning Operations

Round 7 turns recipe feedback and unknown products into governed batches of
knowledge work. `learning_operations.py` owns clustering, enrichment queues,
promotion decisions, monitoring summaries, and release policy.

Negative recipe reports route to an architecture layer:

- wrong ingredients → component identity;
- weird instructions → behavior execution;
- uncookable combination → meal coherence;
- timing or effort → meal orchestration; and
- wrong quantity → quantity contracts.

Reports then cluster by route, cooking method, and dish family. A repeated
pattern becomes one batch-review item with every candidate/build reference,
instead of one patch per reported recipe.

The enrichment queue accepts learning clusters, review-first retail drafts,
and repeated unmatched inventory identities. Nothing promotes directly from
the queue. Promotion requires confirmed canonical identity, provenance, safety
review, a complete behavior contract, and at least two regression cases.

Release policy combines the generated production matrix with unresolved
high-risk learning clusters. Ordinary queued enrichment does not block a safe
release; repeated component-identity or meal-coherence failures do.

`tools/build_learning_report.py` emits the complete machine-readable snapshot
for review, automation, or future dashboards.

