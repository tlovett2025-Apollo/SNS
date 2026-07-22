# Meal Component Planning

SNS plans a meal as a set of independently executable components. A composed
plate is a serving structure; it is not a promise that every component uses the
same vessel or heat source.

## Planning flow

`inventory + selections -> ingredient KOs -> component recognition -> meal
structure -> activity graph -> single-cook schedule -> recipe`

Each layer has one job:

- Ingredient KOs describe physical behavior and culinary capability: pasta,
  meltable cheese, cooking fat, milk or cream, bread suitable for warming, and
  so on.
- Component recognition combines compatible capabilities into a known result.
  For example, pasta + meltable cheese + milk or cooking fat can form a
  macaroni-and-cheese side.
- The meal structure says how components relate at service: integrated skillet,
  layered bowl, composed plate, handheld, and future shapes.
- Component methods assign an environment to each component. A protein may bake
  while a side boils and finishes on the stovetop.
- The activity graph compiles component plans into concrete work, dependencies,
  vessels, attention demand, and service instructions.
- The scheduler determines whether one cook can safely interlace the work.

## Component plan contract

A component plan records:

- stable component and archetype identifiers;
- customer-facing name and meal role;
- preparation method and desired outcome;
- ingredients with explicit jobs (`base`, `binder`, `fat`, `flavor`, etc.);
- required equipment; and
- the knowledge source that justified recognition.

Pantry helpers are requirements of the recognized component. They are not
unassigned extras and must not leak into another component's sauce.

## Knowledge boundary

Planner code may branch on behavior-family codes, component archetypes, meal
structures, and declared methods. It must not learn recipes through ingredient
name checks. New knowledge belongs in one of these locations:

1. a KO family or verified ingredient attribute;
2. a reusable component-recognition rule;
3. a component activity compiler; or
4. a meal-structure or scheduling constraint.

Seed facts are immediately available to an existing installation. Verified CKB
rows overlay those facts, so training remains authoritative without requiring a
planner patch or a database rebuild for every release.

## First vertical slice: macaroni and cheese

The initial component recognizer uses capabilities rather than product names:

- a selected pasta foundation;
- an available meltable cheese; and
- available milk/cream or cooking fat.

The compiler boils and drains the pasta, reserves cooking water, builds the
cheese finish in the pasta pot, and serves the completed side alongside the
main component. The equipment contract includes the pasta pot independently of
the main component's skillet or oven method.

This slice establishes the extension point for boxed sides, steamed vegetable
sides, salads, breads, fried rice, casseroles, and other future component
archetypes without adding recipe-specific branches to the top-level planner.

## Guided side selection

Build My Meal does not need to generate an entire meal before the cook has
decided what sounds good. After the main protein is selected, the side
suggestion service searches My Kitchen for trained components that are fully
producible with owned ingredients and equipment.

Each suggestion is an explicit selection recipe. It names the component
archetype and the exact foundation, produce, and pantry-helper selections that
will reproduce it. The interface and API carry up to two independently prepared
side components. They are not collapsed into the legacy singleton foundation
field. The chosen cards are passed through the same component recognizer and
activity compiler as manually selected ingredients.

The first suggestion families are:

- macaroni and cheese when pasta, meltable cheese, and milk or cooking fat are
  present;
- compatible vegetables steamed together;
- warmed bread; and
- other owned foundation sides prepared by their ingredient KO method.

Allergy and never-include categories are expanded before suggestions are made.
The service returns fewer than five cards when fewer trained sides are fully
supported; it does not fill the row with speculative recipes.

## Round 1 batch

Round 1 establishes a declarative library of fifteen common side archetypes:

1. macaroni and cheese;
2. seasoned beans;
3. steamed vegetables;
4. pepper and onion medley;
5. mashed potatoes;
6. boxed scalloped potatoes;
7. rice;
8. fried rice;
9. green bean casserole;
10. simple salad;
11. fresh tomato relish;
12. warmed bread;
13. roasted potatoes;
14. seasoned corn; and
15. au gratin potatoes.

Every archetype declares its method, equipment, required ingredient jobs,
observable outcome, holding behavior, and activity template. Availability in
the chooser remains evidence-based: a trained archetype is offered only when
the current inventory can satisfy its required jobs.

Ingredient jobs are a separate vocabulary shared across archetypes: main,
side base, vegetable, aromatic, acid, heat, sauce liquid, fat, binder, cheese,
seasoning, and garnish. Family knowledge assigns most jobs; verified item
attributes handle exceptions such as serranos and jalapeños acting as heat.
