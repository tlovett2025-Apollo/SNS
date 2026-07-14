const SNS = (() => {
  const runtime = window.SNS_CONFIG || {};
  const apiBase = String(runtime.apiBaseUrl || "").replace(/\/$/, "");
  const endpoint = path => `${apiBase}${path}`;
  const API = {
    saveKitchen: endpoint("/api/SaveMyKitchen"),
    getRecipeList: endpoint("/api/GetRecipeList"),
    getRecipe: endpoint("/api/GetRecipe"),
    createCheckout: endpoint("/api/CreateCheckoutSession"),
    billingPortal: endpoint("/api/CreateBillingPortalSession")
  };

  const levelMeaning = {
    none: { label: "None", quantity_band: 0 },
    little: { label: "A little", quantity_band: 1 },
    plenty: { label: "Plenty", quantity_band: 3 }
  };

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
      const active = row.querySelector(".amount button.active");
      const level = active?.dataset.level || "none";
      return {
        name: row.dataset.food,
        storage: row.dataset.storage,
        form: row.dataset.form || "On hand",
        amount: level,
        quantity_band: levelMeaning[level].quantity_band
      };
    }).filter(item => item.amount !== "none");

    return {
      api_version: "1.0",
      contract_version: "my-kitchen-v1",
      household_id: "local-demo-household",
      generated_at: new Date().toISOString(),
      servings: 4,
      energy: "Low",
      inventory: items,
      equipment: [],
      meal_preferences: {},
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

  function bindAmounts() {
    document.querySelectorAll(".amount").forEach(group => {
      group.querySelectorAll("button").forEach(button => {
        button.addEventListener("click", () => {
          group.querySelectorAll("button").forEach(b => b.classList.remove("active"));
          button.classList.add("active");
          updateCount();
        });
      });
    });
  }

  function updateCount() {
    const payload = kitchenPayload();
    const target = document.querySelector("[data-selected-count]");
    if (target) target.textContent = payload.inventory.length;
    const dev = document.querySelector("[data-payload]");
    if (dev) dev.textContent = JSON.stringify(payload, null, 2);
  }

  function fallbackRecipes(payload) {
    const names = payload.inventory.map(i => i.name.toLowerCase());
    const has = (...parts) => parts.every(p => names.some(n => n.includes(p)));
    const recipes = [];
    if (has("chicken") && has("rice")) recipes.push({
      id:"chicken-rice-skillet", title:"Comforting Chicken & Rice Skillet",
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
      {id:"kitchen-skillet", title:"My Kitchen Supper Skillet", minutes:30, effort:"Medium", match:"Good match", summary:"Protein, vegetables, and a foundation brought together in one skillet."},
      {id:"simple-plate", title:"Simple Protein, Vegetable & Foundation Plate", minutes:25, effort:"Low", match:"Practical match", summary:"Cook the components simply and finish them together."}
    );
    return recipes.slice(0, 6);
  }

  async function saveKitchen() {
    const payload = kitchenPayload();
    sessionStorage.setItem("snsKitchenPayload", JSON.stringify(payload));
    try {
      await postJson(API.saveKitchen, payload);
      alert("My Kitchen is saved.");
    } catch {
      alert("My Kitchen is saved in this browser prototype. The API will receive the same payload when connected.");
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
          <div class="meta">
            <span class="pill">${escapeHtml(recipe.total_minutes || recipe.minutes || "Flexible")} min</span>
            <span class="pill">Effort ${escapeHtml(recipe.effort ?? "Practical")}</span>
            <span class="pill">${escapeHtml(recipe.match || "Match")}</span>
          </div>
          <h2>${escapeHtml(recipe.title)}</h2>
          <p>${escapeHtml(recipe.summary || "")}</p>
          <div class="meta">
            <span class="pill">${escapeHtml(recipe.meal_shape || "meal")}</span>
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
    try {
      recipe = await postJson(API.getRecipe, request);
    } catch {
      const choices = JSON.parse(sessionStorage.getItem("snsRecipeChoices") || "[]");
      const choice = choices.find(r => (r.candidate_id || r.id) === recipeId) || {};
      recipe = {
        id: recipeId,
        title: choice.title || "Stock & Stir Recipe",
        summary: choice.summary || "A practical meal built from My Kitchen.",
        ingredients: (kitchen.inventory || []).slice(0, 8).map(item => `${item.name} — ${item.amount}`),
        steps: [
          "Gather the selected ingredients and the equipment you need.",
          "Prep the protein and vegetables before the main cooking begins.",
          "Cook the longest-lead component first, then add quick-cooking ingredients later.",
          "Taste, adjust the seasoning, and serve when everything is safely cooked and ready."
        ],
        total_minutes: choice.minutes || 35
      };
    }
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
    document.querySelector("[data-steps]").innerHTML = (recipe.steps || recipe.instructions || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");
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
    bindAmounts();
    updateCount();
    renderRecipeChoices();
    renderRecipe();
    document.querySelector("[data-save-kitchen]")?.addEventListener("click", saveKitchen);
    document.querySelector("[data-get-recipes]")?.addEventListener("click", generateRecipeList);
    document.querySelectorAll("[data-checkout]").forEach(b => b.addEventListener("click", () => checkout(b.dataset.checkout)));
    document.querySelector("[data-billing-portal]")?.addEventListener("click", billingPortal);
  }

  return { init, kitchenPayload, API };
})();
document.addEventListener("DOMContentLoaded", SNS.init);
