(() => {
  const rawPieces = new Set(["Chicken breast", "Chicken drumsticks", "Chicken thighs", "Chicken wings", "Whole chicken", "Pork chops", "Pork loin", "Turkey breast", "Turkey sausage", "Breakfast sausage", "Italian sausage", "Kielbasa"]);
  const rawPounds = new Set(["Ground beef", "Beef brisket", "Beef stew meat", "Chuck roast", "Flank steak", "Ribeye steak", "Sirloin steak", "Ground chicken", "Ground turkey", "Pork shoulder", "Salmon", "Cod", "Shrimp", "Tilapia"]);
  const refrigerated = new Set(["Butter", "Cheddar cheese", "Colby Jack cheese", "Cottage cheese", "Cream cheese", "Greek yogurt", "Heavy cream", "Milk", "Monterey Jack cheese", "Pepper Jack cheese", "Sour cream", "Swiss cheese", "Eggs"]);
  const canned = new Set(["Baked beans", "Black beans", "Black-eyed peas", "Butter beans", "Cannellini beans", "Chickpeas", "Cranberry beans", "Great Northern beans", "Kidney beans", "Lima beans", "Navy beans", "Pinto beans", "Refried beans", "White beans", "Canned tuna", "Coconut milk", "Cream of chicken soup", "Cream of mushroom soup", "Diced tomatoes", "Rotel", "Tomato sauce"]);
  const bottles = new Set(["Apple cider vinegar", "BBQ sauce", "Chicken broth", "Hot sauce", "Maple syrup", "Molasses", "Mustard", "Olive oil", "Sesame oil", "Vegetable oil", "Worcestershire sauce"]);
  const pantryFoundations = new Set(["Brown rice", "Cornbread", "Egg noodles", "Jasmine rice", "Macaroni", "Pasta", "Quinoa", "White rice", "Wild rice"]);
  const herbs = new Set(["Cilantro", "Fresh thyme"]);
  const shelfProduce = new Set(["Garlic", "Onions", "Potatoes", "Sweet potatoes", "Butternut squash"]);
  const packagedProduce = new Set(["Asparagus", "Blackberries", "Blueberries", "Broccoli", "Brussels sprouts", "Cranberries", "Green beans", "Kale", "Mushrooms", "Mustard greens"]);

  function pantryItem(name) {
    let form = "Fresh", storage_location = "Fresh", quantity = 2, unit = "piece";
    if (rawPieces.has(name)) [form, storage_location, quantity, unit] = ["Frozen Raw", "Freezer", 4, "piece"];
    else if (rawPounds.has(name)) [form, storage_location, quantity, unit] = ["Frozen Raw", "Freezer", 1.5, "lb"];
    else if (refrigerated.has(name)) {
      [form, storage_location, quantity, unit] = ["Refrigerated", "Fridge", 1, "package"];
      if (name === "Eggs") [quantity, unit] = [12, "egg"];
      if (name === "Milk") [quantity, unit] = [1, "carton"];
      if (name === "Butter") [quantity, unit] = [1, "lb"];
    } else if (pantryFoundations.has(name)) [form, storage_location, quantity, unit] = ["Dry", "Pantry", 2, name.includes("rice") || name === "Quinoa" ? "lb" : "box"];
    else if (name === "Corn tortillas") [form, storage_location, quantity, unit] = ["Refrigerated", "Fridge", 1, "package"];
    else if (canned.has(name)) [form, storage_location, quantity, unit] = ["Canned", "Pantry", 2, "can"];
    else if (bottles.has(name)) [form, storage_location, quantity, unit] = ["Shelf-stable", "Pantry", name === "Chicken broth" ? 2 : 1, name === "Chicken broth" ? "carton" : "bottle"];
    else if (herbs.has(name)) [form, storage_location, quantity, unit] = ["Fresh", "Fridge", 1, "bunch"];
    else if (shelfProduce.has(name)) [form, storage_location, quantity, unit] = ["Fresh", "Fresh", name === "Garlic" ? 2 : 3, "piece"];
    else if (packagedProduce.has(name)) [form, storage_location, quantity, unit] = ["Fresh", "Fridge", 1, "package"];
    else if (["All-purpose flour", "Sugar", "Brown sugar"].includes(name)) [form, storage_location, quantity, unit] = ["Shelf-stable", "Pantry", 3, "lb"];
    else if (["Bread", "Biscuits"].includes(name)) [form, storage_location, quantity, unit] = ["Shelf-stable", "Pantry", 1, "package"];
    else if (["Bacon", "Ham"].includes(name)) [form, storage_location, quantity, unit] = ["Cooked", "Fridge", 1, "package"];
    else if (/beans|lentils/.test(name.toLowerCase()) || name === "Split peas") [form, storage_location, quantity, unit] = ["Dry", "Pantry", 1, "lb"];
    else if (/salt|pepper|powder|cumin|paprika|dill|sage|turmeric|ginger/i.test(name)) [form, storage_location, quantity, unit] = ["Shelf-stable", "Pantry", 1, "jar"];
    return { name, form, storage_location, quantity, unit, quantity_band: "", origin: "sample_pantry", notes: "" };
  }

  const common = ["All-purpose flour", "Sugar", "Salt", "Black pepper", "Garlic powder", "Onion powder", "Vegetable oil", "Butter", "Eggs", "Milk", "Onions", "Garlic", "Chicken broth", "White rice", "Pasta", "Diced tomatoes", "Tomato sauce", "Potatoes", "Chicken breast", "Ground beef", "Cheddar cheese", "Bread", "Carrots", "Celery"];
  const definitions = [
    ["pacific_northwest", "Pacific Northwest", "Seafood, berries, sturdy greens, and cool-climate staples.", ["Salmon", "Cod", "Canned tuna", "Wild rice", "Mushrooms", "Kale", "Asparagus", "Apples", "Pears", "Blueberries", "Blackberries", "Cranberries", "Brussels sprouts", "Butternut squash", "Fresh thyme", "Dill", "Maple syrup", "Greek yogurt", "Quinoa", "Navy beans", "Apple cider vinegar", "Olive oil"]],
    ["southern_california", "Southern California", "Produce-forward staples with citrus, chiles, tortillas, and seafood.", ["Avocado", "Limes", "Corn tortillas", "Pinto beans", "Black beans", "Refried beans", "Cilantro", "Jalapenos", "Tomatillos", "Poblanos", "Monterey Jack cheese", "Pepper Jack cheese", "Shrimp", "Tilapia", "Mango", "Papaya", "Oranges", "Zucchini", "Eggplant", "Olive oil", "Greek yogurt", "Cumin", "Chili powder", "Hot sauce"]],
    ["southwest", "Southwest", "Braising meats, beans, chiles, tortillas, and smoky seasonings.", ["Beef brisket", "Flank steak", "Pork shoulder", "Corn tortillas", "Pinto beans", "Black beans", "Refried beans", "Rotel", "Tomatillos", "Poblanos", "Jalapenos", "Serranos", "Cumin", "Chili powder", "Smoked paprika", "Cayenne pepper", "Corn", "Limes", "Avocado", "Cilantro", "Monterey Jack cheese", "Hot sauce", "BBQ sauce"]],
    ["mountain_west", "Mountain West", "Roasts, beans, roots, winter vegetables, and hearty grains.", ["Chuck roast", "Beef stew meat", "Pork chops", "Pork loin", "Kielbasa", "Brown rice", "Quinoa", "Pinto beans", "Great Northern beans", "Sweet potatoes", "Parsnips", "Beets", "Cabbage", "Kale", "Butternut squash", "Apples", "Peaches", "Cornbread", "Apple cider vinegar", "Sage", "Smoked paprika"]],
    ["great_plains", "Great Plains", "Practical casseroles, roasts, noodles, beans, and freezer-friendly vegetables.", ["Chuck roast", "Pork chops", "Pork loin", "Kielbasa", "Breakfast sausage", "Cornbread", "Biscuits", "Egg noodles", "Hash browns", "Baked beans", "Kidney beans", "Cream of chicken soup", "Cream of mushroom soup", "Corn", "Green beans", "Peas", "Cabbage", "Broccoli", "Sour cream", "Colby Jack cheese", "Worcestershire sauce", "Mustard"]],
    ["great_lakes_midwest", "Great Lakes & Midwest", "Sausages, lake fish, noodles, beans, dairy, and pickled flavors.", ["Kielbasa", "Italian sausage", "Salmon", "Canned tuna", "Macaroni", "Egg noodles", "Hash browns", "Navy beans", "Kidney beans", "Sauerkraut", "Cabbage", "Green beans", "Corn", "Peas", "Broccoli", "Cheddar cheese", "Swiss cheese", "Sour cream", "Cream of mushroom soup", "Mustard", "Dill", "Apple cider vinegar"]],
    ["gulf_deep_south", "Gulf Coast & Deep South", "Seafood, smoked sausage, field peas, greens, okra, and heat.", ["Shrimp", "Tilapia", "Kielbasa", "Chicken thighs", "Pork shoulder", "Black-eyed peas", "Butter beans", "Lima beans", "Cornbread", "Biscuits", "Okra", "Collard greens", "Mustard greens", "Green bell pepper", "Celery", "Hot sauce", "Cayenne pepper", "Paprika", "Smoked paprika", "Molasses", "Apple cider vinegar", "Sweet potatoes"]],
    ["florida", "Florida & Caribbean-influenced", "Seafood, tropical fruit, rice, beans, citrus, peppers, and warm spices.", ["Shrimp", "Tilapia", "Cod", "Chicken thighs", "Coconut milk", "Mango", "Papaya", "Pineapple", "Limes", "Oranges", "Avocado", "Black beans", "Jasmine rice", "Cilantro", "Corn tortillas", "Green bell pepper", "Red bell pepper", "Tomatoes", "Hot sauce", "Cumin", "Turmeric", "Ginger", "Sesame oil"]],
    ["appalachia_upper_south", "Appalachia & Upper South", "Pork, beans, greens, cornmeal, biscuits, roots, and orchard fruit.", ["Pork shoulder", "Ham", "Bacon", "Breakfast sausage", "Chicken thighs", "Pinto beans", "Navy beans", "Green beans", "Corn", "Collard greens", "Mustard greens", "Turnips", "Sweet potatoes", "Biscuits", "Cornbread", "Molasses", "Apple cider vinegar", "Apples", "Peaches", "Cream of chicken soup", "Sage", "Cayenne pepper"]],
    ["northeast_new_england", "Northeast & New England", "Fish, beans, brassicas, dairy, maple, apples, and cranberries.", ["Cod", "Salmon", "Canned tuna", "Corned beef", "Navy beans", "Cranberry beans", "Cabbage", "Leeks", "Celery root", "Apples", "Cranberries", "Blueberries", "Maple syrup", "Mustard", "Heavy cream", "Cheddar cheese", "Dill", "Fresh thyme", "Apple cider vinegar", "Brown sugar", "Split peas", "Beets"]],
    ["mid_atlantic", "Mid-Atlantic", "Seafood, pork, beans, greens, corn, orchard fruit, and sharp condiments.", ["Shrimp", "Cod", "Chicken thighs", "Pork loin", "Ham", "Black-eyed peas", "Navy beans", "Cornbread", "Egg noodles", "Collard greens", "Kale", "Corn", "Tomatoes", "Green beans", "Apples", "Peaches", "Apple cider vinegar", "Mustard", "Hot sauce", "Paprika", "Celery seed", "Worcestershire sauce"]]
  ];

  window.SNS_SAMPLE_PANTRIES = definitions.map(([id, label, description, extras]) => ({
    id, label, description,
    items: [...new Set([...common, ...extras])].map(pantryItem)
  }));
})();
