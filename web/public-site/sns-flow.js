const SNS = (() => {
  const runtime = window.SNS_CONFIG || {};
  const apiBase = String(runtime.apiBaseUrl || "https://sns-api-xsq4.onrender.com").replace(/\/$/, "");
  const endpoint = path => `${apiBase}${path}`;
  const API = {
    saveKitchen: endpoint("/api/SaveMyKitchen"),
    getMealBuilderOptions: endpoint("/api/GetMealBuilderOptions"),
    getRecipeList: endpoint("/api/GetRecipeList"),
    getRecipe: endpoint("/api/GetRecipe"),
    createCheckout: endpoint("/api/CreateCheckoutSession"),
    billingPortal: endpoint("/api/CreateBillingPortalSession")
  };

  const inventoryUnits = [
    ["item", "items"], ["can", "cans"], ["jar", "jars"], ["box", "boxes"],
    ["bag", "bags"], ["package", "packages"],
    ["egg", "eggs"], ["piece", "pieces"], ["lb", "pounds"], ["oz", "ounces"],
    ["cup", "cups"], ["carton", "cartons"], ["bottle", "bottles"],
    ["bunch", "bunches"], ["loaf", "loaves"], ["portion", "portions"],
    ["meal", "meals"]
  ];
  const quantityProfiles = {
    "canned chicken": { unit: "can", step: 1 },
    "white beans": { unit: "can", step: 1 },
    "cream of chicken soup": { unit: "can", step: 1 },
    "lasagna noodles": { unit: "box", step: 1 },
    "spaghetti": { unit: "box", step: 1 },
    "white rice": { unit: "cup", step: 0.25 },
    "chicken broth": { unit: "carton", step: 1 },
    "eggs": { unit: "egg", step: 1 },
    "milk": { unit: "cup", step: 0.25 },
    "cheese": { unit: "cup", step: 0.25 },
    "chicken breast": { unit: "piece", step: 1 },
    "ground beef": { unit: "lb", step: 0.25 },
    "frozen vegetables": { unit: "bag", step: 1 },
    "bread": { unit: "loaf", step: 1 },
    "fish": { unit: "piece", step: 1 },
    "prepared meal": { unit: "meal", step: 1 },
    "cooked leftovers": { unit: "portion", step: 1 },
    "onions": { unit: "piece", step: 1 },
    "potatoes": { unit: "piece", step: 1 },
    "carrots": { unit: "piece", step: 1 },
    "tomatoes": { unit: "piece", step: 1 },
    "mushrooms": { unit: "package", step: 1 },
    "spinach": { unit: "bunch", step: 1 },
    "kale": { unit: "bunch", step: 1 },
    "swiss chard": { unit: "bunch", step: 1 },
    "romaine lettuce": { unit: "bunch", step: 1 },
    "breakfast sausage": { unit: "lb", step: 0.25 },
    "bacon": { unit: "package", step: 1 }
  };
  const unitRules = {
    "canned chicken": ["can"], "white beans": ["can"], "cream of chicken soup": ["can"],
    "lasagna noodles": ["piece", "box", "package"], "spaghetti": ["box", "package", "lb"],
    "white rice": ["cup", "bag", "lb"], "chicken broth": ["carton", "can", "cup"],
    "eggs": ["egg"], "milk": ["cup", "carton"], "cheese": ["cup", "package", "lb"],
    "chicken breast": ["piece", "lb", "package"], "ground beef": ["lb", "package"],
    "fish": ["piece", "lb", "package"], "breakfast sausage": ["lb", "package"],
    "bacon": ["package", "lb"], "bread": ["loaf", "package"],
    "onions": ["piece", "lb", "bag"], "potatoes": ["piece", "lb", "bag"],
    "carrots": ["piece", "lb", "bag"], "tomatoes": ["piece", "lb", "package"],
    "mushrooms": ["package", "cup", "lb"], "zucchini": ["piece", "lb", "bag"],
    "spinach": ["bunch", "bag", "package"], "kale": ["bunch", "bag"],
    "swiss chard": ["bunch"], "romaine lettuce": ["piece", "package"],
    "frozen vegetables": ["bag", "package", "cup"], "prepared meal": ["meal", "portion", "package"],
    "cooked leftovers": ["portion", "cup", "package"]
  };
  const kitchenStorageKey = "snsKitchenStateV1";
  const mealHistoryKey = "snsMealHistoryV1";
  const defaultForms = {
    Pantry: "Shelf-stable",
    Fridge: "Refrigerated",
    Freezer: "Frozen",
    Fresh: "Fresh"
  };

  function currentPage() {
    return location.pathname.split("/").pop() || "home.html";
  }

  function installAppShell() {
    if (!document.body.hasAttribute("data-app-shell")) return;
    document.body.classList.add("app-shell-page");
    const page = currentPage();
    const activeFor = href => {
      if (href === "my-kitchen.html?start=ideas") return page === "choose-recipe.html";
      if (href === "my-kitchen.html?start=builder") return page === "build-your-meal.html";
      return page === href.split("?")[0];
    };
    const link = (href, label, className = "") => `
      <a class="app-nav-link ${className}${activeFor(href) ? " active" : ""}" href="${href}"${activeFor(href) ? ' aria-current="page"' : ""}>${label}</a>`;
    const onKitchenPage = page === "my-kitchen.html";
    const sidebar = document.createElement("aside");
    sidebar.className = "app-sidebar";
    sidebar.setAttribute("aria-label", "Stock and Stir navigation");
    sidebar.innerHTML = `
      <a class="app-sidebar-brand" href="home.html">Stock <span>&amp;</span> Stir</a>
      <nav class="app-sidebar-nav">
        ${link("home.html", "Home")}
        <div class="app-nav-label">Make dinner</div>
        ${link("my-kitchen.html?start=ideas", "Give Me Meal Ideas", "meal-action")}
        ${link("my-kitchen.html?start=builder", "Help Me Build My Meal", "meal-action")}
        ${link("signature-recipes.html", "Signature Recipes", "meal-action")}
        ${link("favorite-recipes.html", "My Favorite Recipes")}
        <div class="app-nav-label">My household</div>
        ${link("my-kitchen.html", "My Kitchen")}
        ${link("household-preferences.html", "Household Preferences")}
        <div class="app-nav-label">Learn</div>
        ${link("kitchen-training.html", "Kitchen Training")}
        ${link("pantry-101.html", "Pantry 101")}
      </nav>
      ${onKitchenPage ? `<div class="app-sidebar-save"><span data-save-status>Changes are stored in this browser.</span><button class="btn btn-primary" type="button" data-save-kitchen>Save My Kitchen</button></div>` : ""}
      <a class="app-sidebar-account" href="login.html">Account</a>`;
    const overlay = document.createElement("button");
    overlay.type = "button";
    overlay.className = "app-sidebar-overlay";
    overlay.setAttribute("aria-label", "Close navigation");
    document.body.prepend(overlay);
    document.body.prepend(sidebar);

    const header = document.querySelector(".site-header");
    if (header) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "app-menu-toggle";
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Menu";
      header.prepend(toggle);
      const close = () => {
        document.body.classList.remove("app-nav-open");
        toggle.setAttribute("aria-expanded", "false");
      };
      toggle.addEventListener("click", () => {
        const open = document.body.classList.toggle("app-nav-open");
        toggle.setAttribute("aria-expanded", String(open));
      });
      overlay.addEventListener("click", close);
      sidebar.querySelectorAll("a").forEach(item => item.addEventListener("click", close));
    }
  }

  function renderHome() {
    const target = document.querySelector("[data-welcome-name]");
    if (!target) return;
    let auth = {};
    try { auth = JSON.parse(sessionStorage.getItem("snsAuthPrototype") || "{}"); } catch {}
    const emailName = String(auth.email || "").split("@")[0].replace(/[._-]+/g, " ").trim();
    target.textContent = String(auth.displayName || "").trim() || emailName || "there";
    let kitchen = {};
    try { kitchen = JSON.parse(localStorage.getItem(kitchenStorageKey) || "{}"); } catch {}
    const count = (kitchen.foods || []).filter(item => Number(item.quantity || 0) > 0).length;
    const countTarget = document.querySelector("[data-home-kitchen-count]");
    if (countTarget) countTarget.textContent = count ? `${count} foods remembered` : "My Kitchen is ready";
  }

  function runRequestedKitchenAction() {
    if (currentPage() !== "my-kitchen.html") return;
    const action = new URLSearchParams(location.search).get("start");
    if (!action) return;
    history.replaceState({}, "", "my-kitchen.html");
    if (action === "ideas") generateRecipeList();
    if (action === "builder") openMealBuilder();
  }

  function quantityProfile(name) {
    return quantityProfiles[String(name || "").toLowerCase()] || { unit: "item", step: 1 };
  }

  function quantityStepForUnit(unit) {
    return ({ lb: 0.25, cup: 0.25, package: 0.25, can: 0.5 }[unit] || 1);
  }

  function legacyQuantity(level) {
    if (level === "plenty") return 3;
    if (level === "little") return 1;
    return 0;
  }

  function allowedUnits(name) {
    const key = String(name || "").trim().toLowerCase();
    if (unitRules[key]) return unitRules[key];
    if (key.startsWith("canned ")) return ["can"];
    if (/powder|seasoning|spice|salt|pepper|granule/.test(key)) return ["jar", "bottle", "package"];
    return [quantityProfile(name).unit, "package"].filter((value, index, list) => list.indexOf(value) === index);
  }

  function unitOptions(selected, name) {
    const allowed = allowedUnits(name);
    const safeSelected = allowed.includes(selected) ? selected : allowed[0];
    return inventoryUnits.filter(([value]) => allowed.includes(value)).map(([value, label]) =>
      `<option value="${value}"${value === safeSelected ? " selected" : ""}>${label}</option>`
    ).join("");
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(async response => {
      if (!response.ok) throw new Error(await response.text() || `Request failed: ${response.status}`);
      return response.json();
    });
  }

  function kitchenPayload() {
    const items = [...document.querySelectorAll("[data-food]")].map(row => {
      const quantity = Number(row.querySelector("[data-quantity]")?.value || 0);
      return {
        name: row.dataset.food,
        storage: row.dataset.storage,
        form: row.dataset.form || "On hand",
        quantity,
        unit: row.querySelector("[data-unit]")?.value || quantityProfile(row.dataset.food).unit,
        opened_at: row.querySelector("[data-opened-at]")?.value || null,
        refrigerated_after_opening: row.querySelector("[data-refrigerated-after-opening]")?.checked ?? null,
        package_weight_oz: Number(row.querySelector("[data-package-weight]")?.value || 0) || null,
        expiration_date: row.querySelector("[data-expiration-date]")?.value || null
      };
    }).filter(item => item.quantity > 0);
    const householdMembers = [...document.querySelectorAll("[data-household-member]")].map(row => ({
      name: row.querySelector("[data-member-name]")?.value.trim() || "Household member",
      appetite: row.querySelector("[data-member-appetite]")?.value || "standard"
    }));
    const effort = document.querySelector("[data-make-effort]")?.value || "Low";

    return {
      api_version: "1.0",
      contract_version: "my-kitchen-v1",
      household_id: "local-demo-household",
      generated_at: new Date().toISOString(),
      servings: householdMembers.length || 4,
      energy: effort,
      effort,
      inventory: items,
      equipment: [...document.querySelectorAll("[data-equipment].active")].map(button => ({
        name: button.dataset.equipment,
        available: true
      })),
      meal_preferences: {
        household_members: householdMembers,
        recent_meals: recentMealHistory()
      },
      cost_filter: null
    };
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  const commonKitchenCatalog = [
    "Asparagus", "Bacon", "Basmati rice", "Black olives", "Breakfast sausage", "Broccoli",
    "Canned chicken", "Carrots", "Chicken breast", "Chicken broth", "Chickpeas", "Cream of chicken soup",
    "Eggs", "Garlic", "Ground beef", "Kale", "Lasagna noodles", "Mayonnaise", "Milk", "Mushrooms",
    "Navy beans", "Okra", "Onions", "Potatoes", "Romaine lettuce", "Salsa", "Spaghetti", "Spinach",
    "Swiss chard", "Tomatoes", "White beans", "White rice", "Zucchini"
  ];
  const kitchenAliases = {
    "chikn brest": "Chicken breast", "chicken breasts": "Chicken breast", "chikn breast": "Chicken breast",
    "zukini": "Zucchini", "zuchini": "Zucchini", "zuccini": "Zucchini", "mayo": "Mayonnaise"
  };

  function normalizedFoodName(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function editDistance(left, right) {
    const a = normalizedFoodName(left), b = normalizedFoodName(right);
    const row = [...Array(b.length + 1).keys()];
    for (let i = 1; i <= a.length; i += 1) {
      let previous = row[0]; row[0] = i;
      for (let j = 1; j <= b.length; j += 1) {
        const held = row[j];
        row[j] = Math.min(row[j] + 1, row[j - 1] + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1));
        previous = held;
      }
    }
    return row[b.length];
  }

  function canonicalSuggestions(value) {
    const query = normalizedFoodName(value);
    if (query.length < 2) return [];
    const catalog = [...new Set([
      ...commonKitchenCatalog,
      ...[...document.querySelectorAll("[data-food]")].map(row => row.dataset.food)
    ])];
    const alias = kitchenAliases[query];
    return catalog.map(name => ({
      name, score: alias === name ? -10 : normalizedFoodName(name).startsWith(query) ? -5 : editDistance(query, name)
    })).filter(item => item.score <= Math.max(2, Math.floor(query.length * .35)))
      .sort((a, b) => a.score - b.score || a.name.localeCompare(b.name)).slice(0, 5);
  }

  function canonicalFoodName(value) {
    const query = normalizedFoodName(value);
    if (kitchenAliases[query]) return kitchenAliases[query];
    const best = canonicalSuggestions(value)[0];
    return best && best.score <= Math.max(1, Math.floor(query.length * .25)) ? best.name : String(value || "").trim();
  }

  function browserKitchenState() {
    return {
      foods: [...document.querySelectorAll("[data-food]")].map(row => ({
        name: row.dataset.food,
        storage: row.dataset.storage,
        form: row.dataset.form || "On hand",
        quantity: Number(row.querySelector("[data-quantity]")?.value || 0),
        unit: row.querySelector("[data-unit]")?.value || quantityProfile(row.dataset.food).unit,
        opened_at: row.querySelector("[data-opened-at]")?.value || null,
        refrigerated_after_opening: row.querySelector("[data-refrigerated-after-opening]")?.checked ?? null,
        package_weight_oz: Number(row.querySelector("[data-package-weight]")?.value || 0) || null,
        expiration_date: row.querySelector("[data-expiration-date]")?.value || null,
        custom: row.dataset.custom === "true"
      })),
      equipment: [...document.querySelectorAll("[data-equipment]")].map(button => ({
        name: button.dataset.equipment,
        active: button.classList.contains("active"),
        custom: button.dataset.custom === "true"
      })),
      household_members: [...document.querySelectorAll("[data-household-member]")].map(row => ({
        name: row.querySelector("[data-member-name]")?.value || "",
        appetite: row.querySelector("[data-member-appetite]")?.value || "standard"
      })),
      tonight_effort: document.querySelector("[data-make-effort]")?.value || "Low"
    };
  }

  function storeBrowserKitchen() {
    localStorage.setItem(kitchenStorageKey, JSON.stringify(browserKitchenState()));
  }

  function recentMealHistory() {
    try { return JSON.parse(localStorage.getItem(mealHistoryKey) || "[]").slice(0, 8); }
    catch { return []; }
  }

  function recordMealHistory(meal) {
    if (!meal?.title) return;
    const history = recentMealHistory();
    history.unshift({
      title: meal.title,
      protein: meal.protein || "",
      dish_family: meal.dish_family || "",
      meal_structure: meal.meal_structure || "",
      production_strategy: meal.production_strategy || "",
      cuisine: meal.cuisine || "",
      cooking_method: meal.cooking_method || "",
      cooked_at: new Date().toISOString()
    });
    localStorage.setItem(mealHistoryKey, JSON.stringify(history.slice(0, 8)));
  }

  function quantityEditor(name, quantity = 1, unit = "", openedAt = "", refrigerated = false, packageWeightOz = "", expirationDate = "") {
    const profile = quantityProfile(name);
    const selectedUnit = unit || profile.unit;
    return `
      <button class="quantity-none" data-set-none type="button">None</button>
      <label class="quantity-value">
        <span class="sr-only">${escapeHtml(name)} quantity</span>
        <input data-quantity type="number" min="0" step="${quantityStepForUnit(selectedUnit)}" inputmode="decimal" value="${Number(quantity) || 0}">
      </label>
      <label class="quantity-unit">
        <span class="sr-only">${escapeHtml(name)} unit</span>
        <select data-unit>${unitOptions(selectedUnit, name)}</select>
      </label>
      <details class="inventory-detail" data-inventory-detail>
        <summary>Dates and package details</summary>
        <div class="inventory-detail-fields">
          <label class="wide"><span>Use-by or best-by date (optional)</span><input type="date" data-expiration-date value="${escapeHtml(expirationDate)}"></label>
          <label data-can-field><span>Opened date</span><input type="date" data-opened-at value="${escapeHtml(openedAt)}"></label>
          <label data-can-field><span>Refrigerated promptly</span><input type="checkbox" data-refrigerated-after-opening${refrigerated ? " checked" : ""}></label>
          <label data-package-field class="wide"><span>Original package weight in ounces (optional)</span><input type="number" min="0.1" step="0.1" data-package-weight value="${escapeHtml(packageWeightOz)}"></label>
        </div>
      </details>`;
  }

  function createFoodRow({ name, storage, form, quantity, unit = "", level = "little", custom = true, opened_at = "", refrigerated_after_opening = false, package_weight_oz = "", expiration_date = "" }) {
    const row = document.createElement("div");
    row.className = "food-row";
    row.dataset.food = name;
    row.dataset.storage = storage;
    row.dataset.form = form || defaultForms[storage] || "On hand";
    row.dataset.custom = String(Boolean(custom));
    const startingQuantity = quantity ?? legacyQuantity(level);
    row.innerHTML = `
      <div><div class="food-name">${escapeHtml(name)}</div><div class="food-note">${escapeHtml(row.dataset.form)}</div></div>
      <div class="amount quantity-editor" aria-label="${escapeHtml(name)} quantity">${quantityEditor(name, startingQuantity, unit, opened_at, refrigerated_after_opening, package_weight_oz, expiration_date)}</div>`;
    return row;
  }

  function createEquipmentButton({ name, active = true, custom = true }) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `equipment-item${active ? " active" : ""}`;
    button.dataset.equipment = name;
    button.dataset.custom = String(Boolean(custom));
    button.setAttribute("aria-pressed", String(active));
    button.textContent = name;
    return button;
  }

  function createHouseholdMember(member = {}) {
    const row = document.createElement("div");
    row.className = "household-member-row";
    row.dataset.householdMember = "true";
    row.innerHTML = `
      <label><span class="sr-only">Name</span><input data-member-name placeholder="Name" value="${escapeHtml(member.name || "")}"></label>
      <label><span class="sr-only">Appetite</span><select data-member-appetite>
        <option value="light"${member.appetite === "light" ? " selected" : ""}>Light · ¾ portion</option>
        <option value="standard"${!member.appetite || member.appetite === "standard" ? " selected" : ""}>Standard · 1 portion</option>
        <option value="big"${member.appetite === "big" ? " selected" : ""}>Big · 1½ portions</option>
      </select></label>
      <button type="button" data-remove-member>Remove</button>`;
    row.querySelectorAll("input,select").forEach(input => input.addEventListener("change", markChanged));
    row.querySelector("[data-remove-member]").addEventListener("click", () => { row.remove(); markChanged(); });
    return row;
  }

  function inventoryGroup(name, storage) {
    const key = normalizedFoodName(name);
    if (storage === "Fresh") {
      if (/apple|banana|berry|berries|citrus|lemon|lime|orange|peach|pear|fruit/.test(key)) return "Fruit";
      if (/basil|cilantro|dill|mint|parsley|rosemary|sage|thyme|herb/.test(key)) return "Herbs";
      return "Vegetables";
    }
    if (storage === "Pantry") {
      if (/powder|seasoning|spice|salt|pepper|paprika|cumin|oregano|thyme|granule/.test(key)) return "Spices & seasonings";
      if (/rice|oat|quinoa|barley|grain|flour/.test(key)) return "Grains & baking";
      if (/bread|bun|tortilla|wrap|pita|cracker/.test(key)) return "Bread & crackers";
      if (/pasta|spaghetti|noodle|macaroni|lasagna/.test(key)) return "Pasta & noodles";
      if (/cereal|granola/.test(key)) return "Cereal";
      if (/oil|butter|shortening|lard/.test(key)) return "Fats & oils";
      if (/salsa|sauce|mayo|mayonnaise|mustard|ketchup|broth|stock|soup/.test(key)) return "Sauces & cooking helpers";
      if (/fruit|peach|pear|pineapple|applesauce/.test(key)) return "Fruit";
      if (/bean|chickpea|tomato|corn|pea|vegetable/.test(key)) return "Vegetables & legumes";
      return "Other pantry food";
    }
    if (storage === "Freezer") {
      if (/chicken|beef|pork|fish|steak|sausage|bacon|turkey/.test(key)) return "Proteins";
      if (/vegetable|broccoli|spinach|pea|corn|fruit|berry/.test(key)) return "Produce";
      return "Prepared food & bread";
    }
    if (storage === "Fridge") {
      if (/egg|chicken|beef|pork|fish|steak|sausage|bacon|turkey/.test(key)) return "Proteins & eggs";
      if (/milk|cheese|yogurt|cream|butter/.test(key)) return "Dairy";
      if (/sauce|salsa|mayo|mayonnaise|mustard|ketchup|pickle/.test(key)) return "Condiments";
      return "Prepared food & leftovers";
    }
    return "Other";
  }

  function organizeInventorySection(section) {
    if (!section || section.dataset.section === "Equipment") return;
    const list = section.querySelector(".item-list");
    if (!list) return;
    const rows = [...list.querySelectorAll("[data-food]")].sort((a, b) =>
      a.dataset.food.localeCompare(b.dataset.food, undefined, { sensitivity: "base" })
    );
    const groups = new Map();
    rows.forEach(row => {
      const label = inventoryGroup(row.dataset.food, row.dataset.storage);
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(row);
    });
    list.replaceChildren(...[...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([label, items]) => {
      const group = document.createElement("section");
      group.className = "inventory-subgroup";
      group.innerHTML = `<h3>${escapeHtml(label)}</h3><div class="inventory-subgroup-items"></div>`;
      group.querySelector(".inventory-subgroup-items").append(...items);
      return group;
    }));
  }

  function organizeInventory() {
    document.querySelectorAll("[data-section]").forEach(organizeInventorySection);
  }

  function findFoodRow(name, storage) {
    return [...document.querySelectorAll("[data-food]")].find(row =>
      row.dataset.food.toLowerCase() === name.toLowerCase()
      && row.dataset.storage === storage
    );
  }

  function setRowQuantity(row, quantity, unit, details = {}) {
    const input = row.querySelector("[data-quantity]");
    const select = row.querySelector("[data-unit]");
    if (input) input.value = Number(quantity) || 0;
    if (select && unit && [...select.options].some(option => option.value === unit)) {
      select.value = unit;
    }
    if (row.querySelector("[data-opened-at]")) row.querySelector("[data-opened-at]").value = details.opened_at || "";
    if (row.querySelector("[data-refrigerated-after-opening]")) row.querySelector("[data-refrigerated-after-opening]").checked = Boolean(details.refrigerated_after_opening);
    if (row.querySelector("[data-package-weight]")) row.querySelector("[data-package-weight]").value = details.package_weight_oz || "";
    if (row.querySelector("[data-expiration-date]")) row.querySelector("[data-expiration-date]").value = details.expiration_date || "";
    syncInventoryDetails(row.querySelector(".amount"));
  }

  function syncInventoryDetails(group) {
    if (!group) return;
    const unit = group.querySelector("[data-unit]")?.value;
    group.querySelectorAll("[data-can-field]").forEach(field => field.hidden = unit !== "can");
    group.querySelectorAll("[data-package-field]").forEach(field => field.hidden = unit !== "package");
  }

  function upgradeQuantityEditors() {
    document.querySelectorAll("[data-food]").forEach(row => {
      const holder = row.querySelector(".amount");
      if (!holder || holder.querySelector("[data-quantity]")) return;
      const level = holder.querySelector("button.active")?.dataset.level || "none";
      const profile = quantityProfile(row.dataset.food);
      holder.classList.add("quantity-editor");
      holder.setAttribute("aria-label", `${row.dataset.food} quantity`);
      holder.innerHTML = quantityEditor(row.dataset.food, legacyQuantity(level), profile.unit);
    });
  }

  function restoreBrowserKitchen() {
    let state;
    try { state = JSON.parse(localStorage.getItem(kitchenStorageKey) || "null"); }
    catch { state = null; }
    if (!state) return;
    const effort = document.querySelector("[data-make-effort]");
    if (effort && state.tonight_effort) effort.value = state.tonight_effort;

    (state.foods || []).forEach(originalFood => {
      const food = { ...originalFood, name: canonicalFoodName(originalFood.name) };
      let row = findFoodRow(food.name, food.storage);
      if (!row && food.custom) {
        const list = document.querySelector(`[data-section="${food.storage}"] .item-list`);
        row = createFoodRow(food);
        list?.append(row);
      }
      if (row) {
        const quantity = food.quantity ?? legacyQuantity(food.level);
        setRowQuantity(row, quantity, food.unit || quantityProfile(food.name).unit, food);
      }
    });

    (state.equipment || []).forEach(equipment => {
      let button = [...document.querySelectorAll("[data-equipment]")].find(item =>
        item.dataset.equipment.toLowerCase() === equipment.name.toLowerCase()
      );
      if (!button && equipment.custom) {
        button = createEquipmentButton(equipment);
        document.querySelector(".equipment-grid")?.append(button);
      }
      if (button) {
        button.classList.toggle("active", Boolean(equipment.active));
        button.setAttribute("aria-pressed", String(Boolean(equipment.active)));
      }
    });
    const memberHolder = document.querySelector("[data-household-members]");
    if (memberHolder && (state.household_members || []).length) {
      memberHolder.replaceChildren(...state.household_members.map(createHouseholdMember));
    }
  }

  function ensureRemoveControl(row) {
    if (row.querySelector("[data-remove-food]")) return;
    const actions = document.createElement("div");
    actions.className = "inventory-row-actions";
    actions.innerHTML = '<button class="remove-kitchen-item" data-remove-food type="button">Remove</button>';
    actions.querySelector("button").addEventListener("click", () => {
      if (row.dataset.custom === "true") row.remove();
      else setRowQuantity(row, 0);
      updateCount();
      markChanged();
    });
    row.append(actions);
  }

  function bindQuantityEditor(group) {
    if (group.dataset.bound === "true") return;
    group.dataset.bound = "true";
    group.querySelector("[data-set-none]")?.addEventListener("click", () => {
      group.querySelector("[data-quantity]").value = 0;
      updateCount();
      markChanged();
    });
    group.querySelector("[data-quantity]")?.addEventListener("input", () => {
      updateCount();
      markChanged();
    });
    group.querySelector("[data-unit]")?.addEventListener("change", event => {
      group.querySelector("[data-quantity]").step = quantityStepForUnit(event.target.value);
      syncInventoryDetails(group);
      markChanged();
    });
    group.querySelectorAll("[data-opened-at], [data-refrigerated-after-opening], [data-package-weight], [data-expiration-date]").forEach(input => input.addEventListener("change", markChanged));
    syncInventoryDetails(group);
  }

  function bindAmounts() {
    upgradeQuantityEditors();
    document.querySelectorAll(".amount").forEach(bindQuantityEditor);
    document.querySelectorAll("[data-food]").forEach(ensureRemoveControl);
  }

  function updateCount() {
    const payload = kitchenPayload();
    document.querySelectorAll("[data-food]").forEach(row => {
      const present = Number(row.querySelector("[data-quantity]")?.value || 0) > 0;
      row.classList.toggle("is-present", present);
      row.classList.toggle("is-absent", !present);
    });

    const target = document.querySelector("[data-selected-count]");
    if (target) target.textContent = payload.inventory.length;

    const storageCounts = {};
    payload.inventory.forEach(item => storageCounts[item.storage] = (storageCounts[item.storage] || 0) + 1);
    const summary = document.querySelector("[data-storage-summary]");
    if (summary) summary.textContent = Object.entries(storageCounts).map(([name, count]) => `${name} ${count}`).join(" · ");

    document.querySelectorAll("[data-section]").forEach(section => {
      const foodCount = section.querySelectorAll("[data-food].is-present").length;
      const equipmentCount = section.querySelectorAll("[data-equipment].active").length;
      const count = section.querySelector("[data-section-count]");
      if (count) count.textContent = section.dataset.section === "Equipment" ? equipmentCount : foodCount;
      const absent = section.querySelectorAll("[data-food].is-absent").length;
      const showButton = section.querySelector("[data-show-absent]");
      if (showButton) {
        showButton.hidden = absent === 0;
        showButton.textContent = section.classList.contains("show-all") ? "Hide items not on hand" : `Show ${absent} items not on hand`;
      }
    });

    const dev = document.querySelector("[data-payload]");
    if (dev) dev.textContent = JSON.stringify(payload, null, 2);
  }

  function markChanged() {
    storeBrowserKitchen();
    const status = document.querySelector("[data-save-status]");
    if (status) status.textContent = "You have unsaved changes.";
  }

  function bindKitchenDashboard() {
    const search = document.querySelector("[data-kitchen-search]");
    const empty = document.querySelector("[data-empty-search]");

    function applySearch() {
      const query = (search?.value || "").trim().toLowerCase();
      let matches = 0;
      document.querySelectorAll("[data-food]").forEach(row => {
        const match = !query || `${row.dataset.food} ${row.dataset.storage} ${row.dataset.form}`.toLowerCase().includes(query);
        row.classList.toggle("search-match", Boolean(query && match));
        row.hidden = Boolean(query && !match);
        if (match && query) matches += 1;
      });
      document.querySelectorAll("[data-section]").forEach(section => {
        if (!query || section.dataset.section === "Equipment") return section.hidden = false;
        section.hidden = !section.querySelector("[data-food].search-match");
      });
      if (empty) empty.hidden = !query || matches > 0;
    }

    search?.addEventListener("input", applySearch);
    document.querySelector("[data-clear-search]")?.addEventListener("click", () => {
      search.value = "";
      applySearch();
      search.focus();
    });

    document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
      document.querySelectorAll("[data-view]").forEach(item => item.classList.toggle("active", item === button));
      document.querySelectorAll("[data-section]").forEach(section => section.classList.toggle("show-all", button.dataset.view === "all"));
      updateCount();
    }));

    document.querySelectorAll("[data-show-absent]").forEach(button => button.addEventListener("click", () => {
      button.closest("[data-section]").classList.toggle("show-all");
      updateCount();
    }));

    document.querySelectorAll(".section-heading").forEach(button => button.addEventListener("click", () => {
      const section = button.closest("[data-section]");
      section.classList.toggle("collapsed");
      button.setAttribute("aria-expanded", String(!section.classList.contains("collapsed")));
    }));

    document.querySelectorAll("[data-equipment]").forEach(button => button.addEventListener("click", () => {
      button.classList.toggle("active");
      button.setAttribute("aria-pressed", String(button.classList.contains("active")));
      updateCount();
      markChanged();
    }));
    document.querySelector("[data-make-effort]")?.addEventListener("change", markChanged);
    document.querySelector("[data-add-household-member]")?.addEventListener("click", () => {
      const row = createHouseholdMember();
      document.querySelector("[data-household-members]")?.append(row);
      row.querySelector("[data-member-name]")?.focus();
      markChanged();
    });

    const dialog = document.querySelector("[data-kitchen-dialog]");
    const dialogForm = document.querySelector("[data-kitchen-dialog-form]");
    const addName = document.querySelector("[data-dialog-name]");
    const addForm = document.querySelector("[data-dialog-form]");
    const addQuantity = document.querySelector("[data-dialog-quantity]");
    const addUnit = document.querySelector("[data-dialog-unit]");
    const suggestions = document.querySelector("[data-inventory-suggestions]");
    let addSection = "";

    function updateDialogUnit() {
      const profile = quantityProfile(addName.value);
      addUnit.innerHTML = unitOptions(profile.unit, addName.value);
      addQuantity.step = quantityStepForUnit(profile.unit);
      const garlic = addName.value.trim().toLowerCase() === "garlic";
      const note = document.querySelector("[data-dialog-form-note]");
      if (note) note.textContent = garlic
        ? "Tell SNS which garlic: fresh intact bulb, peeled/cut fresh, jarred minced, dried minced, granules, powder, garlic salt, or a seasoning blend."
        : "Form changes how SNS stores, preps, and cooks an ingredient.";
      if (garlic && ["", "shelf-stable", "fresh", "refrigerated", "on hand"].includes(addForm.value.trim().toLowerCase())) addForm.value = "";
    }

    function showNameSuggestions() {
      const matches = canonicalSuggestions(addName.value);
      suggestions.hidden = !matches.length;
      suggestions.innerHTML = matches.map(item =>
        `<button type="button" data-canonical-name="${escapeHtml(item.name)}">${escapeHtml(item.name)}</button>`
      ).join("");
    }

    function openAddDialog(sectionName) {
      addSection = sectionName;
      const equipmentMode = sectionName === "Equipment";
      document.querySelector("[data-dialog-title]").textContent = equipmentMode ? "Add equipment" : `Add to ${sectionName}`;
      document.querySelector("[data-dialog-name-label]").textContent = equipmentMode ? "Equipment name" : "Item name";
      document.querySelector("[data-dialog-form-field]").hidden = equipmentMode;
      document.querySelector("[data-dialog-amount-field]").hidden = equipmentMode;
      addName.value = "";
      addForm.value = defaultForms[sectionName] || "";
      addQuantity.value = 1;
      updateDialogUnit();
      dialog.showModal();
      setTimeout(() => addName.focus(), 0);
    }

    addName?.addEventListener("input", () => { updateDialogUnit(); showNameSuggestions(); });
    suggestions?.addEventListener("click", event => {
      const button = event.target.closest("[data-canonical-name]");
      if (!button) return;
      addName.value = button.dataset.canonicalName;
      suggestions.hidden = true;
      updateDialogUnit();
      addQuantity.focus();
    });
    addUnit?.addEventListener("change", () => {
      addQuantity.step = quantityStepForUnit(addUnit.value);
    });

    document.querySelectorAll("[data-section]").forEach(section => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "add-kitchen-item";
      button.dataset.addKitchenItem = section.dataset.section;
      button.textContent = section.dataset.section === "Equipment" ? "+ Add equipment" : `+ Add ${section.dataset.section.toLowerCase()} item`;
      section.querySelector(".section-body")?.append(button);
      button.addEventListener("click", () => openAddDialog(section.dataset.section));
    });

    document.querySelector("[data-dialog-cancel]")?.addEventListener("click", () => dialog.close());
    dialogForm?.addEventListener("submit", event => {
      event.preventDefault();
      let name = addName.value.trim();
      if (!name) return;
      const canonical = canonicalSuggestions(name)[0];
      if (canonical && canonical.score <= Math.max(1, Math.floor(normalizedFoodName(name).length * .25))) {
        name = canonical.name;
        addName.value = name;
        updateDialogUnit();
      }
      if (name.toLowerCase() === "garlic" && !addForm.value.trim()) {
        addForm.setCustomValidity("Choose the kind of garlic so SNS knows how to store and use it.");
        addForm.reportValidity();
        return;
      }
      addForm.setCustomValidity("");

      if (addSection === "Equipment") {
        let button = [...document.querySelectorAll("[data-equipment]")].find(item =>
          item.dataset.equipment.toLowerCase() === name.toLowerCase()
        );
        if (!button) {
          button = createEquipmentButton({ name });
          document.querySelector(".equipment-grid")?.append(button);
          button.addEventListener("click", () => {
            button.classList.toggle("active");
            button.setAttribute("aria-pressed", String(button.classList.contains("active")));
            updateCount();
            markChanged();
          });
        } else {
          button.classList.add("active");
          button.setAttribute("aria-pressed", "true");
        }
      } else {
        let row = findFoodRow(name, addSection);
        if (!row) {
          row = createFoodRow({
            name, storage: addSection, form: addForm.value.trim(),
            quantity: Number(addQuantity.value), unit: addUnit.value
          });
          document.querySelector(`[data-section="${addSection}"] .item-list`)?.append(row);
          bindQuantityEditor(row.querySelector(".amount"));
          ensureRemoveControl(row);
          organizeInventorySection(document.querySelector(`[data-section="${addSection}"]`));
        } else {
          setRowQuantity(row, Number(addQuantity.value), addUnit.value);
        }
      }
      dialog.close();
      updateCount();
      markChanged();
    });
  }

  function fallbackRecipes(payload) {
    const names = payload.inventory.map(i => i.name.toLowerCase());
    const has = (...parts) => parts.every(p => names.some(n => n.includes(p)));
    const recipes = [];
    if (has("chicken") && has("rice")) recipes.push({
      id:"chicken-rice-supper", title:"Comforting One-Pot Chicken & Rice",
      minutes:35, effort:"Low", match:"Strong match",
      summary:"A calm one-pan meal built from familiar pantry food.",
      meal_shape:"plate", serving_temperature:"hot", preparation_mode:"cooked",
      capability_status:"prototype"
    });
    if (has("beef") && (has("potato") || has("carrot"))) recipes.push({
      id:"beef-stew", title:"Beef, Potato & Carrot Stew",
      minutes:90, effort:"Low attention", match:"Strong match",
      summary:"A covered gentle simmer with a fork-tender finish.",
      meal_shape:"stew", serving_temperature:"hot", preparation_mode:"cooked",
      capability_status:"prototype"
    });
    recipes.push(
      {id:"pantry-soup", title:"Use-What-You-Have Pantry Soup", minutes:40, effort:"Flexible", match:"Good match", summary:"A forgiving soup shaped around the foods already selected."},
      {id:"kitchen-supper", title:"My Kitchen One-Pot Supper", minutes:30, effort:"Medium", match:"Good match", summary:"Compatible ingredients brought together in stages in one vessel."},
      {id:"simple-plate", title:"Simple Protein, Vegetable & Foundation Plate", minutes:25, effort:"Low", match:"Practical match", summary:"Cook the components simply and finish them together."}
    );
    return recipes.slice(0, 6);
  }

  async function saveKitchen() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    storeBrowserKitchen();
    try {
      await postJson(API.saveKitchen, payload);
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = "My Kitchen is saved.";
    } catch {
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = "Saved in this browser; API connection is pending.";
    }
  }

  async function generateRecipeList() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    let recipes;
    try {
      const response = await postJson(API.getRecipeList, payload);
      recipes = response.candidates || response.recipes || response;
    } catch {
      recipes = fallbackRecipes(payload);
    }
    sessionStorage.setItem("snsRecipeChoices", JSON.stringify(recipes));
    location.href = "choose-recipe.html";
  }

  function openMealBuilder() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    storeBrowserKitchen();
    location.href = "build-your-meal.html";
  }

  function openSignatureRecipes() {
    location.href = "signature-recipes.html";
  }

  const fallbackBuilderOptions = {
    proteins: ["Chicken breast", "Ground beef", "Eggs", "Canned chicken", "White beans"].map(name => ({name})),
    produce: ["Onions", "Carrots", "Mushrooms", "Spinach", "Tomatoes", "Broccoli", "Apples"].map(name => ({name, kind: name === "Apples" ? "fruit" : "vegetable"})),
    foundations: ["White rice", "Pasta", "Bread", "Flour tortillas", "Potatoes"].map(name => ({name})),
    extras: ["Mayonnaise", "Salsa", "Mustard", "BBQ sauce", "Hot sauce", "Soy sauce", "Sour cream", "Cheddar cheese", "Chicken broth", "Tomato sauce"].map(name => ({name})),
    cuisines: ["Comfort Food", "American", "Italian", "Mexican", "Mediterranean"],
    methods: [
      {id:"skillet", label:"Stovetop", description:"One or more stovetop vessels; meal structure decides whether components join or stay separate."},
      {id:"soup", label:"Soup or Stew", description:"A liquid-led one-vessel meal; SNS chooses the suitable owned pot."},
      {id:"casserole", label:"Oven Bake", description:"An oven-baked meal assembled in one baking dish."},
      {id:"handheld", label:"Handheld", description:"Components cooked as needed, then assembled with bread or a wrap."}
    ],
    meal_structures: [
      {id:"integrated", label:"Cooked Together", description:"A cohesive one-vessel meal whose compatible ingredients join in stages."},
      {id:"composed_plate", label:"Composed Plate", description:"Restaurant-style separate components."},
      {id:"layered_bowl", label:"Layered Bowl", description:"Components arranged over a foundation."}
    ]
  };

  function ownedKitchenNames(kitchen) {
    return new Set((kitchen.inventory || []).map(item => String(item.name || "").toLowerCase()));
  }

  function choiceLabel(item, owned) {
    const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
    return `${item.name}${isOwned ? " — In My Kitchen" : " — Need to buy"}`;
  }

  async function renderMealBuilder() {
    const form = document.querySelector("[data-meal-builder]");
    if (!form) return;
    const kitchen = JSON.parse(sessionStorage.getItem("snsKitchenPayload") || "{}");
    const owned = ownedKitchenNames(kitchen);
    const savedMembers = kitchen.meal_preferences?.household_members || [];
    if (savedMembers.length) {
      for (const appetite of ["light", "standard", "big"]) {
        const input = form.querySelector(`[data-eaters-${appetite}]`);
        if (input) input.value = savedMembers.filter(member => member.appetite === appetite).length;
      }
    }
    let options;
    try {
      options = await postJson(API.getMealBuilderOptions, kitchen);
    } catch {
      options = fallbackBuilderOptions;
    }

    const proteinHolder = form.querySelector("[data-protein-options]");
    const inferProteinState = item => {
      const name = String(item.name || "").toLowerCase();
      const savedForm = String(item.form || "").toLowerCase();
      if (name.startsWith("canned ") || savedForm.includes("canned")) return "Canned";
      if (name.includes("rotisserie") || ["cooked", "prepared", "ready to eat", "leftover"].some(term => savedForm.includes(term))) return "Cooked";
      if (savedForm.includes("frozen")) return "Frozen Raw";
      return "Fresh Raw";
    };
    proteinHolder.innerHTML = (options.proteins || []).map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      const state = inferProteinState(item);
      return `<label class="produce-choice protein-choice" data-protein-choice data-search-name="${escapeHtml(item.name.toLowerCase())}">
        <input type="checkbox" name="protein" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small data-protein-role>${isOwned ? `In My Kitchen${item.form ? ` · ${escapeHtml(item.form)}` : ""}` : "Need to buy"}</small>
        <select data-protein-state aria-label="${escapeHtml(item.name)} form"${isOwned ? " disabled" : ""}>
          <option${state === "Fresh Raw" ? " selected" : ""}>Fresh Raw</option>
          <option${state === "Frozen Raw" ? " selected" : ""}>Frozen Raw</option>
          <option${state === "Cooked" ? " selected" : ""}>Cooked</option>
          <option${state === "Canned" ? " selected" : ""}>Canned</option>
        </select>
      </label>`;
    }).join("");
    const syncProteinRoles = () => {
      const selected = [...proteinHolder.querySelectorAll('input[name="protein"]:checked')];
      selected.forEach((input, index) => {
        const role = input.closest("[data-protein-choice]").querySelector("[data-protein-role]");
        const name = input.value.toLowerCase();
        const inferred = index === 0 ? "Main protein" :
          /bean|lentil|chickpea/.test(name) ? "Stretch protein" :
          /bacon|sausage|ham|chorizo/.test(name) ? "Flavor accent" : "Supporting protein";
        role.textContent = `${inferred} · ${role.textContent.replace(/^(Main protein|Stretch protein|Flavor accent|Supporting protein) · /, "")}`;
      });
    };
    proteinHolder.addEventListener("change", syncProteinRoles);
    form.querySelector("[data-protein-search]")?.addEventListener("input", event => {
      const query = event.target.value.trim().toLowerCase();
      form.querySelectorAll("[data-protein-choice]").forEach(choice => {
        choice.hidden = Boolean(query) && !choice.dataset.searchName.includes(query);
      });
    });

    const foundation = form.querySelector("[data-builder-foundation]");
    foundation.innerHTML = `<option value="">No foundation</option>` + (options.foundations || []).map(item =>
      `<option value="${escapeHtml(item.name)}">${escapeHtml(choiceLabel(item, owned))}</option>`
    ).join("");

    form.querySelector("[data-builder-cuisine]").innerHTML = (options.cuisines || fallbackBuilderOptions.cuisines).map(name =>
      `<option value="${escapeHtml(name)}"${name === "Comfort Food" ? " selected" : ""}>${escapeHtml(name)}</option>`
    ).join("");

    form.querySelector("[data-method-options]").innerHTML = (options.methods || fallbackBuilderOptions.methods).map((item, index) => `
      <label class="builder-choice-card">
        <input type="radio" name="cooking-method" value="${escapeHtml(item.id)}"${index === 0 ? " checked" : ""}>
        <span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.description)}</small></span>
      </label>`).join("");
    form.querySelector("[data-structure-options]").innerHTML = (options.meal_structures || fallbackBuilderOptions.meal_structures).map((item, index) => `
      <label class="builder-choice-card">
        <input type="radio" name="meal-structure" value="${escapeHtml(item.id)}"${index === 0 ? " checked" : ""}>
        <span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.description)}</small></span>
      </label>`).join("");
    const syncStructureGuidance = () => {
      const method = form.querySelector('input[name="cooking-method"]:checked')?.value;
      const structureInputs = [...form.querySelectorAll('input[name="meal-structure"]')];
      structureInputs.forEach(input => {
        input.disabled = method !== "skillet" && input.value !== "integrated";
      });
      if (structureInputs.find(input => input.checked)?.disabled) {
        structureInputs.find(input => input.value === "integrated").checked = true;
      }
      const structure = structureInputs.find(input => input.checked)?.value;
      const produceCount = form.querySelectorAll('input[name="produce"]:checked').length;
      const guidance = form.querySelector("[data-structure-guidance]");
      if (method !== "skillet") {
        guidance.textContent = "This cooking family currently determines how the components come together. More structures will appear as their cooking grammar is trained.";
      } else if (structure === "composed_plate" && produceCount > 2) {
        guidance.textContent = "Composed plates usually feature one or two vegetables. You can continue, or choose the ingredients you most want to taste separately.";
      } else if (structure === "composed_plate") {
        guidance.textContent = "Each component will be prepared independently and timed to meet on the plate.";
      } else if (structure === "layered_bowl") {
        guidance.textContent = "The foundation goes into the bowl first, with the other components arranged over it.";
      } else {
        guidance.textContent = "Compatible ingredients can join the same vessel as the cooking environment changes.";
      }
    };
    form.querySelectorAll('input[name="cooking-method"], input[name="meal-structure"]').forEach(input =>
      input.addEventListener("change", syncStructureGuidance)
    );

    const produce = options.produce || fallbackBuilderOptions.produce;
    const produceHolder = form.querySelector("[data-produce-options]");
    produceHolder.innerHTML = produce.map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      return `<label class="produce-choice" data-produce-choice data-search-name="${escapeHtml(item.name.toLowerCase())}">
        <input type="checkbox" name="produce" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small>${isOwned ? `In My Kitchen${item.form ? ` · ${escapeHtml(item.form)}` : ""}` : "Need to buy"}${item.kind === "fruit" ? " · Fruit" : ""}</small>
        <select data-produce-form aria-label="${escapeHtml(item.name)} form"${isOwned ? " disabled" : ""}>
          ${isOwned ? `<option value="${escapeHtml(item.form || "")}">Use My Kitchen form</option>` : '<option>Fresh</option><option>Frozen</option><option>Canned</option>'}
        </select>
      </label>`;
    }).join("");
    produceHolder.addEventListener("change", syncStructureGuidance);
    syncStructureGuidance();

    const extras = options.extras || fallbackBuilderOptions.extras;
    const extrasHolder = form.querySelector("[data-extra-options]");
    extrasHolder.innerHTML = extras.map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      return `<label class="produce-choice" data-extra-choice data-search-name="${escapeHtml(item.name.toLowerCase())}">
        <input type="checkbox" name="extras" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small>${isOwned ? "In My Kitchen" : "Need to buy"}</small>
      </label>`;
    }).join("");

    form.querySelector("[data-produce-search]")?.addEventListener("input", event => {
      const query = event.target.value.trim().toLowerCase();
      form.querySelectorAll("[data-produce-choice]").forEach(choice => {
        choice.hidden = Boolean(query) && !choice.dataset.searchName.includes(query);
      });
    });
    form.querySelector("[data-extra-search]")?.addEventListener("input", event => {
      const query = event.target.value.trim().toLowerCase();
      form.querySelectorAll("[data-extra-choice]").forEach(choice => {
        choice.hidden = Boolean(query) && !choice.dataset.searchName.includes(query);
      });
    });
    const syncPortions = () => {
      const light = Number(form.querySelector("[data-eaters-light]")?.value || 0);
      const standard = Number(form.querySelector("[data-eaters-standard]")?.value || 0);
      const big = Number(form.querySelector("[data-eaters-big]")?.value || 0);
      const people = light + standard + big;
      const portions = light * 0.75 + standard + big * 1.5;
      const portionText = Number.isInteger(portions) ? String(portions) : portions.toFixed(2).replace(/0$/, "");
      form.querySelector("[data-portion-summary]").textContent = `${people} ${people === 1 ? "person" : "people"} · ${portionText} planning portions`;
    };
    form.querySelectorAll("[data-eaters-light], [data-eaters-standard], [data-eaters-big]").forEach(input => input.addEventListener("input", syncPortions));
    syncPortions();
    form.addEventListener("submit", generateBuiltMeal);
    form.querySelector("[data-builder-loading]").hidden = true;
    form.querySelector("[data-builder-fields]").hidden = false;
  }

  async function generateBuiltMeal(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const status = form.querySelector("[data-builder-status]");
    const button = form.querySelector("button[type=submit]");
    const kitchen = JSON.parse(sessionStorage.getItem("snsKitchenPayload") || "{}");
    const eaterProfiles = {
      light: Number(form.querySelector("[data-eaters-light]")?.value || 0),
      standard: Number(form.querySelector("[data-eaters-standard]")?.value || 0),
      big: Number(form.querySelector("[data-eaters-big]")?.value || 0)
    };
    const people = eaterProfiles.light + eaterProfiles.standard + eaterProfiles.big;
    const payload = {
      mode: "build_your_meal",
      kitchen,
      selections: {
        proteins: [...form.querySelectorAll('input[name="protein"]:checked')].map((input, index) => {
          const name = input.value;
          const key = name.toLowerCase();
          return {
            name,
            state: input.closest("[data-protein-choice]")?.querySelector("[data-protein-state]")?.value || "Fresh Raw",
            role: index === 0 ? "main" : /bean|lentil|chickpea/.test(key) ? "stretch" : /bacon|sausage|ham|chorizo/.test(key) ? "accent" : "supporting"
          };
        }),
        produce: [...form.querySelectorAll('input[name="produce"]:checked')].map(item => item.value),
        produce_forms: Object.fromEntries([...form.querySelectorAll('input[name="produce"]:checked')].map(item => [
          item.value, item.closest("[data-produce-choice]")?.querySelector("[data-produce-form]")?.value || ""
        ])),
        extras: [...form.querySelectorAll('input[name="extras"]:checked')].map(item => item.value),
        foundation: form.querySelector("[data-builder-foundation]").value,
        cuisine: form.querySelector("[data-builder-cuisine]").value,
        cooking_method: form.querySelector('input[name="cooking-method"]:checked')?.value,
        meal_structure: form.querySelector('input[name="meal-structure"]:checked')?.value,
        serving_temperature: form.querySelector('input[name="temperature"]:checked')?.value,
        meal_occasion: form.querySelector("[data-meal-occasion]").value,
        energy: form.querySelector("[data-builder-energy]").value,
        time_minutes: Number(form.querySelector("[data-builder-time]").value),
        servings: people,
        eater_profiles: eaterProfiles,
        use_all_cans: Boolean(form.querySelector("[data-use-all-cans]")?.checked)
      }
    };
    if (!payload.selections.proteins.length) {
      status.textContent = "Choose at least one protein first.";
      form.querySelector('input[name="protein"]')?.focus();
      return;
    }
    if (payload.selections.proteins.length > 1 && payload.selections.cooking_method !== "skillet") {
      status.textContent = "Multiple-protein planning is trained for Stovetop Meal first. Choose Stovetop Meal for this combination.";
      form.querySelector('input[name="cooking-method"][value="skillet"]')?.focus();
      return;
    }
    if (people < 1) {
      status.textContent = "Add at least one person to the meal.";
      form.querySelector("[data-eaters-standard]")?.focus();
      return;
    }
    button.disabled = true;
    status.textContent = "Building your meal…";
    try {
      const response = await postJson(API.getRecipeList, payload);
      const candidate = response.candidates?.[0];
      if (!candidate) throw new Error(response.notices?.[0]?.message || "No trained plan matched those choices.");
      sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
      sessionStorage.setItem("snsRecipeChoices", JSON.stringify([candidate]));
      await requestRecipe(candidate.candidate_id || candidate.id);
    } catch (error) {
      status.textContent = error.message || "The meal could not be built yet. Try another method or ingredient.";
    } finally {
      button.disabled = false;
    }
  }

  function renderRecipeChoices() {
    const holder = document.querySelector("[data-recipe-grid]");
    if (!holder) return;
    const recipes = JSON.parse(sessionStorage.getItem("snsRecipeChoices") || "[]");
    const kitchen = JSON.parse(sessionStorage.getItem("snsKitchenPayload") || "{}");
    document.querySelector("[data-kitchen-summary]").textContent =
      `${kitchen.inventory?.length || 0} kitchen items were sent to GetRecipeList.`;

    holder.innerHTML = recipes.map(recipe => `
      <article class="recipe-card">
        <div class="recipe-art"></div>
        <div class="recipe-body">
          ${recipe.selection_badge ? `<span class="selection-badge">${escapeHtml(recipe.selection_badge)}</span>` : ""}
          <div class="meta">
            <span class="pill">${escapeHtml(recipe.total_minutes || recipe.minutes || "Flexible")} min</span>
            <span class="pill">Effort ${escapeHtml(recipe.effort_label || recipe.effort || "Practical")}</span>
            <span class="pill">${escapeHtml(recipe.match || "Match")}</span>
          </div>
          <h2>${escapeHtml(recipe.title)}</h2>
          <p>${escapeHtml(recipe.summary || "")}</p>
          <div class="meta">
            <span class="pill">${escapeHtml(recipe.meal_shape || "meal")}</span>
            <span class="pill">${escapeHtml(recipe.production_label || "Practical plan")}</span>
            <span class="pill">${escapeHtml(recipe.serving_temperature || "")}</span>
          </div>
          <button class="btn btn-primary" data-recipe-id="${escapeHtml(recipe.candidate_id || recipe.id)}">Make this recipe</button>
        </div>
      </article>`).join("");

    holder.querySelectorAll("[data-recipe-id]").forEach(button => {
      button.addEventListener("click", () => requestRecipe(button.dataset.recipeId));
    });
  }

  async function requestRecipe(recipeId) {
    const kitchen = JSON.parse(sessionStorage.getItem("snsKitchenPayload") || "{}");
    const request = { candidate_id: recipeId, recipe_id: recipeId, kitchen };
    sessionStorage.setItem("snsRecipeRequest", JSON.stringify(request));
    let recipe;
    const choices = JSON.parse(sessionStorage.getItem("snsRecipeChoices") || "[]");
    const selectedChoice = choices.find(r => (r.candidate_id || r.id) === recipeId) || {};
    try {
      recipe = await postJson(API.getRecipe, request);
    } catch {
      const choice = selectedChoice;
      recipe = {
        id: recipeId,
        title: choice.title || "Stock & Stir Recipe",
        summary: choice.summary || "A practical meal built from My Kitchen.",
        ingredients: (kitchen.inventory || []).slice(0, 8).map(item => `${item.name} — ${item.quantity} ${item.unit}`),
        steps: [
          "Gather the selected ingredients and the equipment you need.",
          "Prep the protein and vegetables before the main cooking begins.",
          "Start anything that needs extra cooking time first, then add quick-cooking ingredients closer to the end.",
          "Taste, adjust the seasoning, and serve when everything is safely cooked and ready."
        ],
        total_minutes: choice.minutes || 35
      };
    }
    recordMealHistory({...selectedChoice, ...recipe});
    sessionStorage.setItem("snsGeneratedRecipe", JSON.stringify(recipe));
    location.href = "recipe.html";
  }

  function renderRecipe() {
    const recipe = JSON.parse(sessionStorage.getItem("snsGeneratedRecipe") || "{}");
    if (!document.querySelector("[data-recipe-title]")) return;
    document.querySelector("[data-recipe-title]").textContent = recipe.title || "Your recipe";
    document.querySelector("[data-recipe-summary]").textContent = recipe.summary || "";
    document.querySelector("[data-recipe-time]").textContent = recipe.total_minutes ? `${recipe.total_minutes} minutes` : "Flexible timing";
    document.querySelector("[data-ingredients]").innerHTML = (recipe.ingredients || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");
    const kitchenItems = (recipe.inventory_requirements || [])
      .filter(item => ["Need", "Substitute", "Omit"].includes(item?.status))
      .filter(item => item.status !== "Omit" || item.omission_consequence)
      .map(item => {
        if (item.status === "Substitute") {
          return `${item.name} — use ${item.resolved_name}.`;
        }
        if (item.status === "Omit") {
          return `${item.name} — omit it. ${item.omission_consequence || "The meal remains valid without it."}`;
        }
        const options = (item.substitutions || []).length
          ? ` Possible substitutes: ${item.substitutions.join(", ")}.`
          : "";
        return `${item.name} — not listed in My Kitchen.${options}`;
      });
    const kitchenCheck = document.querySelector("[data-kitchen-check]");
    if (kitchenCheck && kitchenItems.length) {
      kitchenCheck.hidden = false;
      document.querySelector("[data-missing-items]").innerHTML = kitchenItems
        .map(item => `<li>${escapeHtml(item)}</li>`).join("");
    }
    const planItems = Array.isArray(recipe.plan_items) && recipe.plan_items.length
      ? recipe.plan_items
      : (recipe.steps || recipe.instructions || []).map(text => ({ kind: "action", text }));
    let actionNumber = 0;
    document.querySelector("[data-steps]").innerHTML = planItems.map(item => {
      const text = escapeHtml(item.text || "");
      if (item.kind === "info") {
        return `<div class="plan-info"><span class="plan-info-marker" aria-hidden="true">•</span><p>${text}</p></div>`;
      }
      actionNumber += 1;
      return `<div class="plan-action"><span class="plan-action-number">${actionNumber}</span><p>${text}</p></div>`;
    }).join("");

    const provenance = recipe.build_provenance;
    const provenancePanel = document.querySelector("[data-build-provenance]");
    if (provenancePanel && provenance?.build_id) {
      const git = provenance.git || {};
      provenancePanel.hidden = false;
      document.querySelector("[data-build-summary]").textContent =
        `Test provenance · ${provenance.build_id} · commit ${git.commit || "unavailable"}`;
      document.querySelector("[data-build-configuration]").innerHTML = Object.entries(provenance.configuration || {})
        .map(([key, value]) => `<div><dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${escapeHtml(Array.isArray(value) ? value.join(", ") : value)}</dd></div>`)
        .join("");
      document.querySelector("[data-build-files]").innerHTML = (provenance.files || [])
        .map(file => `<li><span>${escapeHtml(file.path)}</span><code>${escapeHtml(file.sha256)}</code></li>`)
        .join("");
    }
  }

  async function checkout(plan) {
    try {
      const response = await postJson(API.createCheckout, {
        plan,
        success_url: `${location.origin}/subscription-success.html`,
        cancel_url: `${location.origin}/subscription-canceled.html`
      });
      if (response.url) location.href = response.url;
    } catch {
      alert(`Stripe Checkout placeholder: ${plan}. Connect ${API.createCheckout} to redirect to a Stripe-hosted Checkout Session.`);
    }
  }

  async function billingPortal() {
    try {
      const response = await postJson(API.billingPortal, { return_url: location.href });
      if (response.url) location.href = response.url;
    } catch {
      alert(`Stripe Billing Portal placeholder. Connect ${API.billingPortal}.`);
    }
  }

  function init() {
    installAppShell();
    upgradeQuantityEditors();
    restoreBrowserKitchen();
    organizeInventory();
    bindAmounts();
    bindKitchenDashboard();
    updateCount();
    renderRecipeChoices();
    renderRecipe();
    renderMealBuilder();
    renderHome();
    document.querySelector("[data-save-kitchen]")?.addEventListener("click", saveKitchen);
    document.querySelector("[data-get-recipes]")?.addEventListener("click", generateRecipeList);
    document.querySelector("[data-build-meal]")?.addEventListener("click", openMealBuilder);
    document.querySelector("[data-signature-recipes]")?.addEventListener("click", openSignatureRecipes);
    document.querySelectorAll("[data-checkout]").forEach(b => b.addEventListener("click", () => checkout(b.dataset.checkout)));
    document.querySelector("[data-billing-portal]")?.addEventListener("click", billingPortal);
    runRequestedKitchenAction();
  }

  return { init, kitchenPayload, API };
})();
document.addEventListener("DOMContentLoaded", SNS.init);
