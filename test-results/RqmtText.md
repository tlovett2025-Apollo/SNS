
Yes—this is a coherent restructuring. Most of the pain you’re seeing is presentation, but several pieces require small, important data-model upgrades.

The clean page model is becoming:

1. My Kitchen — inventory only
2. Household Preferences — eaters, appetites, exclusions, defaults
3. Give Me Meal Ideas — SNS proposes possibilities
4. Help Me Build My Meal — guided meal composition
5. Signature Recipes — known recipes checked against tonight’s household and kitchen

### My Kitchen

The current cards are too large for inventory management. I would change them into compact rows:

`Lasagna noodles | 8 | noodles ▾ | Details ▸ | Remove`

Details would contain dates, package weight, opened-can information, and other uncommon fields. Most people should see several rows at once.

The Save My Kitchen controls can become a sticky left rail on desktop. On a phone, it should become a compact sticky bottom control because a left rail would consume too much screen.

Units must become ingredient-specific. Examples:

* Lasagna noodles: noodles/sheets, boxes, packages, ounces
* Chicken broth: cartons, cans, cups, ounces
* Bananas: pieces, bunches, pounds
* Ground beef: pounds, ounces, packages
* Bread: loaves, slices, packages
* Eggs: eggs, dozens, cartons

A can should never appear merely because “can” exists in the global unit list.

### Inventory organization

Only foods actually on hand should occupy permanent rows. “Add to My Kitchen” becomes the catalog browser—with yesterday’s typo-tolerant search.

Within storage locations, use subsections and alphabetize inside them:

* Fresh

  * Vegetables
  * Fruit
  * Fresh herbs
* Refrigerator

  * Proteins
  * Dairy
  * Prepared foods and leftovers
  * Condiments
* Freezer

  * Proteins
  * Vegetables and fruit
  * Prepared foods
  * Breads and foundations
* Pantry

  * Grains and rice
  * Pasta and noodles
  * Breads and wraps
  * Cereal and breakfast
  * Beans and proteins
  * Vegetables
  * Fruit
  * Sauces and condiments
  * Baking
  * Fats and oils
* Spices and seasonings

Spices can remain technically stored in `Pantry`. We only need a separate `inventory_group = Spices and seasonings` classification. There is no reason to pretend they occupy a different physical storage system.

### Household Preferences

This should be separate from inventory. It would contain:

* Household members
* Appetite size
* Default participation in meals
* Allergies and hard medical exclusions
* Household exclusions
* Individual dislikes or preferences
* Possibly default meal times and effort assumptions later

A meal then inherits the household automatically.

For tonight, the user can say:

* Lynsey isn’t eating
* Two guests are joining
* One guest is a light eater
* Add a tonight-only exclusion

I would distinguish safety levels:

* Allergies and medical exclusions: cannot be overridden in the normal meal flow
* Household exclusions: require an explicit warning and confirmation
* Dislikes/preferences: can be overridden, but SNS should disclose it

That is safer than treating every exclusion identically.

### Help Me Build My Meal

I agree that tonight’s constraints must come first:

1. Meal: breakfast, lunch, dinner
2. Energy/effort
3. Time available
4. Who is eating tonight
5. Meal-specific exclusions

Then build the food:

* Protein — choose one or more
* Vegetables/fruit — choose multiple
* Foundation — optional
* Cuisine or seasoning direction
* Meal structure
* Cooking environment
* Pantry/fridge extras

The saved form should appear beside owned ingredients:

* Chicken breast — Frozen Raw
* Navy beans — Canned
* Rotisserie chicken — Cooked

No redundant form question.

Multiple proteins do introduce real processing work. SNS must distinguish between:

* Two equal main proteins
* One main protein plus a supporting ingredient
* A stretching combination such as chicken and beans
* Eggs, bacon, sausage, cheese, or canned fish acting as accents

We can allow multiple selection, but the planner must assign roles rather than cook two full protein portions automatically.

### “Need something else?”

Every ingredient selector should begin with owned inventory and end with:

> Need something else?

That opens the typo-tolerant catalog. Selecting an unowned item immediately adds it to a visible “Need to buy” drawer.

That drawer should show:

* Required purchase and quantity
* Possible owned substitution
* Consequence of omission
* Whether changing the ingredient changes the cooking plan
* “Use substitute,” “Buy this,” or “Omit” choices

It should not wait until the completed recipe to reveal the shopping list.

### Combinations that do not work

I recommend an inline compatibility panel instead of frequent popups:

> This combination needs attention.

Then explain specifically:

* The selected cooking environment cannot prepare one component
* These ingredients need incompatible cooking conditions
* A foundation is required for this layered bowl
* Two selected proteins would create excessive quantities
* The cuisine direction lacks an important structural ingredient
* A selected item conflicts with an exclusion

Offer fixes directly:

* Change cooking environment
* Use this substitute
* Remove this component
* Prepare it separately
* Move to a composed plate
* Add the missing ingredient to the grocery list

Use a true modal only for safety issues or intentionally overriding a household exclusion.

So yes: much of this is organizing and presenting existing intelligence. The backend additions are bounded but real:

* Ingredient-specific units and inventory groups
* Household defaults plus tonight-only overrides
* Multiple-protein roles
* Compatibility resolutions
* An explicit grocery/substitution response

The overall direction is excellent. My Kitchen becomes pleasantly boring inventory management; Household Preferences remembers the people; Help Me Build My Meal concentrates on tonight.

Yes. Multiple proteins are officially deferred as a separate feature.

The logged-in landing page should become the application’s home—not another inventory or meal-building screen.

### Persistent left navigation

* Give Me Meal Ideas
* Help Me Build My Meal
* Signature Recipes
* My Favorite Recipes
* My Kitchen
* Household Preferences
* Kitchen Training — future
* Pantry 101

On smaller screens, this becomes a menu rather than consuming the page width.

### Landing-page content

The right pane begins with:

> Welcome back, Susie-Q.

Below that, one useful pantry article occupies most of the page. Initially it can be a static article such as:

> Why My Kitchen makes dinner easier

Later, we can rotate a small collection weekly without needing a new API. The navigation stays fixed while the featured article changes.

We can also include small links such as:

* Continue organizing My Kitchen
* See this week’s meal ideas
* Open my favorite recipes

But it should remain an inviting home page, not become another dense dashboard.

### Favorite recipes

“I want to make this again” is exactly the right language.

Importantly, SNS must save the exact generated recipe—not merely its candidate ID. Future inventory changes, planner improvements, or ingredient substitutions must not silently turn it into a different recipe.

A saved favorite should retain:

* Exact title and ingredients
* Quantities and servings
* Cooking instructions
* Meal structure and production strategy
* Substitutions used
* Recipe-engine/build provenance
* Date saved
* Optional personal note

When reopening it later, SNS can offer:

* **Make it exactly as saved**
* **Adapt it to My Kitchen today**

Either way, it should still perform the current exclusion and food-safety check.

For this first rollout, we only need the logged-in landing-page shell, persistent navigation, one pantry article, and links to existing or placeholder destinations. Authentication and favorite-recipe persistence can connect afterward without redesigning the page.
Yes—I see exactly what you mean.

From the name alone, **Chicken Breast, Tomatoes & White Rice Layered Bowl** implies distinct components. Eight minutes of tomatoes cooking alone in a skillet contradicts that structure. They would collapse, release liquid, and begin becoming a tomato sauce.

For this bowl, fresh tomatoes would more naturally be:

* Added raw as a fresh topping
* Briefly warmed or blistered for perhaps 1–3 minutes
* Roasted separately
* Added to a deliberately named tomato pan sauce

Your “party-cooked vegetable” vocabulary is useful. Tomatoes generally want either:

* Company—onions, peppers, garlic, zucchini, beans, meat, or sauce ingredients
* A short finishing role
* A specific solo dry-heat treatment such as roasting, broiling, grilling, stuffing, or baking with a topping

The exceptions matter too: breaded fried green tomatoes behave differently from ripe tomatoes.

This identifies missing vegetable knowledge beyond cooking time. Each vegetable KO needs to understand:

* Whether it cooks well alone
* Preferred companions
* Good solo cooking environments
* When it should enter a shared vessel
* Whether the intended outcome is fresh, shape-retaining, softened, browned, or sauce-like
* Form-specific exceptions
* Meal-structure compatibility

A layered bowl should preserve component identity. A cooked-together meal may intentionally let tomatoes dissolve into everything else.

And yes—okra will absolutely require its own personality: whole versus sliced, fresh versus frozen, dry heat versus stewing, slime management, acid, breading, and when that texture is intentional.

Captured. Still collecting; no changes yet.
