const SNS = (() => {
  const runtime = window.SNS_CONFIG || {};
  const apiBase = String(runtime.apiBaseUrl || "https://sns-api-xsq4.onrender.com").replace(/\/$/, "");
  const endpoint = path => `${apiBase}${path}`;
  const API = {
    myKitchen: endpoint("/api/MyKitchen"),
    saveKitchen: endpoint("/api/SaveMyKitchen"),
    resolveBarcode: endpoint("/api/ResolveBarcode"),
    recognizePantryPhoto: endpoint("/api/RecognizePantryPhoto"),
    getMealBuilderOptions: endpoint("/api/GetMealBuilderOptions"),
    getRecipeList: endpoint("/api/GetRecipeList"),
    getRecipe: endpoint("/api/GetRecipe"),
    reportRecipe: endpoint("/api/ReportRecipe"),
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
  const kitchenImportUndoKey = "snsKitchenImportUndoV1";
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
      if (href.startsWith("choose-recipe.html")) return page === "choose-recipe.html";
      if (href === "build-your-meal.html") return page === "build-your-meal.html";
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
        ${link("choose-recipe.html?refresh=1", "Give Me Meal Ideas", "meal-action")}
        ${link("build-your-meal.html", "Help Me Build My Meal", "meal-action")}
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

  async function renderHome() {
    const target = document.querySelector("[data-welcome-name]");
    if (!target) return;
    let session = null;
    try { session = await window.SNS_AUTH?.session?.(); } catch {}
    const metadataName = String(session?.user?.user_metadata?.display_name || "").trim();
    const emailName = String(session?.user?.email || "").split("@")[0].replace(/[._-]+/g, " ").trim();
    target.textContent = metadataName || emailName || "there";
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
    if (action === "ideas") location.replace("choose-recipe.html?refresh=1");
    if (action === "builder") location.replace("build-your-meal.html");
  }

  function savedKitchenState() {
    try { return JSON.parse(localStorage.getItem(kitchenStorageKey) || "{}") || {}; }
    catch { return {}; }
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
    const allowed = [...new Set([
      ...allowedUnits(name),
      ...(inventoryUnits.some(([value]) => value === selected) ? [selected] : [])
    ])];
    const safeSelected = allowed.includes(selected) ? selected : allowed[0];
    return inventoryUnits.filter(([value]) => allowed.includes(value)).map(([value, label]) =>
      `<option value="${value}"${value === safeSelected ? " selected" : ""}>${label}</option>`
    ).join("");
  }

  async function authorizationHeaders() {
    const token = await window.SNS_AUTH?.accessToken?.();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function responseJson(response) {
    if (!response.ok) {
      const raw = await response.text();
      let message = raw;
      try {
        const body = JSON.parse(raw);
        message = body.detail || body.message || raw;
      } catch {
        // Keep a plain-text service response as-is.
      }
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  async function getJson(url) {
    const response = await fetch(url, { headers: await authorizationHeaders() });
    return responseJson(response);
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await authorizationHeaders()) },
      body: JSON.stringify(payload)
    });
    return responseJson(response);
  }

  function kitchenPayload() {
    const saved = savedKitchenState();
    const foodRows = [...document.querySelectorAll("[data-food]")];
    const items = foodRows.map(row => {
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
    const memberRows = [...document.querySelectorAll("[data-household-member]")];
    const householdMembers = memberRows.map(row => ({
      name: row.querySelector("[data-member-name]")?.value.trim() || "Household member",
      appetite: row.querySelector("[data-member-appetite]")?.value || "standard"
    }));
    const inventory = foodRows.length ? items : (saved.foods || []).filter(item => Number(item.quantity || 0) > 0);
    const members = memberRows.length ? householdMembers : (saved.household_members || []);
    const equipmentButtons = [...document.querySelectorAll("[data-equipment]")];
    const equipment = equipmentButtons.length
      ? equipmentButtons.filter(button => button.classList.contains("active")).map(button => ({
          name: button.dataset.equipment,
          available: true
        }))
      : (saved.equipment || []).filter(item => item.active).map(item => ({name: item.name, available: true}));
    const effort = document.querySelector("[data-make-effort]")?.value || saved.tonight_effort || "Low";

    return {
      api_version: "1.0",
      contract_version: "my-kitchen-v1",
      household_id: saved.household_id || "local-demo-household",
      generated_at: new Date().toISOString(),
      servings: members.length || 4,
      energy: effort,
      effort,
      inventory,
      equipment,
      meal_preferences: {
        household_members: members,
        excluded_items: (saved.preferences || [])
          .filter(item => ["allergy", "medical_exclusion", "religious_exclusion", "exclusion"].includes(item.preference_type))
          .filter(item => ["never", "avoid"].includes(item.severity))
          .map(item => item.target_value),
        stored_preferences: saved.preferences || [],
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
    "Cornstarch", "Eggs", "Garlic", "Ground beef", "Kale", "Lasagna noodles", "Mayonnaise", "Milk", "Mushrooms",
    "Navy beans", "Okra", "Onions", "Potatoes", "Romaine lettuce", "Salsa", "Spaghetti", "Spinach",
    "Ribeye steak", "Swiss chard", "Tomatoes", "Vegetable oil", "White beans", "White rice", "Zucchini"
  ];
  const kitchenAliases = {
    "chikn brest": "Chicken breast", "chicken breasts": "Chicken breast", "chikn breast": "Chicken breast",
    "zukini": "Zucchini", "zuchini": "Zucchini", "zuccini": "Zucchini", "mayo": "Mayonnaise",
    "ribeye": "Ribeye steak", "rib eye": "Ribeye steak", "corn starch": "Cornstarch",
    "cooking oil": "Vegetable oil"
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
      ...(window.SNS_SAMPLE_PANTRIES || []).flatMap(sample => sample.items.map(item => item.name)),
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

  function knownKitchenNames() {
    return new Set([
      ...commonKitchenCatalog,
      ...(window.SNS_SAMPLE_PANTRIES || []).flatMap(sample => sample.items.map(item => item.name)),
      ...[...document.querySelectorAll("[data-food]")].map(row => row.dataset.food)
    ].map(normalizedFoodName));
  }

  function parseCsv(text) {
    const rows = [];
    let row = [], cell = "", quoted = false;
    const input = String(text || "").replace(/^\uFEFF/, "");
    for (let index = 0; index < input.length; index += 1) {
      const character = input[index];
      if (character === '"' && quoted && input[index + 1] === '"') { cell += '"'; index += 1; }
      else if (character === '"') quoted = !quoted;
      else if (character === "," && !quoted) { row.push(cell); cell = ""; }
      else if ((character === "\n" || character === "\r") && !quoted) {
        if (character === "\r" && input[index + 1] === "\n") index += 1;
        row.push(cell); cell = "";
        if (row.some(value => value.trim())) rows.push(row);
        row = [];
      } else cell += character;
    }
    if (quoted) throw new Error("The CSV has an unclosed quoted value.");
    row.push(cell);
    if (row.some(value => value.trim())) rows.push(row);
    if (rows.length < 2) throw new Error("The CSV needs a header row and at least one pantry item.");
    const headers = rows.shift().map(value => normalizedFoodName(value).replaceAll(" ", "_"));
    return rows.map((values, index) => ({
      rowNumber: index + 2,
      ...Object.fromEntries(headers.map((header, column) => [header, String(values[column] || "").trim()]))
    }));
  }

  function normalizeInventoryUnit(value) {
    const aliases = {
      items: "item", cans: "can", jars: "jar", boxes: "box", bags: "bag", packages: "package",
      eggs: "egg", pieces: "piece", pound: "lb", pounds: "lb", lbs: "lb", ounces: "oz",
      cups: "cup", cartons: "carton", bottles: "bottle", bunches: "bunch", head: "piece", heads: "piece",
      pints: "package", tubs: "package", loaves: "loaf", portions: "portion", meals: "meal"
    };
    const unit = String(value || "").trim().toLowerCase();
    return aliases[unit] || unit;
  }

  function normalizeStorageLocation(value, form = "") {
    const storage = normalizedFoodName(value);
    if (storage === "pantry" || storage === "shelf stable") return "Pantry";
    if (storage === "fridge" || storage === "refrigerator" || storage === "refrigerated") return "Fridge";
    if (storage === "freezer" || storage === "frozen") return "Freezer";
    if (storage === "fresh" || storage === "counter") return "Fresh";
    const kind = normalizedFoodName(form);
    if (kind.includes("frozen")) return "Freezer";
    if (kind.includes("refrigerated") || kind === "cooked") return "Fridge";
    if (kind === "fresh" || kind === "fresh raw") return "Fresh";
    return "Pantry";
  }

  function normalizeImportRows(rows, source = "CSV") {
    if (rows.length > 500) throw new Error("Import up to 500 pantry rows at a time.");
    const known = knownKitchenNames();
    const errors = [];
    const items = rows.map((row, index) => {
      const originalName = String(row.name || row.ingredient_name || "").trim();
      const canonicalName = canonicalFoodName(originalName);
      const quantity = Number(row.quantity);
      const unit = normalizeInventoryUnit(row.unit);
      const form = String(row.form || "").trim() || defaultForms[normalizeStorageLocation(row.storage_location || row.storage)] || "On hand";
      const storage_location = normalizeStorageLocation(row.storage_location || row.storage, form);
      const rowNumber = row.rowNumber || index + 2;
      if (!originalName) errors.push(`Row ${rowNumber}: ingredient name is required.`);
      if (!Number.isFinite(quantity) || quantity <= 0) errors.push(`Row ${rowNumber}: quantity must be greater than zero.`);
      if (!inventoryUnits.some(([value]) => value === unit)) errors.push(`Row ${rowNumber}: “${row.unit || ""}” is not a supported unit.`);
      return {
        name: canonicalName, originalName, form, storage_location, quantity, unit,
        origin: row.origin || source, notes: row.notes || "",
        unresolved: Boolean(originalName && !known.has(normalizedFoodName(canonicalName)))
      };
    });
    if (errors.length) throw new Error(errors.slice(0, 8).join("\n"));
    return items;
  }

  function browserKitchenState() {
    const saved = savedKitchenState();
    const foodRows = [...document.querySelectorAll("[data-food]")];
    const equipmentButtons = [...document.querySelectorAll("[data-equipment]")];
    const memberRows = [...document.querySelectorAll("[data-household-member]")];
    const preferenceInputs = [...document.querySelectorAll("[data-preference-type]")];
    const preferences = preferenceInputs.length
      ? preferenceInputs.flatMap(input => String(input.value || "").split(/[,\n]/).map(value => value.trim()).filter(Boolean).map(value => ({
          preference_type: input.dataset.preferenceType,
          target_type: input.dataset.targetType || "ingredient",
          target_value: value,
          severity: input.dataset.severity || "avoid",
          notes: ""
        })))
      : (saved.preferences || []);
    return {
      household_id: saved.household_id || null,
      foods: foodRows.length ? foodRows.map(row => ({
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
      })) : (saved.foods || []),
      equipment: equipmentButtons.length ? equipmentButtons.map(button => ({
        name: button.dataset.equipment,
        active: button.classList.contains("active"),
        custom: button.dataset.custom === "true"
      })) : (saved.equipment || []),
      household_members: memberRows.length ? memberRows.map(row => ({
        name: row.querySelector("[data-member-name]")?.value || "",
        appetite: row.querySelector("[data-member-appetite]")?.value || "standard"
      })) : (saved.household_members || []),
      preferences,
      tonight_effort: document.querySelector("[data-make-effort]")?.value || saved.tonight_effort || "Low"
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
      <label class="quantity-value">
        <span class="sr-only">${escapeHtml(name)} quantity</span>
        <input data-quantity type="number" min="0" step="${quantityStepForUnit(selectedUnit)}" inputmode="decimal" value="${Number(quantity) || 0}">
      </label>
      <label class="quantity-unit">
        <span class="sr-only">${escapeHtml(name)} unit</span>
        <select data-unit>${unitOptions(selectedUnit, name)}</select>
      </label>
      <details class="inventory-detail" data-inventory-detail>
        <summary>More details</summary>
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

  function applyImportedPantry(items, mode) {
    localStorage.setItem(kitchenImportUndoKey, JSON.stringify({ saved_at: new Date().toISOString(), state: browserKitchenState() }));
    if (mode === "replace") {
      document.querySelectorAll("[data-food]").forEach(row => {
        if (row.dataset.custom === "true") row.remove();
        else setRowQuantity(row, 0);
      });
    }
    items.forEach(item => {
      const storage = normalizeStorageLocation(item.storage_location, item.form);
      let row = findFoodRow(item.name, storage);
      if (!row) {
        row = createFoodRow({
          name: item.name, storage, form: item.form, quantity: item.quantity,
          unit: item.unit, custom: true
        });
        document.querySelector(`[data-section="${storage}"] .item-list`)?.append(row);
        bindQuantityEditor(row.querySelector(".amount"));
        ensureRemoveControl(row);
      } else {
        row.dataset.form = item.form || row.dataset.form;
        const note = row.querySelector(".food-note");
        if (note && item.form) note.textContent = item.form;
        setRowQuantity(row, item.quantity, item.unit);
      }
    });
    organizeInventory();
    bindAmounts();
    updateCount();
    storeBrowserKitchen();
  }

  function bindPantryImporter() {
    const dialog = document.querySelector("[data-pantry-import-dialog]");
    if (!dialog) return;
    const samples = window.SNS_SAMPLE_PANTRIES || [];
    const sampleSelect = dialog.querySelector("[data-sample-pantry-select]");
    const csvInput = dialog.querySelector("[data-pantry-csv]");
    const preview = dialog.querySelector("[data-pantry-import-preview]");
    const previewItems = dialog.querySelector("[data-import-preview-items]");
    const unresolvedPanel = dialog.querySelector("[data-import-unresolved]");
    const unresolvedItems = dialog.querySelector("[data-import-unresolved-items]");
    const confirmCustom = dialog.querySelector("[data-confirm-custom-items]");
    const applyButton = dialog.querySelector("[data-apply-pantry-import]");
    const error = dialog.querySelector("[data-pantry-import-error]");
    const description = dialog.querySelector("[data-sample-pantry-description]");
    let pendingItems = [];

    samples.forEach(sample => {
      const option = document.createElement("option");
      option.value = sample.id;
      option.textContent = sample.label;
      sampleSelect.append(option);
    });

    function setError(message = "") {
      error.hidden = !message;
      error.textContent = message;
    }

    function refreshApplyState() {
      const hasUnresolved = pendingItems.some(item => item.unresolved);
      applyButton.disabled = !pendingItems.length || (hasUnresolved && !confirmCustom.checked);
    }

    function showPreview(items, title, detail = "") {
      pendingItems = items;
      setError();
      preview.hidden = false;
      dialog.querySelector("[data-import-preview-title]").textContent = title;
      dialog.querySelector("[data-import-preview-count]").textContent = `${items.length} items · ${items.filter(item => item.unresolved).length} need review`;
      description.textContent = detail || "Review the imported quantities and storage locations before applying them.";
      previewItems.innerHTML = items.map(item => `
        <article class="pantry-import-item${item.unresolved ? " unresolved" : ""}">
          <span><strong>${escapeHtml(item.name || item.originalName)}</strong><small>${escapeHtml(item.form)} · ${escapeHtml(item.storage_location)}</small></span>
          <b>${escapeHtml(item.quantity)} ${escapeHtml(item.quantity === 1 ? item.unit : (inventoryUnits.find(([value]) => value === item.unit)?.[1] || item.unit))}</b>
        </article>`).join("");
      const unresolved = items.filter(item => item.unresolved);
      unresolvedPanel.hidden = !unresolved.length;
      unresolvedItems.innerHTML = unresolved.map(item => `<span>${escapeHtml(item.originalName)}</span>`).join("");
      confirmCustom.checked = false;
      refreshApplyState();
    }

    sampleSelect.addEventListener("change", () => {
      const sample = samples.find(item => item.id === sampleSelect.value);
      if (!sample) {
        pendingItems = [];
        preview.hidden = true;
        description.textContent = "Select a sample to see its ingredients, or upload a CSV with name, quantity, and unit columns.";
        refreshApplyState();
        return;
      }
      csvInput.value = "";
      try { showPreview(normalizeImportRows(sample.items, `sample:${sample.id}`), sample.label, sample.description); }
      catch (caught) { setError(caught.message); }
    });

    csvInput.addEventListener("change", async () => {
      const file = csvInput.files?.[0];
      if (!file) return;
      sampleSelect.value = "";
      try {
        if (file.size > 1024 * 1024) throw new Error("Choose a CSV smaller than 1 MB.");
        const rows = parseCsv(await file.text());
        showPreview(normalizeImportRows(rows, `csv:${file.name}`), file.name, "CSV preview. Unknown names are held for your confirmation.");
      } catch (caught) {
        pendingItems = [];
        preview.hidden = true;
        setError(caught.message || "The CSV could not be read.");
        refreshApplyState();
      }
    });

    confirmCustom.addEventListener("change", refreshApplyState);
    document.querySelector("[data-open-pantry-import]")?.addEventListener("click", () => dialog.showModal());
    dialog.querySelectorAll("[data-close-pantry-import]").forEach(button => button.addEventListener("click", () => dialog.close()));
    applyButton.addEventListener("click", async () => {
      if (!pendingItems.length || applyButton.disabled) return;
      const mode = dialog.querySelector('input[name="pantry-import-mode"]:checked')?.value || "merge";
      applyButton.disabled = true;
      applyImportedPantry(pendingItems, mode);
      dialog.close();
      const undo = document.querySelector("[data-pantry-import-undo]");
      if (undo) {
        undo.hidden = false;
        undo.querySelector("[data-pantry-import-undo-message]").textContent = `${pendingItems.length} pantry items ${mode === "replace" ? "replaced" : "merged into"} My Kitchen.`;
      }
      await saveKitchen();
      refreshApplyState();
    });

    const undo = document.querySelector("[data-pantry-import-undo]");
    if (localStorage.getItem(kitchenImportUndoKey) && undo) undo.hidden = false;
    document.querySelector("[data-undo-pantry-import]")?.addEventListener("click", async () => {
      let snapshot;
      try { snapshot = JSON.parse(localStorage.getItem(kitchenImportUndoKey) || "null"); } catch { snapshot = null; }
      if (!snapshot?.state) return;
      localStorage.setItem(kitchenStorageKey, JSON.stringify(snapshot.state));
      localStorage.removeItem(kitchenImportUndoKey);
      sessionStorage.setItem("snsKitchenUndoNeedsSave", "1");
      location.reload();
    });
  }

  function captureUnitOptions(selected = "package") {
    const known = inventoryUnits.some(([value]) => value === selected) ? selected : "package";
    return inventoryUnits.map(([value, label]) =>
      `<option value="${value}"${value === known ? " selected" : ""}>${label}</option>`
    ).join("");
  }

  async function pantryPhotoDataUrl(file) {
    if (!file || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      throw new Error("Choose a JPEG, PNG, or WebP photo.");
    }
    if (file.size > 15 * 1024 * 1024) throw new Error("Choose a photo smaller than 15 MB.");
    const objectUrl = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.decoding = "async";
      image.src = objectUrl;
      await image.decode();
      const longest = Math.max(image.naturalWidth, image.naturalHeight);
      const scale = Math.min(1, 1600 / longest);
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      canvas.getContext("2d", { alpha: false }).drawImage(image, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", .78);
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  }

  function bindInventoryCapture() {
    const dialog = document.querySelector("[data-inventory-capture-dialog]");
    if (!dialog) return;
    const barcodePanel = dialog.querySelector("[data-capture-barcode]");
    const photoPanel = dialog.querySelector("[data-capture-photo]");
    const barcodeInput = dialog.querySelector("[data-capture-barcode-input]");
    const lookupButton = dialog.querySelector("[data-lookup-barcode]");
    const cameraButton = dialog.querySelector("[data-start-barcode-camera]");
    const cameraHolder = dialog.querySelector("[data-barcode-camera]");
    const video = dialog.querySelector("[data-barcode-video]");
    const photoInput = dialog.querySelector("[data-pantry-photo]");
    const photoButton = dialog.querySelector("[data-recognize-pantry-photo]");
    const progress = dialog.querySelector("[data-capture-progress]");
    const error = dialog.querySelector("[data-capture-error]");
    const review = dialog.querySelector("[data-capture-review]");
    const reviewItems = dialog.querySelector("[data-capture-review-items]");
    const applyButton = dialog.querySelector("[data-apply-captured-items]");
    let stream = null;
    let scanning = false;

    async function barcodeDetectorClass() {
      if ("BarcodeDetector" in window) return window.BarcodeDetector;
      try {
        const module = await import("https://cdn.jsdelivr.net/npm/@undecaf/barcode-detector-polyfill@0.9.23/dist/main.js");
        window.BarcodeDetector = module.BarcodeDetectorPolyfill;
        return window.BarcodeDetector;
      } catch {
        return null;
      }
    }

    function setError(message = "") {
      error.hidden = !message;
      error.textContent = message;
    }

    function setBusy(busy, message = "Reading the items…") {
      progress.hidden = !busy;
      progress.textContent = message;
      lookupButton.disabled = busy;
      photoButton.disabled = busy || !photoInput.files?.[0];
    }

    function selectedItems() {
      return [...reviewItems.querySelectorAll("[data-capture-item]")]
        .filter(row => row.querySelector("[data-capture-include]").checked)
        .map(row => ({
          name: row.querySelector("[data-capture-name]").value.trim(),
          form: row.querySelector("[data-capture-form]").value.trim(),
          storage_location: row.querySelector("[data-capture-storage]").value,
          quantity: Number(row.querySelector("[data-capture-quantity]").value || 1),
          unit: row.querySelector("[data-capture-unit]").value,
          unresolved: row.dataset.status !== "matched"
        })).filter(item => item.name && item.quantity > 0);
    }

    function refreshApply() {
      applyButton.disabled = selectedItems().length === 0;
    }

    function showReview(payload) {
      const items = Array.isArray(payload?.items) ? payload.items : [];
      if (!items.length) throw new Error("No items were clear enough to review.");
      review.hidden = false;
      dialog.querySelector("[data-capture-review-summary]").textContent =
        `${items.length} ${items.length === 1 ? "item" : "items"} found. Confirm only what is really there.`;
      reviewItems.innerHTML = items.map((item, index) => {
        const needsReview = item.status !== "matched" || Number(item.confidence) < .75;
        const existing = item.already_on_hand
          ? `<span class="capture-existing">Already in My Kitchen: ${escapeHtml(item.existing_quantity)} ${escapeHtml(item.existing_unit || "")}</span>` : "";
        return `<article class="capture-review-item${needsReview ? " needs-review" : ""}" data-capture-item data-status="${escapeHtml(item.status)}">
          <label class="capture-include"><input type="checkbox" data-capture-include${needsReview ? "" : " checked"}><span class="sr-only">Include item ${index + 1}</span></label>
          <div class="capture-item-fields">
            <label class="capture-name"><span>Item</span><input data-capture-name value="${escapeHtml(item.name)}" autocomplete="off"></label>
            <label><span>Form</span><input data-capture-form value="${escapeHtml(item.form)}" placeholder="Canned, fresh, frozen…"></label>
            <label><span>Stored in</span><select data-capture-storage>${["Pantry", "Fridge", "Freezer", "Fresh"].map(value => `<option${value === item.storage_location ? " selected" : ""}>${value}</option>`).join("")}</select></label>
            <label><span>Amount</span><input data-capture-quantity type="number" inputmode="decimal" min="0.25" step="0.25" value="${escapeHtml(item.quantity || 1)}"></label>
            <label><span>Unit</span><select data-capture-unit>${captureUnitOptions(item.unit)}</select></label>
          </div>
          <div class="capture-item-note"><span>${needsReview ? "Please check this match" : "Strong catalog match"}</span>${existing}</div>
        </article>`;
      }).join("");
      reviewItems.querySelectorAll("input,select").forEach(input => input.addEventListener("input", refreshApply));
      refreshApply();
    }

    async function signedIn() {
      try {
        return Boolean(await window.SNS_AUTH?.session?.());
      } catch {
        return false;
      }
    }

    function stopCamera() {
      scanning = false;
      (stream?.getTracks?.() || []).forEach(track => track.stop());
      stream = null;
      video.srcObject = null;
      cameraHolder.hidden = true;
      cameraButton.textContent = "Use phone camera";
    }

    async function lookupBarcode() {
      const barcode = barcodeInput.value.replace(/\D/g, "");
      if (barcode.length < 8 || barcode.length > 14) {
        setError("Enter or scan an 8- to 14-digit barcode.");
        return;
      }
      stopCamera();
      setError();
      review.hidden = true;
      setBusy(true, "Looking up that package…");
      try {
        showReview(await postJson(API.resolveBarcode, { barcode }));
      } catch (caught) {
        setError(caught.message || "That barcode could not be read. Enter the item manually instead.");
      } finally {
        setBusy(false);
      }
    }

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("This browser cannot open the camera. Type the barcode numbers above instead.");
        return;
      }
      if (stream) return stopCamera();
      setError();
      try {
        cameraButton.disabled = true;
        cameraButton.textContent = "Preparing camera…";
        const Detector = await barcodeDetectorClass();
        if (!Detector) throw new Error("barcode decoder unavailable");
        const supported = await Detector.getSupportedFormats?.() || [];
        const wanted = ["ean_13", "ean_8", "upc_a", "upc_e"].filter(format => !supported.length || supported.includes(format));
        const detector = new Detector(wanted.length ? { formats: wanted } : undefined);
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        video.srcObject = stream;
        await video.play();
        cameraHolder.hidden = false;
        cameraButton.textContent = "Stop camera";
        scanning = true;
        const scan = async () => {
          if (!scanning) return;
          try {
            const codes = await detector.detect(video);
            const value = String(codes?.[0]?.rawValue || "").replace(/\D/g, "");
            if (value) {
              barcodeInput.value = value;
              await lookupBarcode();
              return;
            }
          } catch {
            // A frame can fail while autofocus settles; keep scanning.
          }
          if (scanning) requestAnimationFrame(scan);
        };
        requestAnimationFrame(scan);
      } catch {
        stopCamera();
        setError("Camera access was not available. Type the barcode numbers above instead.");
      } finally {
        cameraButton.disabled = false;
      }
    }

    async function recognizePhoto() {
      const file = photoInput.files?.[0];
      if (!file) return;
      setError();
      review.hidden = true;
      setBusy(true, "Preparing the photo on this device…");
      try {
        const imageDataUrl = await pantryPhotoDataUrl(file);
        progress.textContent = "Finding visible pantry items…";
        showReview(await postJson(API.recognizePantryPhoto, { image_data_url: imageDataUrl }));
      } catch (caught) {
        setError(caught.message || "The photo could not be read. Try a clearer photo or add the items manually.");
      } finally {
        setBusy(false);
      }
    }

    async function openCapture(mode) {
      setError();
      review.hidden = true;
      reviewItems.replaceChildren();
      applyButton.disabled = true;
      barcodePanel.hidden = mode !== "barcode";
      photoPanel.hidden = mode !== "photo";
      dialog.querySelector("[data-capture-title]").textContent = mode === "photo" ? "Add from a pantry photo" : "Scan a barcode";
      if (!(await signedIn())) {
        setError("Log in first so confirmed items can be saved to the same kitchen on every device.");
      }
      dialog.showModal();
      if (mode === "barcode") barcodeInput.focus();
    }

    document.querySelectorAll("[data-open-inventory-capture]").forEach(button =>
      button.addEventListener("click", () => openCapture(button.dataset.openInventoryCapture))
    );
    dialog.querySelectorAll("[data-close-inventory-capture]").forEach(button => button.addEventListener("click", () => dialog.close()));
    dialog.addEventListener("close", stopCamera);
    lookupButton.addEventListener("click", lookupBarcode);
    barcodeInput.addEventListener("keydown", event => {
      if (event.key === "Enter") { event.preventDefault(); lookupBarcode(); }
    });
    cameraButton.addEventListener("click", startCamera);
    photoInput.addEventListener("change", () => { photoButton.disabled = !photoInput.files?.[0]; });
    photoButton.addEventListener("click", recognizePhoto);
    dialog.querySelector("[data-select-all-capture]").addEventListener("click", () => {
      reviewItems.querySelectorAll("[data-capture-include]").forEach(input => { input.checked = true; });
      refreshApply();
    });
    applyButton.addEventListener("click", async () => {
      const items = selectedItems();
      if (!items.length) return;
      applyButton.disabled = true;
      applyImportedPantry(items, "merge");
      dialog.close();
      await saveKitchen();
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = `${items.length} reviewed ${items.length === 1 ? "item" : "items"} added to My Kitchen.`;
    });
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
    document.querySelectorAll("[data-preference-type]").forEach(input => {
      const values = (state.preferences || [])
        .filter(item => item.preference_type === input.dataset.preferenceType)
        .map(item => item.target_value)
        .filter(Boolean);
      input.value = values.join(", ");
    });
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
        if (!section.hidden) {
          section.classList.remove("collapsed");
          section.querySelector(".section-heading")?.setAttribute("aria-expanded", "true");
        }
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
      const opening = section.classList.contains("collapsed");
      document.querySelectorAll("[data-section]").forEach(other => {
        if (other === section) return;
        other.classList.add("collapsed");
        other.querySelector(".section-heading")?.setAttribute("aria-expanded", "false");
      });
      section.classList.toggle("collapsed", !opening);
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

  function initializeKitchenAccordion() {
    if (!document.body.classList.contains("kitchen-page")) return;
    const sections = [...document.querySelectorAll("[data-section]")];
    const requested = location.hash ? document.querySelector(location.hash) : null;
    sections.forEach((section, index) => {
      const collapsed = requested ? section !== requested : index !== 0;
      section.classList.toggle("collapsed", collapsed);
      section.querySelector(".section-heading")?.setAttribute("aria-expanded", String(!collapsed));
    });
  }

  function recipeServiceError(error) {
    return escapeHtml(error?.message || "The cooking service did not return a recipe.");
  }

  async function hydrateSharedKitchen() {
    if (!window.SNS_AUTH?.configured) return;
    let session;
    try { session = await window.SNS_AUTH.session(); }
    catch { return; }
    if (!session) return;

    try {
      let remote = await getJson(API.myKitchen);
      const local = savedKitchenState();
      const localFoods = (local.foods || []).filter(item => Number(item.quantity || 0) > 0);
      const remoteFoods = (remote.foods || remote.inventory || []).filter(item => Number(item.quantity || 0) > 0);
      const marker = `snsKitchenMigrated:${session.user.id}`;

      if (!remoteFoods.length && localFoods.length && !localStorage.getItem(marker)) {
        const move = window.confirm(
          `We found ${localFoods.length} foods saved on this device. Move them into your shared Stock & Stir kitchen so they appear on your phone and other devices?`
        );
        if (move) {
          remote = await postJson(API.saveKitchen, {
            ...local,
            inventory: localFoods,
            servings: (local.household_members || []).length || 4,
            energy: local.tonight_effort || "Low",
            effort: local.tonight_effort || "Low",
            sync_source_type: "browser_migration",
            sync_source_fingerprint: `browser-v1:${session.user.id}`
          });
        }
        localStorage.setItem(marker, move ? "moved" : "kept-local");
      }

      const sharedFoods = (remote.foods || remote.inventory || []).filter(item => Number(item.quantity || 0) > 0);
      if (sharedFoods.length || !localFoods.length) {
        localStorage.setItem(kitchenStorageKey, JSON.stringify(remote));
      }
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = "This kitchen is shared across your signed-in devices.";
    } catch (error) {
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = `Using this device's saved kitchen for now. ${error.message || "Shared sync is unavailable."}`;
    }
  }

  async function saveKitchen() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    storeBrowserKitchen();
    try {
      const response = await postJson(API.saveKitchen, {
        ...payload,
        preferences: browserKitchenState().preferences
      });
      if (response?.storage_mode === "supabase_household") {
        localStorage.setItem(kitchenStorageKey, JSON.stringify(response));
      }
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = document.querySelector("[data-save-household]")
        ? "Household preferences are saved to every signed-in device."
        : "My Kitchen is saved to every signed-in device.";
    } catch {
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = "Saved in this browser; API connection is pending.";
    }
  }

  async function generateRecipeList() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    try {
      const response = await postJson(API.getRecipeList, payload);
      const recipes = response.candidates || response.recipes || response;
      if (!Array.isArray(recipes) || !recipes.length) throw new Error("No trained meal matched My Kitchen yet.");
      sessionStorage.setItem("snsRecipeChoices", JSON.stringify(recipes));
      location.href = "choose-recipe.html";
    } catch (error) {
      const status = document.querySelector("[data-save-status]");
      if (status) status.textContent = error.message || "Meal ideas could not load. Please try again.";
    }
  }

  async function refreshRecipeChoices() {
    if (currentPage() !== "choose-recipe.html") return;
    const params = new URLSearchParams(location.search);
    const recipes = JSON.parse(sessionStorage.getItem("snsRecipeChoices") || "[]");
    if (params.get("refresh") !== "1" && recipes.length) return;
    history.replaceState({}, "", "choose-recipe.html");
    const holder = document.querySelector("[data-recipe-grid]");
    if (holder) holder.innerHTML = '<p class="recipe-loading">Finding genuinely different ideas from My Kitchen…</p>';
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    try {
      const response = await postJson(API.getRecipeList, payload);
      const choices = response.candidates || response.recipes || response;
      if (!Array.isArray(choices) || !choices.length) throw new Error("No trained meal matched My Kitchen yet.");
      sessionStorage.setItem("snsRecipeChoices", JSON.stringify(choices));
      renderRecipeChoices();
    } catch (error) {
      sessionStorage.removeItem("snsRecipeChoices");
      if (holder) holder.innerHTML = `
        <div class="recipe-service-error" role="alert">
          <strong>Meal ideas could not load.</strong>
          <p>${recipeServiceError(error)}</p>
          <button class="btn btn-primary" type="button" data-retry-recipes>Try again</button>
        </div>`;
      holder?.querySelector("[data-retry-recipes]")?.addEventListener("click", refreshRecipeChoices);
    }
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
    const kitchen = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(kitchen));
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
    } catch (error) {
      const loading = form.querySelector("[data-builder-loading]");
      if (loading) loading.textContent = `The meal builder could not load: ${error.message || "please try again."}`;
      return;
    }

    const proteinHolder = form.querySelector("[data-protein-options]");
    const inferProteinState = item => {
      return item.default_state || "Fresh Raw";
    };
    proteinHolder.innerHTML = (options.proteins || []).map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      const state = inferProteinState(item);
      return `<label class="produce-choice protein-choice${isOwned ? "" : " is-purchase"}" data-protein-choice data-owned="${isOwned}" data-protein-role-kind="${escapeHtml(item.suggested_role || "supporting")}" data-search-name="${escapeHtml(item.name.toLowerCase())}"${isOwned ? "" : " hidden"}>
        <input type="checkbox" name="protein" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small data-protein-role>${isOwned ? `In My Kitchen${item.form ? ` · ${escapeHtml(item.form)}` : ""}` : "Added to grocery list"}</small>
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
        const kind = input.closest("[data-protein-choice]").dataset.proteinRoleKind;
        const inferred = index === 0 ? "Main protein" :
          kind === "stretch" ? "Stretch protein" :
          kind === "accent" ? "Flavor accent" : "Supporting protein";
        role.textContent = `${inferred} · ${role.textContent.replace(/^(Main protein|Stretch protein|Flavor accent|Supporting protein) · /, "")}`;
      });
    };
    proteinHolder.addEventListener("change", syncProteinRoles);

    const foundation = form.querySelector("[data-builder-foundation]");
    foundation.innerHTML = `<option value="">No foundation</option>` + (options.foundations || []).map(item =>
      `<option value="${escapeHtml(item.name)}" data-owned="${Boolean(item.owned ?? owned.has(String(item.name).toLowerCase()))}"${item.owned ?? owned.has(String(item.name).toLowerCase()) ? "" : " hidden"}>${escapeHtml(item.name)}${item.owned ?? owned.has(String(item.name).toLowerCase()) ? " · In My Kitchen" : " · Grocery item"}</option>`
    ).join("");

    form.querySelector("[data-builder-cuisine]").innerHTML = (options.cuisines || []).map(name =>
      `<option value="${escapeHtml(name)}"${name === "Comfort Food" ? " selected" : ""}>${escapeHtml(name)}</option>`
    ).join("");

    form.querySelector("[data-method-options]").innerHTML = (options.methods || []).map((item, index) => `
      <label class="builder-choice-card${item.available === false ? " unavailable" : ""}">
        <input type="radio" name="cooking-method" value="${escapeHtml(item.id)}"${index === 0 ? " checked" : ""}${item.available === false ? " disabled" : ""}>
        <span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.note || item.description)}</small></span>
      </label>`).join("");
    const grillOption = (options.methods || []).find(item => item.id === "grill");
    const grillNote = form.querySelector("[data-grill-equipment-note]");
    if (grillNote) grillNote.hidden = grillOption?.available !== false;
    form.querySelector("[data-structure-options]").innerHTML = (options.meal_structures || []).map((item, index) => `
      <label class="builder-choice-card">
        <input type="radio" name="meal-structure" value="${escapeHtml(item.id)}"${index === 0 ? " checked" : ""}>
        <span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.description)}</small></span>
      </label>`).join("");
    const syncStructureGuidance = () => {
      const method = form.querySelector('input[name="cooking-method"]:checked')?.value;
      const structureInputs = [...form.querySelectorAll('input[name="meal-structure"]')];
      structureInputs.forEach(input => {
        input.disabled = !["skillet", "grill"].includes(method) && input.value !== "integrated";
      });
      if (structureInputs.find(input => input.checked)?.disabled) {
        structureInputs.find(input => input.value === "integrated").checked = true;
      }
      const structure = structureInputs.find(input => input.checked)?.value;
      const produceCount = form.querySelectorAll('input[name="produce"]:checked').length;
      const guidance = form.querySelector("[data-structure-guidance]");
      if (!["skillet", "grill"].includes(method)) {
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

    const produce = options.produce || [];
    const produceHolder = form.querySelector("[data-produce-options]");
    produceHolder.innerHTML = produce.map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      return `<label class="produce-choice${isOwned ? "" : " is-purchase"}" data-produce-choice data-owned="${isOwned}" data-search-name="${escapeHtml(item.name.toLowerCase())}"${isOwned ? "" : " hidden"}>
        <input type="checkbox" name="produce" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small>${isOwned ? `In My Kitchen${item.form ? ` · ${escapeHtml(item.form)}` : ""}` : "Added to grocery list"}${item.kind === "fruit" ? " · Fruit" : ""}</small>
        <select data-produce-form aria-label="${escapeHtml(item.name)} form"${isOwned ? " disabled" : ""}>
          ${isOwned ? `<option value="${escapeHtml(item.form || "")}">Use My Kitchen form</option>` : '<option>Fresh</option><option>Frozen</option><option>Canned</option>'}
        </select>
      </label>`;
    }).join("");
    produceHolder.addEventListener("change", syncStructureGuidance);
    syncStructureGuidance();

    const extras = options.extras || [];
    const extrasHolder = form.querySelector("[data-extra-options]");
    extrasHolder.innerHTML = extras.map(item => {
      const isOwned = item.owned ?? owned.has(String(item.name).toLowerCase());
      return `<label class="produce-choice${isOwned ? "" : " is-purchase"}" data-extra-choice data-owned="${isOwned}" data-search-name="${escapeHtml(item.name.toLowerCase())}"${isOwned ? "" : " hidden"}>
        <input type="checkbox" name="extras" value="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <small>${isOwned ? "In My Kitchen" : "Added to grocery list"}</small>
      </label>`;
    }).join("");

    const selectedPurchaseNames = () => {
      const names = [...form.querySelectorAll('.produce-choice[data-owned="false"] input:checked')].map(input => input.value);
      const selectedFoundation = foundation.selectedOptions[0];
      if (selectedFoundation?.dataset.owned === "false") names.push(selectedFoundation.value);
      return [...new Set(names)];
    };

    const catalogDialog = document.querySelector("[data-ingredient-catalog]");
    const catalogHolder = catalogDialog?.querySelector("[data-catalog-options]");
    const catalogItems = [
      ...(options.proteins || []).map(item => ({ ...item, catalogKind: "protein", catalogLabel: "Protein" })),
      ...(options.produce || []).map(item => ({ ...item, catalogKind: "produce", catalogLabel: item.kind === "fruit" ? "Fruit" : "Produce" })),
      ...(options.foundations || []).map(item => ({ ...item, catalogKind: "foundation", catalogLabel: "Foundation" })),
      ...(options.extras || []).map(item => ({ ...item, catalogKind: "extra", catalogLabel: "Pantry & fridge" })),
    ].filter(item => !(item.owned ?? owned.has(String(item.name).toLowerCase())));

    if (catalogHolder) {
      catalogHolder.innerHTML = catalogItems.map(item => `
        <button type="button" data-catalog-item data-catalog-kind="${item.catalogKind}" data-catalog-name="${escapeHtml(item.name)}" data-search-name="${escapeHtml(item.name.toLowerCase())}" aria-pressed="false">
          <span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.catalogLabel)}</small></span>
          <b data-catalog-action>Add</b>
        </button>`).join("");
    }

    const selectedInput = (kind, name) => {
      const selector = kind === "protein" ? 'input[name="protein"]' : kind === "produce" ? 'input[name="produce"]' : 'input[name="extras"]';
      return [...form.querySelectorAll(selector)].find(input => input.value === name);
    };

    const syncPurchaseUI = () => {
      const purchases = selectedPurchaseNames();
      const summary = form.querySelector("[data-builder-purchase-summary]");
      const summaryItems = form.querySelector("[data-builder-purchase-items]");
      if (summary) summary.hidden = purchases.length === 0;
      if (summaryItems) summaryItems.innerHTML = purchases.map(name => `<span>${escapeHtml(name)}</span>`).join("");

      form.querySelectorAll('.produce-choice[data-owned="false"]').forEach(choice => {
        choice.hidden = !choice.querySelector("input")?.checked;
      });
      [...foundation.options].forEach(option => {
        if (option.dataset.owned === "false") option.hidden = option.value !== foundation.value;
      });
      catalogHolder?.querySelectorAll("[data-catalog-item]").forEach(button => {
        const name = button.dataset.catalogName;
        const kind = button.dataset.catalogKind;
        const selected = kind === "foundation"
          ? foundation.value === name
          : Boolean(selectedInput(kind, name)?.checked);
        button.classList.toggle("selected", selected);
        button.setAttribute("aria-pressed", String(selected));
        button.querySelector("[data-catalog-action]").textContent = selected ? "Added" : "Add";
      });
    };

    const bindOwnedSearch = (inputSelector, choiceSelector) => {
      form.querySelector(inputSelector)?.addEventListener("input", event => {
        const query = event.target.value.trim().toLowerCase();
        form.querySelectorAll(choiceSelector).forEach(choice => {
          const availableHere = choice.dataset.owned === "true" || choice.querySelector("input")?.checked;
          choice.hidden = !availableHere || (Boolean(query) && !choice.dataset.searchName.includes(query));
        });
      });
    };
    bindOwnedSearch("[data-protein-search]", "[data-protein-choice]");
    bindOwnedSearch("[data-produce-search]", "[data-produce-choice]");
    bindOwnedSearch("[data-extra-search]", "[data-extra-choice]");

    const openCatalog = (filter = "all") => {
      const filterButton = catalogDialog?.querySelector(`[data-catalog-filter="${filter}"]`)
        || catalogDialog?.querySelector('[data-catalog-filter="all"]');
      catalogDialog?.querySelectorAll("[data-catalog-filter]").forEach(item => item.classList.toggle("active", item === filterButton));
      syncPurchaseUI();
      catalogDialog?.showModal();
      applyCatalogFilter();
      setTimeout(() => catalogDialog?.querySelector("[data-catalog-search]")?.focus(), 0);
    };
    form.querySelector("[data-open-ingredient-catalog]")?.addEventListener("click", () => openCatalog("all"));
    form.querySelectorAll("[data-browse-catalog]").forEach(button =>
      button.addEventListener("click", () => openCatalog(button.dataset.browseCatalog))
    );
    catalogHolder?.addEventListener("click", event => {
      const button = event.target.closest("[data-catalog-item]");
      if (!button) return;
      const { catalogKind: kind, catalogName: name } = button.dataset;
      if (kind === "foundation") {
        const option = [...foundation.options].find(item => item.value === name);
        if (option) option.hidden = false;
        foundation.value = foundation.value === name ? "" : name;
        foundation.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        const input = selectedInput(kind, name);
        if (input) {
          input.checked = !input.checked;
          input.closest(".produce-choice").hidden = false;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      syncProteinRoles();
      syncPurchaseUI();
    });
    form.querySelectorAll('input[name="protein"], input[name="produce"], input[name="extras"], [data-builder-foundation]').forEach(input =>
      input.addEventListener("change", syncPurchaseUI)
    );
    const applyCatalogFilter = () => {
      const query = catalogDialog?.querySelector("[data-catalog-search]")?.value.trim().toLowerCase() || "";
      const filter = catalogDialog?.querySelector("[data-catalog-filter].active")?.dataset.catalogFilter || "all";
      let matches = 0;
      catalogHolder?.querySelectorAll("[data-catalog-item]").forEach(button => {
        const visible = (filter === "all" || button.dataset.catalogKind === filter)
          && (!query || button.dataset.searchName.includes(query));
        button.hidden = !visible;
        if (visible) matches += 1;
      });
      const empty = catalogDialog?.querySelector("[data-catalog-empty]");
      if (empty) empty.hidden = matches > 0;
    };
    catalogDialog?.querySelector("[data-catalog-search]")?.addEventListener("input", applyCatalogFilter);
    catalogDialog?.querySelectorAll("[data-catalog-filter]").forEach(button => button.addEventListener("click", () => {
      catalogDialog.querySelectorAll("[data-catalog-filter]").forEach(item => item.classList.toggle("active", item === button));
      applyCatalogFilter();
    }));
    syncPurchaseUI();
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
          return {
            name,
            state: input.closest("[data-protein-choice]")?.querySelector("[data-protein-state]")?.value || "Fresh Raw",
            role: index === 0 ? "main" : ""
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
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await requestRecipe(button.dataset.recipeId);
        } catch (error) {
          holder.querySelector("[data-recipe-request-error]")?.remove();
          holder.insertAdjacentHTML("afterbegin", `
            <div class="recipe-service-error" role="alert" data-recipe-request-error>
              <strong>This recipe could not load.</strong>
              <p>${recipeServiceError(error)} Please try again.</p>
            </div>`);
          button.disabled = false;
        }
      });
    });
  }

  async function requestRecipe(recipeId) {
    const kitchen = JSON.parse(sessionStorage.getItem("snsKitchenPayload") || "{}");
    const request = { candidate_id: recipeId, recipe_id: recipeId, kitchen };
    sessionStorage.setItem("snsRecipeRequest", JSON.stringify(request));
    const choices = JSON.parse(sessionStorage.getItem("snsRecipeChoices") || "[]");
    const selectedChoice = choices.find(r => (r.candidate_id || r.id) === recipeId) || {};
    const recipe = await postJson(API.getRecipe, request);
    recordMealHistory({...selectedChoice, ...recipe});
    sessionStorage.setItem("snsGeneratedRecipe", JSON.stringify(recipe));
    location.href = "recipe.html";
  }

  function renderRecipe() {
    const recipe = JSON.parse(sessionStorage.getItem("snsGeneratedRecipe") || "{}");
    if (!document.querySelector("[data-recipe-title]")) return;
    document.querySelector("[data-recipe-title]").textContent = recipe.title || "Your recipe";
    document.querySelector("[data-recipe-summary]").textContent = recipe.summary || "";
    document.querySelector("[data-recipe-time]").textContent = recipe.total_minutes ? `${recipe.total_minutes} total minutes` : "Flexible timing";
    const workTime = document.querySelector("[data-recipe-work-time]");
    if (workTime) {
      const active = Number(recipe.active_minutes || 0);
      const passive = Number(recipe.passive_minutes || 0);
      workTime.textContent = active || passive
        ? `${active} active · ${passive} mostly waiting`
        : "";
    }
    const ingredientLines = recipe.ingredients || [];
    document.querySelector("[data-ingredients]").innerHTML = ingredientLines.map(x => `<li>${escapeHtml(x)}</li>`).join("");
    const ingredientQuantity = name => {
      const line = ingredientLines.find(item => String(item).toLowerCase().startsWith(`${String(name).toLowerCase()} —`));
      if (!line) return "";
      const details = String(line).split(" — ").slice(1).join(" — ");
      const parts = details.split(" · ").filter(Boolean);
      return parts.length > 1 ? parts.at(-1) : details;
    };
    const groceryItems = [];
    const groceryNames = new Set();
    (recipe.inventory_requirements || [])
      .filter(item => ["Need", "Short"].includes(item?.status))
      .forEach(item => {
        const key = String(item.name || "").toLowerCase();
        if (!key || groceryNames.has(key)) return;
        groceryNames.add(key);
        const shortfall = Number(item.quantity_shortfall || 0);
        const amount = item.status === "Short"
          ? `add ${shortfall || "some"} more`
          : item.quantity || ingredientQuantity(item.name);
        groceryItems.push({
          name: item.name,
          amount,
        });
      });
    const groceryList = document.querySelector("[data-grocery-list]");
    const groceryEmpty = document.querySelector("[data-grocery-empty]");
    if (groceryList) groceryList.innerHTML = groceryItems.map(item =>
      `<li><span>${escapeHtml(item.name)}</span>${item.amount ? `<strong>${escapeHtml(item.amount)}</strong>` : ""}</li>`
    ).join("");
    if (groceryEmpty) groceryEmpty.hidden = groceryItems.length > 0;
    const kitchenItems = (recipe.inventory_requirements || [])
      .filter(item => ["Substitute", "Omit"].includes(item?.status))
      .filter(item => !(item.status === "Substitute" && [
        "cooking oil or butter", "broth or water", "water or broth"
      ].includes(String(item.name || "").toLowerCase())))
      .filter(item => item.status !== "Omit" || item.omission_consequence)
      .map(item => {
        if (item.status === "Substitute") {
          return `${item.name} — use ${item.resolved_name}.`;
        }
        if (item.status === "Omit") {
          return `${item.name} — omit it. ${item.omission_consequence || "The meal remains valid without it."}`;
        }
        if (item.status === "Short") {
          const shortfall = Number(item.quantity_shortfall || 0);
          return `${item.name} — ${shortfall || "more"} additional ${shortfall === 1 ? "portion is" : "portions are"} needed for the planned servings.`;
        }
        const options = (item.substitutions || []).length
          ? ` Possible substitutes: ${item.substitutions.join(", ")}.`
          : "";
        if (item.planned_purchase) {
          return `${item.name} — add it to the shopping list.${options}`;
        }
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
    installRecipeReport(recipe);
  }

  function installRecipeReport(recipe) {
    const dialog = document.querySelector("[data-recipe-report-dialog]");
    const form = document.querySelector("[data-recipe-report-form]");
    const open = document.querySelector("[data-open-recipe-report]");
    const status = document.querySelector("[data-recipe-report-status]");
    if (!dialog || !form || !open || open.dataset.bound === "true") return;
    open.dataset.bound = "true";
    open.addEventListener("click", () => dialog.showModal());
    document.querySelectorAll("[data-close-recipe-report]").forEach(button =>
      button.addEventListener("click", () => dialog.close())
    );
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const submit = form.querySelector("[data-submit-recipe-report]");
      const categories = [...form.querySelectorAll('input[name="issue"]:checked')]
        .map(input => input.value);
      submit.disabled = true;
      status.textContent = "Sending this recipe for review…";
      try {
        await postJson(API.reportRecipe, {
          candidate_id: recipe.candidate_id,
          recipe_snapshot: recipe,
          rendered_recipe_text: document.querySelector("main")?.innerText || "",
          issue_categories: categories.length ? categories : ["general_review"],
          user_note: form.elements.note.value
        });
        dialog.close();
        form.reset();
        open.disabled = true;
        open.textContent = "Sent for review";
        status.textContent = "Thank you. Stock & Stir received this exact recipe for review.";
      } catch (error) {
        status.textContent = error.message || "This report could not be sent. Please try again.";
      } finally {
        submit.disabled = false;
      }
    });
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

  async function init() {
    installAppShell();
    await hydrateSharedKitchen();
    upgradeQuantityEditors();
    restoreBrowserKitchen();
    organizeInventory();
    bindAmounts();
    bindKitchenDashboard();
    bindPantryImporter();
    bindInventoryCapture();
    updateCount();
    initializeKitchenAccordion();
    renderRecipeChoices();
    renderRecipe();
    renderMealBuilder();
    renderHome();
    document.querySelector("[data-save-kitchen]")?.addEventListener("click", saveKitchen);
    document.querySelector("[data-save-household]")?.addEventListener("click", saveKitchen);
    document.querySelector("[data-get-recipes]")?.addEventListener("click", generateRecipeList);
    document.querySelector("[data-build-meal]")?.addEventListener("click", openMealBuilder);
    document.querySelector("[data-signature-recipes]")?.addEventListener("click", openSignatureRecipes);
    if (sessionStorage.getItem("snsKitchenUndoNeedsSave") === "1") {
      sessionStorage.removeItem("snsKitchenUndoNeedsSave");
      saveKitchen();
    }
    document.querySelectorAll("[data-checkout]").forEach(b => b.addEventListener("click", () => checkout(b.dataset.checkout)));
    document.querySelector("[data-billing-portal]")?.addEventListener("click", billingPortal);
    runRequestedKitchenAction();
    refreshRecipeChoices();
  }

  return { init, kitchenPayload, API };
})();
document.addEventListener("DOMContentLoaded", SNS.init);
