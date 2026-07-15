# SNS Nightly Project Records and Engineering Handoff

Use this workflow at the end of a Stock & Stir engineering session.

The objective is to maintain the project’s existing system of record and leave one concise handoff for the next session. Do not generate a bundle of documents for Tracy to sort, rename, merge, or store manually.

## Governing Rule

Document the project where the knowledge belongs, then create the handoff.

Do not summarize the entire conversation. Do not manufacture updates. Do not create a new permanent document when an existing canonical record owns the information.

## Step 1 — Establish the Verified Closing State

Record only facts that can be verified from the repository, tests, deployment, or session evidence:

- date and local time;
- repository and branch;
- current commit and commit message;
- current deployed build ID and deployed commit, when available;
- working-tree state;
- tests actually executed and their results;
- current Render service status, when relevant;
- known uncommitted files and why they exist.

Never claim that tests passed unless they were run. Never claim that a deployment is live unless it was verified.

## Step 2 — Update Project Records In Place

Review today’s work and update only the records that genuinely changed.

### Case Study Evidence Log

Canonical record:

`docs/case-study/SNS-Human-AI-Development-CaseStudyLog.md`

Add an entry when the day contains material evidence about the human–AI development model, including:

- a consequential human observation or domain contribution;
- an AI contribution that materially changed implementation or analysis;
- a failure introduced, detected, or corrected;
- a measurable improvement;
- a significant workflow or collaboration decision;
- a milestone supported by builds, commits, screenshots, tests, or deployment evidence.

Each entry must distinguish Tracy’s contribution and authority from the AI contribution. Preserve failures and uncertainty, not merely success.

### Expense Ledger

Canonical record:

`docs/finances/expenses.md`

Update only when a new expense, corrected amount, date, cadence, or financial commitment was identified. Recalculate the known totals. Never guess a missing amount.

### Engineering Council Minutes

Update or create dated minutes only when the session produced durable decisions or discoveries that should still matter years from now.

Appropriate subjects include:

- mission and product philosophy;
- architecture ownership and system boundaries;
- business or pricing decisions;
- durable user-experience rules;
- terminology;
- roadmap decisions;
- Culinary Knowledge Base evolution;
- constitution candidates;
- approved future features.

Do not place routine debugging, Git commands, deployment mechanics, or transient implementation details in Council Minutes.

### Decision Log, Vision, Architecture, Backlog, and Build Notes

Edit the existing canonical file only when its owned information changed:

- Decision Log — durable decisions and their reasoning
- Vision — enduring mission or product direction
- Architecture — lasting responsibilities, boundaries, terminology, or data flow
- Knowledge Backlog — valuable ideas intentionally deferred
- Build Notes — concise implementation milestone record

Do not produce “suggested additions” for Tracy to merge later. Make the correct in-place edit when authorized and possible.

If a record did not change, leave it untouched. “No changes” belongs in the closeout report, not in the permanent file.

## Step 3 — Create One Morning Engineering Handoff

Create one dated handoff in the established handoff documentation area. The handoff should be compact enough to read at the start of the next session without reconstructing the prior day.

Include:

### Session Identity

- handoff date;
- repository and branch;
- current local commit;
- deployed commit and build ID;
- working-tree state;
- active Horizon, program, or release heat.

### Current Mission

One paragraph explaining what the active work is intended to accomplish and why it is the next highest-value work.

### Completed Today

- capabilities completed;
- defects corrected;
- documentation or operational records updated;
- tests actually run;
- commits pushed and deployment status.

### Proven but Not Yet Complete

State what works, what has only been locally validated, and what still requires live verification.

### Active Risks and Known Defects

Include only current actionable risks. Identify whether each is blocking, non-blocking, or deferred.

### Exact Restart Point

- the first recommended task;
- exact files most likely to change;
- required database or external service;
- context documents the next engineer must read;
- commands or verification steps that are genuinely required;
- definition of done for the next heat.

### Do Not Repeat

List resolved approaches, obsolete assumptions, or failed paths that the next session must not accidentally revisit.

## Step 4 — Close the Repository Deliberately

Before declaring the session closed:

1. Run the appropriate tests and record the actual result.
2. Review `git status` and `git diff --check`.
3. Separate unrelated user files from the intended commit.
4. Commit and push only when Tracy has authorized that action.
5. Verify the deployed build when deployment is part of the heat.
6. Ensure the handoff matches the repository’s real final state.

Never use broad staging when unrelated or untracked files are present.

## Step 5 — Return a Short Closeout Report

Tell Tracy:

- which permanent records were updated;
- the path to the new handoff;
- test, Git, and deployment status;
- anything requiring her decision;
- whether the session is safely closed.

Do not return a ZIP unless Tracy needs changed files transferred between workspaces or devices. When a ZIP is needed, include only changed files and preserve repository-relative paths.

## Nightly Completion Standard

The nightly closeout is complete when:

- durable knowledge is stored in its canonical record;
- case-study evidence is preserved when warranted;
- expenses are current when spending occurred;
- one concise handoff identifies the exact restart point;
- tests, Git state, and deployment state are reported truthfully;
- Tracy has no manual documentation-sorting task waiting for her.
