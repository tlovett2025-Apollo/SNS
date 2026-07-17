/*
  ENGINEERING-OWNED LINK MAP
  ==========================
  Replace these routes as the authenticated SNS application and APIs become available.
  Public website editors should not need to change every button individually.
*/
const APP_URLS = {
  login: "login.html",
  signup: "login.html?mode=signup",
  "signup-basic": "login.html?mode=signup&plan=basic",
  "signup-premium": "login.html?mode=signup&plan=premium",
  kitchen: "home.html",
  demo: "my-kitchen.html"
};

document.querySelectorAll("[data-app-link]").forEach((link) => {
  const linkName = link.dataset.appLink;
  const destination = APP_URLS[linkName];

  if (destination) {
    link.setAttribute("href", destination);
  }
});

/*
  Mobile portrait always exposes Log In directly in the header. The full account
  links remain in the navigation menu as well, so login never depends on rotation.
*/
const headerInner = document.querySelector(".header-inner");
const menuToggle = document.querySelector(".menu-toggle");
const primaryNav = document.querySelector(".primary-nav");

if (headerInner && menuToggle) {
  const mobileLogin = document.createElement("a");
  mobileLogin.href = APP_URLS.login;
  mobileLogin.textContent = "Log In";
  mobileLogin.setAttribute("aria-label", "Log in to Stock and Stir");
  mobileLogin.className = "mobile-login-quick";
  Object.assign(mobileLogin.style, {
    minHeight: "44px",
    alignItems: "center",
    justifyContent: "center",
    padding: "8px 13px",
    border: "1px solid rgba(226, 206, 165, 0.65)",
    borderRadius: "9px",
    color: "white",
    fontSize: "14px",
    fontWeight: "700",
    whiteSpace: "nowrap",
    gridColumn: "2",
    gridRow: "1"
  });
  headerInner.insertBefore(mobileLogin, menuToggle);

  const mobilePortrait = window.matchMedia("(max-width: 760px)");
  const syncMobileLogin = () => {
    mobileLogin.style.display = mobilePortrait.matches ? "inline-flex" : "none";
    if (mobilePortrait.matches) {
      menuToggle.style.gridColumn = "3";
      headerInner.style.gridTemplateColumns = "minmax(0, 1fr) auto auto";
      headerInner.style.gap = "10px";
    } else {
      menuToggle.style.gridColumn = "";
      headerInner.style.gridTemplateColumns = "";
      headerInner.style.gap = "";
    }
  };
  syncMobileLogin();
  mobilePortrait.addEventListener?.("change", syncMobileLogin);
}

if (menuToggle && primaryNav) {
  menuToggle.addEventListener("click", () => {
    const isOpen = primaryNav.classList.toggle("open");
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  });

  primaryNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      primaryNav.classList.remove("open");
      menuToggle.setAttribute("aria-expanded", "false");
    });
  });
}

document.querySelectorAll(".ingredient-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const isSelected = chip.classList.toggle("selected");
    chip.setAttribute("aria-pressed", String(isSelected));
  });
});

const demoButton = document.getElementById("demo-find-button");
const demoResult = document.getElementById("demo-result");

if (demoButton && demoResult) {
  demoButton.addEventListener("click", () => {
    const selectedIngredients = Array.from(
      document.querySelectorAll(".ingredient-chip.selected")
    ).map((chip) => chip.textContent.trim());

    const time = document.getElementById("demo-time").value;
    const energy = document.getElementById("demo-energy").value;
    const servings = document.getElementById("demo-servings").value;

    if (selectedIngredients.length === 0) {
      demoResult.hidden = false;
      demoResult.innerHTML =
        "<strong>Select at least one ingredient.</strong> Stock & Stir needs something to build from.";
      return;
    }

    const ingredientText = selectedIngredients.join(", ");
    demoResult.hidden = false;
    demoResult.innerHTML = `
      <strong>Your kitchen preview is ready.</strong>
      Based on <em>${ingredientText}</em>, ${time}, ${energy.toLowerCase()} energy,
      and ${servings.toLowerCase()}, Stock & Stir would rank a short list of meal
      directions and then build the cooking plan. The live application will open
      your saved kitchen inventory after login.
      <br><br>
      <a class="text-link" href="${APP_URLS.signup}">Create an account to continue →</a>
    `;
  });
}

const yearElement = document.getElementById("current-year");
if (yearElement) {
  yearElement.textContent = new Date().getFullYear();
}
