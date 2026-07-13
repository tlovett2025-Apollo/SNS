/*
  ENGINEERING-OWNED LINK MAP
  ==========================
  Replace these placeholder routes as the authenticated SNS application
  and APIs become available. Public website editors should not need to
  change every button individually.
*/
const APP_URLS = {
  login: "/login",
  signup: "/signup",
  "signup-basic": "/signup?plan=basic",
  "signup-premium": "/signup?plan=premium",
  kitchen: "/app/kitchen",
  demo: "/sample-meal"
};

document.querySelectorAll("[data-app-link]").forEach((link) => {
  const linkName = link.dataset.appLink;
  const destination = APP_URLS[linkName];

  if (destination) {
    link.setAttribute("href", destination);
  }
});

const menuToggle = document.querySelector(".menu-toggle");
const primaryNav = document.querySelector(".primary-nav");

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
