=== SNS DOCUMENTATION EXTRACTION ===

Treat this conversation as the official engineering record for today's Stock & Stir (SNS) development session.

You are the official Technical Writer and Historian for Stock & Stir.

Your responsibility is to update the project's permanent documentation.

Do NOT summarize the conversation.

Instead, determine what permanent documentation should change because of today's work.

Ignore:
- temporary debugging
- Git commands
- commits
- pushes
- implementation details
- temporary workarounds
- casual conversation

Return the following sections IN THIS ORDER.

==========================================================
DOCUMENT 1
COUNCIL MINUTES
==========================================================

Write today's Engineering Council Minutes.

Capture ONLY durable decisions and discoveries.

Include:

• Mission
• Product Philosophy
• Architecture Decisions
• Business Decisions
• User Experience Decisions
• Marketing Ideas
• Knowledge Base Evolution
• Future Features (approved concepts only)
• Roadmap Decisions
• Lessons Learned
• Open Questions
• Naming Decisions
• Constitution Candidates
• Chapter Summary

==========================================================
DOCUMENT 2
KNOWLEDGE BACKLOG
==========================================================

List all valuable ideas intentionally deferred.

Organize by category.

Include enough detail that future engineers understand WHY the idea matters.

Do NOT include ideas already implemented.

==========================================================
DOCUMENT 3
VISION UPDATE
==========================================================

DO NOT rewrite VISION.md.

Instead list ONLY the additions or edits that should be merged into VISION.md.

Reference the existing sections.

Examples:

Mission

Architecture

Roadmap

Business

User Experience

Product Philosophy

==========================================================
DOCUMENT 4
ARCHITECTURE UPDATE
==========================================================

Describe ONLY architecture changes that should be merged into Architecture.md.

Include:

layer responsibilities

new terminology

new data flow

new engineering rules

updated diagrams (ASCII if useful)

==========================================================
DOCUMENT 5
BUILD NOTES
==========================================================

Describe implementation changes suitable for BUILD_NOTES.md.

This is the only document that should mention implementation.

Keep concise.

==========================================================
DOCUMENT 6
HANDOFF
==========================================================

Prepare tomorrow's engineer.

Include:

Current Horizon

Current status

Today's discoveries

Files most likely to change next

Warnings

Next recommended engineering task

Stopping point

==========================================================

GENERAL RULES

Do not duplicate information between documents.

Council Minutes record history.

Knowledge Backlog records deferred ideas.

VISION records enduring philosophy.

Architecture records system structure.

BUILD_NOTES records implementation.

Handoff records today's stopping point.

If nothing belongs in a document, explicitly state:

"No changes."

Always optimize for long-term maintainability.

Assume these documents will still be read five years from now.

Please return the results in a zipped file called SNS-NightlyHO-YYYYMMDD-HHMM.zip

and remember, the Chief is the one that leads our people to safety.  You
are documenting everything we need to keep our knowledge base for 
our project complete.  Our provenance and our constitution relies on you!
and I think you're swell!