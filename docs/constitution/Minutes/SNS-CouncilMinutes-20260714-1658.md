# Stock & Stir Engineering Council Minutes

**Date:** July 14, 2026  
**Meeting Type:** Architecture, deployment, and product milestone review  
**Project:** Stock & Stir (SNS)

## Permanent Milestone

### Decision / Idea
Stock & Stir crossed from a locally developed prototype into a live, mobile-accessible application. The public frontend and the FastAPI service are now deployed online, connected through a working API path, and usable from a smartphone in portrait orientation.

### Reasoning
A product of this kind is not operationally real merely because its code exists or because it runs on one development computer. It becomes materially real when the complete delivery chain works outside the local environment: source control, deployment, browser access, API communication, and an end-user device. Reaching that threshold proves that the architectural layers can communicate in production and that future work can be validated against a real hosted system.

### Expected Long-Term Impact
Future engineering work can now be evaluated as product behavior rather than only as local code behavior. Stock & Stir can be tested from phones, tablets, and other computers, and the team can distinguish deployment defects from planning defects, user-interface defects, and knowledge-quality defects. This materially reduces uncertainty around the path to a commercial application.

---

## Architecture Decisions

### 1. GitHub Is the Operational Source of Truth

**Decision / Idea**  
The primary repository controls both the frontend and backend deployments. Render watches the `main` branch and deploys the affected services after committed changes.

**Reasoning**  
A repository-controlled deployment path removes dependence on one workstation, preserves a reviewable history, and makes the production state reproducible. It also allows the development process to move toward browser-based or remote development without changing the deployment model.

**Expected Long-Term Impact**  
The application becomes portable across development machines and contributors. Production changes remain tied to versioned source, and recovery is based on repository history rather than local folders.

### 2. Frontend and API Remain Separate Deployable Services

**Decision / Idea**  
The public web interface is hosted as a static site, while the cooking and inventory transport layer runs as a separately hosted FastAPI service.

**Reasoning**  
The public interface and the planning engine have different deployment characteristics. Static pages benefit from a simple, inexpensive hosting model, while the Python service requires a runtime capable of executing the planner. Keeping them separate preserves clear contracts between presentation and computation and allows either side to evolve independently.

**Expected Long-Term Impact**  
The user interface can be redesigned or expanded without restructuring the planner, and the planner can gain new capabilities without requiring the public site to become a Python-rendered application. This separation also creates a clean future path for authenticated clients, mobile applications, and additional interfaces.

### 3. Runtime API Configuration Is an Explicit Integration Boundary

**Decision / Idea**  
The frontend constructs its application endpoints from a configured API base URL rather than embedding endpoint behavior throughout individual pages.

**Reasoning**  
A single integration boundary reduces the risk of inconsistent routes and makes it possible to point development, staging, and production frontends at different services. Centralized configuration is easier to secure, test, and replace than scattered hard-coded URLs.

**Expected Long-Term Impact**  
Environment changes will require fewer edits, and the frontend remains suitable for future staging, custom-domain, or local-development configurations.

### 4. Cross-Origin Access Should Be Restricted to Known Application Origins

**Decision / Idea**  
Once the production frontend hostname was known, the API's cross-origin policy was narrowed from unrestricted access to the live frontend origin.

**Reasoning**  
Open cross-origin access was acceptable during initial transport testing, but it should not remain the production default. Restricting the origin establishes a safer baseline before authentication, household data, billing, and persistent inventory are introduced.

**Expected Long-Term Impact**  
Security practices are incorporated before sensitive customer functions exist, reducing the chance that permissive prototype settings become permanent production liabilities.

---

## User Experience Decisions

### 1. Portrait Phone Use Is a First-Class Requirement

**Decision / Idea**  
Essential account actions, especially Log In, must remain visible and usable on a phone held in portrait orientation. Users must not be required to rotate the device to discover primary navigation.

**Reasoning**  
Some users disable screen rotation, use devices one-handed, or simply expect an application to work in the default phone orientation. Login is not secondary content; it is a gateway action. Hiding it because of viewport width creates a functional accessibility failure, not merely a cosmetic flaw.

**Expected Long-Term Impact**  
All major pages should be reviewed in portrait mobile layouts, and primary actions should be visible either directly in the header or in a clearly accessible menu. Mobile acceptance testing becomes part of normal interface validation.

### 2. Core Actions Should Appear Consistently Across Pages

**Decision / Idea**  
Account and application navigation should be available predictably rather than only on one page or at one viewport width.

**Reasoning**  
Users should not have to remember where a gateway action is located. Consistent navigation reduces cognitive load and prevents dead ends as the public site, account pages, My Kitchen, recipe selection, and recipe display expand.

**Expected Long-Term Impact**  
A shared navigation pattern will eventually replace page-specific improvisation and support a coherent product shell across public and authenticated experiences.

### 3. Incomplete Inventory Editing Is Acceptable Until It Becomes Blocking

**Decision / Idea**  
The current My Kitchen interface may temporarily use a defined inventory list without an end-user "Add Pantry Item" workflow.

**Reasoning**  
The absence of an add-item interface is known, but it did not block the higher-value milestone of proving the hosted end-to-end system. Building every inventory-management feature before validating transport and live use would delay learning from the complete application.

**Expected Long-Term Impact**  
The add-item workflow remains a deliberate backlog item rather than an accidental omission. It should be implemented when inventory expansion becomes necessary for product testing or customer use, preferably as searchable multi-select rather than manual free-form entry alone.

---

## Knowledge Base and Planning Engine Evolution

### 1. Candidate Availability Is Not Candidate Coherence

**Decision / Idea**  
The live planner successfully returned multiple meal candidates from the selected kitchen inventory, but some results were nonsensical because ingredient availability was treated as sufficient evidence for a valid meal.

**Reasoning**  
A list of compatible individual ingredients does not automatically form a coherent meal. Multiple available proteins may each be independently usable, but the planner must decide whether they belong together, compete for the same meal role, or should produce separate candidate directions. The live result demonstrated that transport and candidate generation work while also exposing the next intelligence gap.

**Expected Long-Term Impact**  
Candidate generation must evolve from eligibility filtering to meal composition. Future ranking and construction logic should enforce meal shape, role balance, protein-count rules, cuisine compatibility, preparation compatibility, and intentional multi-protein exceptions.

### 2. Deployment Defects and Culinary-Logic Defects Are Now Distinct

**Decision / Idea**  
Once the phone-to-API-to-planner transaction passed, nonsensical recipes were classified as planning and knowledge-quality defects rather than hosting defects.

**Reasoning**  
Clear defect classification prevents the team from repeatedly questioning the whole stack whenever output quality is poor. The successful transaction proves the request reached the planner and a response returned. Therefore, the next investigation belongs in candidate generation, Knowledge Objects, meal-shape rules, ranking, or recipe construction.

**Expected Long-Term Impact**  
Troubleshooting becomes faster and more disciplined. Production testing can isolate transport, interface, contract, planning, and culinary-quality layers instead of treating every failure as an undifferentiated application problem.

### 3. Candidate Coherence Is the Next Planning Heat

**Decision / Idea**  
The next focused engineering heat should prevent incoherent combinations, especially accidental collections of unrelated proteins, and ensure each candidate represents one understandable meal direction.

**Reasoning**  
Now that the hosted transaction works, output quality is the most visible product risk. Users can forgive a limited inventory interface during development, but they will not trust a system that proposes meals without culinary intent. Candidate coherence is therefore the next highest-leverage improvement.

**Expected Long-Term Impact**  
The planner will move closer to the Stock & Stir product promise: not merely listing things that could be cooked, but reducing decision overload by presenting a short set of credible, distinct, usable dinner directions.

---

## Product Philosophy

### 1. A Working Vertical Slice Has Greater Learning Value Than Broad Incomplete Coverage

**Decision / Idea**  
The team prioritized a narrow but complete path—My Kitchen to API to candidate list to recipe display—over finishing every inventory and account feature first.

**Reasoning**  
A vertical slice exposes integration failures, mobile constraints, contract mismatches, deployment behavior, and real planner output. A wider collection of unfinished screens would provide less reliable evidence about whether the product architecture works.

**Expected Long-Term Impact**  
Future development should continue to favor complete, testable user journeys. Each journey may initially be limited, but it should cross the real architectural layers and produce observable value.

### 2. Stock & Stir Must Be Tested Where It Will Be Used

**Decision / Idea**  
Smartphone testing is not a final polish activity; it is part of product development.

**Reasoning**  
Stock & Stir is intended for kitchens, where users are likely to hold or prop up a phone rather than sit at a development computer. Real-device testing immediately revealed a primary navigation failure that desktop testing did not make obvious.

**Expected Long-Term Impact**  
Kitchen-context testing—including portrait phones, constrained attention, touch targets, scrolling, and readability—should influence interface and workflow decisions throughout development.

---

## Roadmap Decisions

### Completed Milestone

**Live Vertical Slice:**

1. GitHub-controlled source repository.
2. Render-hosted static frontend.
3. Render-hosted FastAPI service.
4. Configured frontend-to-API communication.
5. Restricted production CORS origin.
6. Functional My Kitchen inventory payload.
7. Functional save request.
8. Functional candidate request and response.
9. Functional recipe-selection and recipe-display path.
10. Successful phone portrait smoke test.

### Immediate Next Heat

**Candidate Coherence**

The planner should:

- Distinguish primary proteins from supporting proteins.
- Avoid combining unrelated primary proteins by default.
- Permit intentional multi-protein meals only when supported by a recognized meal shape or composition pattern.
- Produce distinct candidate directions rather than variations that merely enumerate available ingredients.
- Validate ingredient roles, preparation forms, and likely cuisine or flavor compatibility before ranking a candidate.
- Preserve the principle that available inventory constrains the meal but does not, by itself, define a sensible meal.

### Deferred but Preserved

- End-user Add Pantry Item workflow.
- Broader shared navigation shell.
- Authentication and persistent household identity.
- Browser-based development environment independent of the primary Windows workstation.
- Custom production domain routing after the hosted services stabilize.

---

## Lessons Learned

### 1. Live Use Reveals the Next Truth Faster Than Speculation

**Decision / Idea**  
The first live phone test simultaneously confirmed the architecture and exposed the next planner weakness.

**Reasoning**  
Before deployment, transport risk and culinary-quality risk were entangled. Once the application ran on a phone, the team could see that the infrastructure worked and that meal coherence required attention. Real use converted assumptions into evidence.

**Expected Long-Term Impact**  
Deploy early enough to learn, but preserve strong contracts and source control so that early deployment does not become uncontrolled production improvisation.

### 2. Mobile Visibility Is Functional Correctness

**Decision / Idea**  
A link that technically exists but cannot be discovered in the normal device orientation is considered broken.

**Reasoning**  
Functional correctness includes whether the user can perceive and activate the action under realistic conditions. Viewport-dependent disappearance of login violated the intended workflow even though the link existed in desktop markup.

**Expected Long-Term Impact**  
Acceptance criteria should describe observable user access, not merely the presence of HTML elements.

### 3. Keep the Local Repository Synchronized After Direct Repository Changes

**Decision / Idea**  
When changes are committed through connected repository tools, the Windows working copy must be pulled and verified clean before further local work.

**Reasoning**  
Two valid development paths can still diverge if synchronization is neglected. A clean pull and status check prevents duplicate edits, rebase confusion, and accidental overwrites.

**Expected Long-Term Impact**  
The team can safely use both assisted repository changes and local development while preserving a single linear project history.

---

## Open Questions

### 1. What Is the Formal Rule for Multiple Proteins?

The architecture must distinguish among:

- Competing primary proteins that should create separate candidates.
- Primary and supporting proteins that legitimately belong together.
- Recognized combinations such as breakfast plates, mixed grills, soups, casseroles, stews, beans with meat, or surf-and-turf patterns.
- Small flavoring proteins such as bacon, sausage, ham, anchovy, or rendered meat used as seasoning rather than as the meal's principal protein.

The rule should be encoded as reusable planning knowledge rather than a collection of recipe-specific exceptions.

### 2. Where Should Candidate Coherence Live?

The team must determine how responsibility is divided among:

- Ingredient and protein Knowledge Objects.
- Meal-shape definitions.
- Cuisine and flavor relationship knowledge.
- Candidate assembly constraints.
- Candidate scoring and rejection rules.
- Final recipe validation.

The likely answer is layered enforcement, but the exact contract between layers remains open.

### 3. When Should Inventory Expansion Become User-Editable?

The Add Item workflow should be implemented when testing requires ingredients outside the seeded list or when customer onboarding begins. The design should preserve controlled vocabulary, aliases, Forms, storage location, and quantity bands while remaining easy enough for ordinary kitchen use.

---

## Historical Statement

On July 14, 2026, Stock & Stir became a live, mobile-accessible application. A user could open the hosted site on a phone, review My Kitchen, change inventory amounts, save the kitchen payload, request meal candidates from the hosted Python service, choose a candidate, and open a generated recipe. The first live result also established the next major intelligence challenge: a meal planner must understand coherence, not merely ingredient availability.

This date marks the transition from a locally demonstrated system to an operational product architecture capable of supporting continued development, testing, and eventual customer use.
