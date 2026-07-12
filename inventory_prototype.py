"""Customer-facing inventory editor prototype for Stock & Stir.

This page reads real ingredient Forms from the CKB. It intentionally keeps
selections in the Streamlit session only; it does not modify the database.
"""

from pathlib import Path
import sqlite3

import streamlit as st


DB_PATH = Path("data") / "ckb_seed_001.db"

st.set_page_config(page_title="My Stock & Stir Kitchen", page_icon="🥫", layout="wide")

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 5rem;}
    h1 {font-size: 2.25rem !important; letter-spacing: -0.03em;}
    .sns-hero {background: linear-gradient(135deg,#123a52,#1d5871); border:1px solid #2f6f88;
               border-radius:20px; padding:22px 26px; margin-bottom:18px;}
    .sns-hero h1 {color:#ffffff !important;}
    .sns-hero p {font-size:1.08rem; margin:4px 0 0 0; color:#e7f3f8;}
    .sns-count {background:#17465f; color:#ffffff; border:1px solid #2f6f88;
                border-radius:14px; padding:12px 16px; margin:8px 0 16px 0;}
    div[data-testid="stExpander"] {border:1px solid #e0ddd5; border-radius:14px; overflow:hidden;}
    div[data-testid="stCheckbox"] label {min-height:42px; align-items:center;}
    .stButton > button {min-height:46px; border-radius:12px; font-weight:650;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_inventory_choices():
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT i.ingredient_id, i.name, i.category, i.default_storage,
                      f.form_id, f.form_name, f.pantry_style
               FROM ingredient_forms f
               JOIN ingredients i ON i.ingredient_id=f.ingredient_id
               WHERE i.active=1
                 AND (COALESCE(i.verified,0)=1 OR i.name='Centauran Gotlet Ribs')
               ORDER BY i.category, i.display_order, i.name, f.form_name"""
        ).fetchall()
    choices = [dict(row) for row in rows]
    by_ingredient = {}
    for row in choices:
        by_ingredient.setdefault(row["ingredient_id"], []).append(row)

    cleaned = []
    generic_forms = {"pantry", "refrigerated"}
    for row in choices:
        form = str(row["form_name"] or "").lower()
        peers = by_ingredient[row["ingredient_id"]]
        peer_forms = {str(peer["form_name"] or "").lower() for peer in peers}
        if row["name"] == "Centauran Gotlet Ribs":
            row["form_name"] = "Fresh Raw"
        elif form == "pantry":
            meaningful_pantry_form = any(
                peer_form not in generic_forms
                and str(peer.get("pantry_style") or "").lower() == "pantry"
                for peer, peer_form in [
                    (peer, str(peer["form_name"] or "").lower()) for peer in peers
                ]
            )
            if meaningful_pantry_form:
                continue
            row["form_name"] = "Canned" if row["name"].lower().startswith("canned ") else "On hand"
        elif form == "refrigerated":
            meaningful_cold_form = any(
                peer_form not in generic_forms
                and str(peer.get("pantry_style") or "").lower() in {"fridge", "refrigerated", "fridge/freezer"}
                for peer, peer_form in [
                    (peer, str(peer["form_name"] or "").lower()) for peer in peers
                ]
            )
            if meaningful_cold_form:
                continue
            row["form_name"] = "On hand"
        cleaned.append(row)
    return cleaned


def section_for(row):
    form = str(row.get("form_name") or "").lower()
    storage = str(row.get("pantry_style") or row.get("default_storage") or "").lower()
    category = str(row.get("category") or "").lower()

    if form == "fresh" or storage == "counter":
        return "Fresh"
    if "freez" in form or storage == "freezer":
        return "Freezer"
    if storage == "pantry" or form in {
        "pantry", "dry", "canned", "jarred", "pouch", "powdered",
        "dehydrated", "freeze dried", "shelf stable",
    }:
        return "Pantry"
    if storage in {"fridge", "refrigerated", "fridge/freezer"}:
        return "Refrigerator"
    if category in {"fruit", "herbs"}:
        return "Fresh"
    return "Pantry"


def grouped(rows):
    result = {}
    for row in rows:
        category = (
            "Foods from Alpha Centauri"
            if row["name"] == "Centauran Gotlet Ribs"
            else friendly_category(row["category"])
        )
        result.setdefault(category, {}).setdefault(row["name"], []).append(row)
    return result


def friendly_category(category):
    category = str(category or "Other").strip()
    lower = category.lower()
    if lower in {"beans", "legumes"}:
        return "Beans & legumes"
    if lower == "foundations":
        return "Rice, pasta & sides"
    if lower == "pantry":
        return "Sauces, baking & staples"
    if lower == "spices":
        return "Spices & seasonings"
    if lower in {"beef", "chicken", "pork", "turkey", "seafood", "processed meat", "plant protein", "eggs", "protein"}:
        return "Proteins"
    if lower == "dairy alternative":
        return "Dairy & alternatives"
    return category


def inventory_key(row):
    return f"inventory_{row['ingredient_id']}_{row['form_id']}"


def selected_rows(rows):
    return [row for row in rows if st.session_state.get(inventory_key(row), False)]


rows = load_inventory_choices()
if not rows:
    st.error("The Cooking Knowledge Base could not be found, or it has no ingredient Forms yet.")
    st.stop()

if "custom_inventory" not in st.session_state:
    st.session_state.custom_inventory = []

st.markdown(
    """
    <div class="sns-hero">
      <h1 style="margin:0">What food do you have?</h1>
      <p>Check what is in your kitchen. You do not need exact amounts, and you can change this anytime.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

top_left, top_right = st.columns([3, 1])
with top_left:
    search = st.text_input(
        "Find an ingredient",
        placeholder="Try chicken, beans, rice, broccoli…",
        help="Search is optional. Browse the kitchen sections below if that is easier.",
    ).strip().lower()
with top_right:
    st.write("")
    st.write("")
    if st.button("Clear my selections", use_container_width=True):
        for row in rows:
            st.session_state[inventory_key(row)] = False
        st.session_state.custom_inventory = []
        st.rerun()

selected = selected_rows(rows)
selected_total = len(selected) + len(st.session_state.custom_inventory)
st.markdown(
    f'<div class="sns-count"><strong>{selected_total} item{"s" if selected_total != 1 else ""} selected</strong>'
    + (" — enough to start finding meals." if selected_total else " — choose only what you know you have.")
    + "</div>",
    unsafe_allow_html=True,
)

with st.expander("Can’t find something? Add it quickly"):
    st.caption("This adds a household item for this session. It does not change the shared Cooking Knowledge Base.")
    with st.form("quick_inventory_entry", clear_on_submit=True):
        quick_name = st.text_input("What is it?", placeholder="Lasagna noodles")
        quick_location = st.selectbox("Where do you keep it?", ["Pantry", "Refrigerator", "Freezer", "Fresh"])
        quick_form = st.selectbox(
            "How do you have it?",
            ["On hand", "Dry", "Canned", "Fresh", "Frozen", "Cooked", "Leftover", "Other"],
        )
        quick_add = st.form_submit_button("Add to my kitchen", type="primary", use_container_width=True)
    if quick_add:
        clean_name = quick_name.strip()
        if not clean_name:
            st.warning("Enter the food name first.")
        else:
            new_item = {"name": clean_name, "form_name": quick_form, "section": quick_location}
            duplicate = any(
                item["name"].lower() == clean_name.lower()
                and item["form_name"].lower() == quick_form.lower()
                and item["section"] == quick_location
                for item in st.session_state.custom_inventory
            )
            if duplicate:
                st.info("That household item is already listed.")
            else:
                st.session_state.custom_inventory.append(new_item)
                st.rerun()

section_help = {
    "Pantry": "Shelf-stable food: cans, jars, boxes, dry goods, spices, and pouches.",
    "Refrigerator": "Food kept cold: raw meat, dairy, leftovers, and refrigerated ingredients.",
    "Freezer": "Frozen meat, vegetables, prepared foods, and other frozen ingredients.",
    "Fresh": "Fresh produce, herbs, fruit, bread, garden food, and counter items.",
}

section_rows = {name: [] for name in section_help}
for row in rows:
    section_rows[section_for(row)].append(row)

tabs = st.tabs(
    [f"{name} · {len({r['ingredient_id'] for r in section_rows[name]})}" for name in section_help]
)

for tab, section_name in zip(tabs, section_help):
    with tab:
        st.caption(section_help[section_name])
        visible = section_rows[section_name]
        if search:
            visible = [
                row for row in visible
                if search in row["name"].lower()
                or search in row["form_name"].lower()
                or search in row["category"].lower()
            ]
        if not visible:
            st.info("Nothing in this section matches that search.")
            continue

        categories = grouped(visible)
        for category, ingredients in categories.items():
            selected_in_category = sum(
                st.session_state.get(inventory_key(form), False)
                for forms in ingredients.values() for form in forms
            )
            label = f"{category} · {len(ingredients)} items"
            if selected_in_category:
                label += f" · {selected_in_category} selected"
            with st.expander(label, expanded=bool(search)):
                st.caption("Choose as many as you have, then keep the whole group at once.")
                form_key = f"batch_{section_name}_{category}".replace(" ", "_").replace("&", "and")
                with st.form(form_key):
                    for ingredient, forms in ingredients.items():
                        name_col, forms_col = st.columns([1.25, 3.75], vertical_alignment="center")
                        with name_col:
                            st.markdown(f"**{ingredient}**")
                        with forms_col:
                            form_columns = st.columns(min(4, max(1, len(forms))))
                            for index, form in enumerate(forms):
                                with form_columns[index % len(form_columns)]:
                                    st.checkbox(
                                        form["form_name"],
                                        key=inventory_key(form),
                                        help=f"Stored in: {section_name.lower()}",
                                    )
                        st.divider()
                    st.form_submit_button("Keep these selections", use_container_width=True)

st.subheader("Your kitchen so far")
selected = selected_rows(rows)
custom_selected = list(st.session_state.custom_inventory)
if not selected and not custom_selected:
    st.write("Nothing selected yet. Start with the foods you use most often.")
else:
    summary = {}
    for row in selected:
        summary.setdefault(section_for(row), []).append(f"{row['name']} — {row['form_name']}")
    for item in custom_selected:
        summary.setdefault(item["section"], []).append(f"{item['name']} — {item['form_name']} (quick entry)")
    columns = st.columns(4)
    for column, section_name in zip(columns, section_help):
        with column:
            st.markdown(f"**{section_name}**")
            items = summary.get(section_name, [])
            if items:
                for item in items:
                    st.write(f"• {item}")
            else:
                st.caption("Nothing selected")

left, right = st.columns([1, 1])
with left:
    st.button("Save for later", disabled=True, use_container_width=True,
              help="Prototype only: this version does not write to the household inventory.")
with right:
    if st.button("Find meals with this food", type="primary", use_container_width=True):
        if selected or custom_selected:
            st.success("Prototype complete: the next page would use these selections to offer a few meal choices.")
        else:
            st.warning("Choose at least one food first.")

st.caption("Prototype page — reads the real CKB but does not save or change inventory data.")
