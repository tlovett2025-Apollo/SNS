import streamlit as st
from schema import create_schema
from seed import seed
from database import (insert_row, update_row, delete_row, fetch_df, fetch_options, table_count, row_exists,
                      safe_delete, ingredient_usage, ingredient_is_linked, usage_text)
from recipe_engine import generate_candidates, build_recipe_from_candidate

st.set_page_config(page_title="Stock & Stir v5", layout="wide")
create_schema()

CATEGORY_OPTIONS = ["protein", "vegetable", "fruit", "foundation", "dairy", "fat", "seasoning", "sauce", "liquid", "other"]
STORAGE_OPTIONS = ["pantry", "fridge", "freezer", "spice", "other"]
LEVEL_OPTIONS = ["", "Very Low", "Low", "Medium", "High"]
BUDGET_OPTIONS = ["", "Pantry Only", "Budget", "Moderate", "High"]
COST_OPTIONS = ["", "Budget", "Moderate", "High"]
ANIMAL_SOURCE_OPTIONS = ["", "Chicken", "Turkey", "Beef", "Pork", "Lamb", "Fish", "Shellfish", "Egg", "Dairy", "Plant", "Other"]
# Alpha-gal will be handled later as a user-profile condition/rules-engine filter, not a protein field in the visible training UI.
MEAT_COLOR_OPTIONS = ["", "White", "Dark", "Red", "None"]
PREP_OPTIONS = ["", "Whole", "Cubed", "Ground", "Shredded", "Sliced", "Diced", "Pulled", "Canned", "Frozen"]
EQUIPMENT_TYPE_OPTIONS = ["", "pot", "pan", "dutch oven", "sheet pan", "baking dish", "pizza pan", "grill", "sous vide", "rice cooker", "grain cooker", "wok", "toaster", "blender", "mixer", "small appliance", "accessory"]
STATE_OPTIONS = ["Raw", "Frozen Raw", "Cooked", "Leftover", "Sous Vide", "Canned", "Freeze Dried", "Dehydrated", "Fresh", "Frozen Cooked"]
ALIAS_TYPE_OPTIONS = ["synonym", "common name", "regional name", "brand shorthand", "misspelling", "search term"]
FOUNDATION_TYPE_OPTIONS = ["", "potato", "rice", "pasta", "bean", "corn", "grain", "bread", "vegetable", "other"]
TEXTURE_OPTIONS = ["", "creamy", "fluffy", "tender", "hearty", "crisp", "soft", "firm", "saucy"]
PANTRY_STYLE_OPTIONS = ["", "Pantry Friendly", "Fresh", "Frozen", "Freeze Dried", "Refrigerated"]

st.title("Stock & Stir")
st.caption("v5 Beta 2D - Repair Build 2 (Component CRUD Stabilization) · Python Babies v9")

APP_BUILD = "python_babies_v9"
if st.session_state.get("app_build") != APP_BUILD:
    st.session_state.app_build = APP_BUILD
    st.session_state.candidates = []
    st.session_state.generated_recipe = None

with st.sidebar:
    st.header("Setup")
    if st.button("Create / Update Schema"):
        create_schema(); st.success("Schema ready.")
    if st.button("Seed Starter Data"):
        seed(); st.success("Starter data loaded.")
    st.divider(); st.subheader("Database Counts")
    for t in ["ingredients", "proteins", "vegetables", "foundations", "cuisines", "sauces", "techniques", "users"]:
        try: st.write(f"{t}: {table_count(t)}")
        except Exception: st.write(f"{t}: -")

tabs = st.tabs(["Build Recipe", "Ingredients", "Components", "Cuisines", "Nutrition", "User Profile", "Signature Recipes", "Admin Editor", "Data Browser"])



def select_from_options(label, options, current_id=None, allow_blank=True, key=None, help_text=None):
    """Mobile/keyboard-friendlier lookup selector. Shows names, stores IDs.
    Streamlit's selectbox is searchable when focused; Enter commits the highlighted option.
    """
    opts = list(options or [])
    display = []
    values = []
    if allow_blank:
        display.append("")
        values.append(None)
    for oid, name in opts:
        display.append(str(name))
        values.append(int(oid))
    try:
        index = values.index(int(current_id)) if current_id not in [None, ""] else 0
    except Exception:
        index = 0
    chosen = st.selectbox(label, display, index=index, key=key, help=help_text)
    return values[display.index(chosen)]

def lookup_display_sql(table):
    if table == "proteins":
        return """SELECT p.protein_id, i.name AS ingredient_name, tech.name AS default_technique, p.cost_level, p.energy_level, p.animal_source, p.meat_color, p.default_prep, p.notes FROM proteins p JOIN ingredients i ON p.ingredient_id=i.ingredient_id LEFT JOIN techniques tech ON p.default_technique_id=tech.technique_id ORDER BY i.name"""
    if table == "vegetables":
        return """SELECT v.vegetable_id, i.name AS ingredient_name, prep.prep_name AS common_prep, v.soft_texture_possible, v.cooks_fast, v.notes FROM vegetables v JOIN ingredients i ON v.ingredient_id=i.ingredient_id LEFT JOIN prep_forms prep ON v.common_prep_id=prep.prep_id ORDER BY i.name"""
    if table == "ingredient_states":
        return """SELECT s.state_id, i.name AS ingredient_name, s.state_name, s.storage_location, s.needs_cooking, s.ready_to_eat, s.typical_prep_minutes, s.typical_cook_minutes, s.energy_level, s.rank_penalty, s.notes FROM ingredient_states s JOIN ingredients i ON s.ingredient_id=i.ingredient_id ORDER BY i.name, s.state_name"""
    if table == "ingredient_aliases":
        return """SELECT a.alias_id, a.alias_name, a.alias_type, i.name AS canonical_ingredient, a.notes FROM ingredient_aliases a JOIN ingredients i ON a.ingredient_id=i.ingredient_id ORDER BY a.alias_name"""
    if table == "ingredient_nutrition":
        return """SELECT n.nutrition_id, i.name AS ingredient_name, n.calories_per_100g, n.protein_g_per_100g, n.carbs_g_per_100g, n.fat_g_per_100g, n.fiber_g_per_100g, n.sodium_mg_per_100g, n.source, n.notes FROM ingredient_nutrition n JOIN ingredients i ON n.ingredient_id=i.ingredient_id ORDER BY i.name"""
    return f"SELECT * FROM {table}"

def df_search(label, query, params=None):
    search = st.text_input("Search", key=f"{label}_search")
    df = fetch_df(query, params or [])
    if search and not df.empty:
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]
    return df

def row_selector(df, id_col, label_col, key):
    if df.empty:
        st.info("No rows yet."); return None
    labels = [f"{int(r[id_col])}: {r[label_col]}" for _, r in df.iterrows()]
    selected = st.selectbox("Select row", labels, key=key)
    selected_id = int(selected.split(":", 1)[0])
    return df[df[id_col] == selected_id].iloc[0].to_dict()

def confirm_delete(table, id_col, id_value, label, key):
    st.warning(f"Delete: {label}?")
    if st.button("Confirm Delete", key=key):
        try:
            delete_row(table, id_col, id_value); st.success("Deleted."); st.rerun()
        except Exception as e:
            st.error(f"Could not delete. It may be used by another table. Details: {e}")

def clean_step_number(step):
    text = "" if step is None else str(step).strip()
    while True:
        parts = text.split(". ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            text = parts[1].strip()
        else:
            return text

with tabs[0]:
    st.header("Build Recipe")
    st.write("Choose what you have and today's constraints. SNS returns top recipe options first; you choose one to generate.")
    proteins = fetch_df("""SELECT p.protein_id, i.name FROM proteins p JOIN ingredients i ON p.ingredient_id=i.ingredient_id WHERE i.active=1 ORDER BY i.name""")
    vegetables = fetch_df("""SELECT v.vegetable_id, i.name FROM vegetables v JOIN ingredients i ON v.ingredient_id=i.ingredient_id WHERE i.active=1 ORDER BY i.name""")
    foundations = fetch_df("SELECT foundation_id, name FROM foundations ORDER BY name")
    cuisines = fetch_df("SELECT cuisine_id, name FROM cuisines ORDER BY name")
    c1,c3,c4 = st.columns(3)
    protein_name = c1.selectbox("Protein", [""] + proteins["name"].tolist() if not proteins.empty else [""], key="build_protein_v8")
    foundation_name = c3.selectbox("Foundation", [""] + foundations["name"].tolist() if not foundations.empty else [""], key="build_foundation_v8")
    cuisine_name = c4.selectbox("Cuisine", [""] + cuisines["name"].tolist() if not cuisines.empty else ["", "American", "Italian", "Mexican"], key="build_cuisine_v8")

    vegetable_options = vegetables["name"].tolist() if not vegetables.empty else []
    vegetable_names = st.multiselect(
        "Vegetables",
        vegetable_options,
        default=[],
        key="build_vegetables_multi_v8",
        placeholder="Choose one or more vegetables, like Asparagus and Mushrooms",
        help="You can select multiple vegetables. The red pills are selected items, not an error.",
    )
    vegetable_name = " & ".join(vegetable_names)
    c5,c6,c7,c8 = st.columns(4)
    energy_level = c5.selectbox("Energy", LEVEL_OPTIONS, index=2)
    budget_level = c6.selectbox("Budget", BUDGET_OPTIONS, index=2)
    time_minutes = c7.number_input("Max Time Minutes", min_value=5, max_value=240, value=30, step=5)
    servings = c8.number_input("Servings", min_value=1, max_value=24, value=4, step=1)
    if "candidates" not in st.session_state: st.session_state.candidates = []
    if st.button("Find Recipe Options", type="primary"):
        st.session_state.generated_recipe = None
        st.session_state.candidates = generate_candidates(protein_name, vegetable_name, foundation_name, cuisine_name, energy_level, budget_level, int(time_minutes), int(servings), 10, vegetable_names=vegetable_names)
    if st.session_state.candidates:
        st.subheader("Top Recipe Options")
        option_labels = [f"{i+1}. {c['title']} — {c['energy']} energy · {c['budget']} · {c['minutes']} min total · {c.get('active_minutes', 0)} active · {c.get('passive_minutes', 0)} passive · attention {c.get('attention_score', 0)}/10 · score {c['score']}" for i,c in enumerate(st.session_state.candidates)]
        chosen = st.radio("Choose one to generate", option_labels)
        candidate = st.session_state.candidates[option_labels.index(chosen)]
        st.caption(f"Why: {candidate['why']} | Sauce/seasoning direction: {candidate['sauce']}")
        if st.button("Generate Selected Recipe"):
            st.session_state.generated_recipe = build_recipe_from_candidate(candidate)
    if st.session_state.get("generated_recipe") is not None:
        result = st.session_state.generated_recipe
        st.divider(); st.subheader(result["name"]); st.caption(result["summary"])
        if result.get("plan_summary"):
            ps = result["plan_summary"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", f"{ps.get('total_minutes', 0)} min")
            m2.metric("Active", f"{ps.get('active_minutes', 0)} min")
            m3.metric("Passive", f"{ps.get('passive_minutes', 0)} min")
            m4.metric("Down-day fit", ps.get("energy_fit", ""))
        st.markdown("### Recipe")
        for i, step in enumerate(result["instructions"], 1): st.markdown(f"**{i}.** {clean_step_number(step)}")
        st.markdown("### Grocery List / Component List")
        for item in result["grocery_list"]: st.write(f"- {item}")

with tabs[1]:
    st.header("Ingredients")
    with st.expander("Add Ingredient", expanded=True):
        with st.form("add_ingredient"):
            c1,c2,c3 = st.columns(3)
            name = c1.text_input("Ingredient Name")
            category = c2.selectbox("Category", CATEGORY_OPTIONS)
            storage = c3.selectbox("Default Storage", STORAGE_OPTIONS)
            c4,c5,c6,c7,c8 = st.columns(5)
            dairy = c4.checkbox("Contains Dairy"); gluten = c5.checkbox("Contains Gluten"); pork = c6.checkbox("Contains Pork"); egg = c7.checkbox("Contains Egg"); active = c8.checkbox("Active", value=True)
            auto_component = st.checkbox("Also create matching component", value=True, help="For protein and vegetable ingredients, create the linked component row immediately. For foundation, create a foundation row with the same name.")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Ingredient")
        if submitted:
            clean_name = name.strip()
            if not clean_name: st.error("Ingredient name is required.")
            elif row_exists("ingredients", "name", clean_name): st.warning(f"{clean_name} already exists. Use Edit instead of adding a duplicate.")
            else:
                new_ingredient_id = insert_row("ingredients", {"name": clean_name, "category": category, "default_storage": storage, "dairy_flag": int(dairy), "gluten_flag": int(gluten), "pork_flag": int(pork), "egg_flag": int(egg), "active": int(active), "notes": notes})
                created = []
                if auto_component:
                    try:
                        if category == "protein":
                            insert_row("proteins", {"ingredient_id": new_ingredient_id, "cost_level": "", "energy_level": "", "notes": ""})
                            created.append("protein component")
                        elif category == "vegetable":
                            insert_row("vegetables", {"ingredient_id": new_ingredient_id, "soft_texture_possible": 0, "cooks_fast": 0, "notes": ""})
                            created.append("vegetable component")
                        elif category == "foundation":
                            if not row_exists("foundations", "name", clean_name):
                                insert_row("foundations", {"name": clean_name, "foundation_type": "", "texture": "", "pantry_style": storage, "energy_level": "", "good_with_gravy": 0, "good_with_sauce": 0, "notes": "Created from ingredient."})
                                created.append("foundation")
                    except Exception as e:
                        st.warning(f"Ingredient was added, but the matching component was not created: {e}")
                suffix = f" and created {', '.join(created)}" if created else ""
                st.success(f"Added ingredient: {clean_name}{suffix}."); st.rerun()
    df = df_search("ingredients", "SELECT * FROM ingredients ORDER BY name")
    st.dataframe(df, width="stretch")
    st.subheader("Edit / Delete Ingredient")
    row = row_selector(df, "ingredient_id", "name", "ingredient_select")
    if row:
        linked = ingredient_is_linked(row["ingredient_id"])
        if linked:
            st.info("This ingredient is linked to: " + usage_text(ingredient_usage(row["ingredient_id"])) + ". Name/category are locked here to prevent corrupting component links. Use Admin Editor/component rows to reassign first, or mark inactive.")
        with st.form("edit_ingredient"):
            c1,c2,c3 = st.columns(3)
            e_name = c1.text_input("Ingredient Name", value=row.get("name", ""), disabled=linked)
            e_category = c2.selectbox("Category", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(row.get("category")) if row.get("category") in CATEGORY_OPTIONS else 0, disabled=linked)
            e_storage = c3.selectbox("Default Storage", STORAGE_OPTIONS, index=STORAGE_OPTIONS.index(row.get("default_storage")) if row.get("default_storage") in STORAGE_OPTIONS else 0)
            c4,c5,c6,c7,c8 = st.columns(5)
            e_dairy = c4.checkbox("Contains Dairy", value=bool(row.get("dairy_flag",0))); e_gluten = c5.checkbox("Contains Gluten", value=bool(row.get("gluten_flag",0))); e_pork = c6.checkbox("Contains Pork", value=bool(row.get("pork_flag",0))); e_egg = c7.checkbox("Contains Egg", value=bool(row.get("egg_flag",0))); e_active = c8.checkbox("Active", value=bool(row.get("active",1)))
            e_notes = st.text_area("Notes", value=row.get("notes") or "")
            save = st.form_submit_button("Save Ingredient")
        if save:
            save_name = row["name"] if linked else e_name.strip()
            save_category = row["category"] if linked else e_category
            if row_exists("ingredients", "name", save_name, "ingredient_id", row["ingredient_id"]): st.warning(f"{save_name} already exists on another row.")
            else:
                update_row("ingredients", "ingredient_id", row["ingredient_id"], {"name": save_name, "category": save_category, "default_storage": e_storage, "dairy_flag": int(e_dairy), "gluten_flag": int(e_gluten), "pork_flag": int(e_pork), "egg_flag": int(e_egg), "active": int(e_active), "notes": e_notes})
                st.success("Ingredient updated."); st.rerun()
        with st.expander("Delete selected ingredient"):
            usages = ingredient_usage(row["ingredient_id"])
            if usages:
                st.warning("Cannot safely delete because this ingredient is used by: " + usage_text(usages))
                if st.button("Mark Ingredient Inactive Instead", key="inactive_ingredient"):
                    update_row("ingredients", "ingredient_id", row["ingredient_id"], {"active": 0})
                    st.success("Ingredient marked inactive.")
                    st.rerun()
            else:
                st.warning(f"Delete: {row['name']}?")
                if st.button("Confirm Delete", key="delete_ingredient"):
                    result = safe_delete("ingredients", "ingredient_id", row["ingredient_id"])
                    if result["ok"]:
                        st.success(result["message"]); st.rerun()
                    else:
                        st.error(result["message"])

with tabs[2]:
    st.header("Components")
    component_tab = st.radio("Component Type", ["Protein", "Vegetable", "Foundation", "Ingredient State", "Ingredient Alias", "Equipment", "Technique", "Sauce"], horizontal=True)
    if component_tab == "Protein":
        ingredients = fetch_options("ingredients", "ingredient_id", "name", "category='protein' AND active=1")
        techniques = fetch_options("techniques", "technique_id", "name")
        if ingredients:
            labels=[x[1] for x in ingredients]
            with st.form("add_protein"):
                selected=st.selectbox("Ingredient", labels); ingredient_id=ingredients[labels.index(selected)][0]
                c1,c2,c3=st.columns(3); animal_source=c1.selectbox("Animal Source", ANIMAL_SOURCE_OPTIONS); meat_color=c2.selectbox("Meat Color", MEAT_COLOR_OPTIONS); default_prep=c3.selectbox("Default Prep", PREP_OPTIONS)
                c4,c5=st.columns(2); cost=c4.selectbox("Cost Level", COST_OPTIONS); energy=c5.selectbox("Energy Level", LEVEL_OPTIONS)
                technique_id=None
                if techniques:
                    t_labels=[""]+[x[1] for x in techniques]; t_selected=st.selectbox("Default Technique", t_labels)
                    if t_selected: technique_id=techniques[[x[1] for x in techniques].index(t_selected)][0]
                notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Protein")
            if submitted:
                try:
                    insert_row("proteins", {"ingredient_id": ingredient_id, "default_technique_id": technique_id, "cost_level": cost, "energy_level": energy, "animal_source": animal_source, "meat_color": meat_color, "default_prep": default_prep, "notes": notes})
                    st.success("Protein added."); st.rerun()
                except Exception as e: st.error(f"Could not add protein. It may already exist. Details: {e}")
        df=df_search("proteins", lookup_display_sql("proteins"))
        st.dataframe(df, width="stretch")
        st.subheader("Edit / Delete Protein")
        edit_df = fetch_df("SELECT * FROM proteins ORDER BY protein_id")
        prow = row_selector(fetch_df("SELECT p.protein_id, i.name AS ingredient_name FROM proteins p JOIN ingredients i ON p.ingredient_id=i.ingredient_id ORDER BY i.name"), "protein_id", "ingredient_name", "protein_edit_select")
        if prow:
            full = fetch_df("SELECT * FROM proteins WHERE protein_id=?", [prow["protein_id"]]).iloc[0].to_dict()
            with st.form(f"edit_protein_{prow['protein_id']}"):
                ing_id = select_from_options("Ingredient", fetch_options("ingredients", "ingredient_id", "name", "category='protein' AND active=1"), full.get("ingredient_id"), key=f"protein_ing_{prow['protein_id']}")
                tech_id = select_from_options("Default Technique", fetch_options("techniques", "technique_id", "name"), full.get("default_technique_id"), key=f"protein_tech_{prow['protein_id']}")
                c1,c2,c3=st.columns(3)
                animal_source=c1.selectbox("Animal Source", ANIMAL_SOURCE_OPTIONS, index=ANIMAL_SOURCE_OPTIONS.index(full.get("animal_source")) if full.get("animal_source") in ANIMAL_SOURCE_OPTIONS else 0)
                meat_color=c2.selectbox("Meat Color", MEAT_COLOR_OPTIONS, index=MEAT_COLOR_OPTIONS.index(full.get("meat_color")) if full.get("meat_color") in MEAT_COLOR_OPTIONS else 0)
                default_prep=c3.selectbox("Default Prep", PREP_OPTIONS, index=PREP_OPTIONS.index(full.get("default_prep")) if full.get("default_prep") in PREP_OPTIONS else 0)
                c4,c5=st.columns(2)
                cost=c4.selectbox("Cost Level", COST_OPTIONS, index=COST_OPTIONS.index(full.get("cost_level")) if full.get("cost_level") in COST_OPTIONS else 0)
                energy=c5.selectbox("Energy Level", LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(full.get("energy_level")) if full.get("energy_level") in LEVEL_OPTIONS else 0)
                notes=st.text_area("Notes", value=full.get("notes") or "")
                savep=st.form_submit_button("Save Protein")
            if savep:
                try:
                    update_row("proteins", "protein_id", prow["protein_id"], {"ingredient_id": ing_id, "default_technique_id": tech_id, "cost_level": cost, "energy_level": energy, "animal_source": animal_source, "meat_color": meat_color, "default_prep": default_prep, "notes": notes})
                    st.success("Protein updated."); st.rerun()
                except Exception as e: st.error(f"Could not update protein: {e}")
            with st.expander("Delete selected protein"):
                confirm_delete("proteins", "protein_id", prow["protein_id"], prow["ingredient_name"], f"delete_protein_{prow['protein_id']}")
    elif component_tab == "Vegetable":
        ingredients=fetch_options("ingredients", "ingredient_id", "name", "category='vegetable' AND active=1"); prep=fetch_options("prep_forms", "prep_id", "prep_name")
        if ingredients:
            labels=[x[1] for x in ingredients]
            with st.form("add_vegetable"):
                selected=st.selectbox("Ingredient", labels); ingredient_id=ingredients[labels.index(selected)][0]
                prep_id=None
                if prep:
                    prep_labels=[""]+[x[1] for x in prep]; prep_selected=st.selectbox("Common Prep", prep_labels)
                    if prep_selected: prep_id=prep[[x[1] for x in prep].index(prep_selected)][0]
                soft=st.checkbox("Soft Texture Possible"); fast=st.checkbox("Cooks Fast"); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Vegetable")
            if submitted:
                try: insert_row("vegetables", {"ingredient_id": ingredient_id, "common_prep_id": prep_id, "soft_texture_possible": int(soft), "cooks_fast": int(fast), "notes": notes}); st.success("Vegetable added."); st.rerun()
                except Exception as e: st.error(f"Could not add vegetable. It may already exist. Details: {e}")
        vdf = df_search("vegetables", lookup_display_sql("vegetables"))
        st.dataframe(vdf, width="stretch")
        st.subheader("Edit / Delete Vegetable")
        vrow = row_selector(fetch_df("SELECT v.vegetable_id, i.name AS ingredient_name FROM vegetables v JOIN ingredients i ON v.ingredient_id=i.ingredient_id ORDER BY i.name"), "vegetable_id", "ingredient_name", "vegetable_edit_select")
        if vrow:
            full = fetch_df("SELECT * FROM vegetables WHERE vegetable_id=?", [vrow["vegetable_id"]]).iloc[0].to_dict()
            with st.form(f"edit_vegetable_{vrow['vegetable_id']}"):
                ing_id = select_from_options("Ingredient", fetch_options("ingredients", "ingredient_id", "name", "category='vegetable' AND active=1"), full.get("ingredient_id"), key=f"veg_ing_{vrow['vegetable_id']}")
                prep_id = select_from_options("Common Prep", fetch_options("prep_forms", "prep_id", "prep_name"), full.get("common_prep_id"), key=f"veg_prep_{vrow['vegetable_id']}")
                soft=st.checkbox("Soft Texture Possible", value=bool(full.get("soft_texture_possible",0)))
                fast=st.checkbox("Cooks Fast", value=bool(full.get("cooks_fast",0)))
                notes=st.text_area("Notes", value=full.get("notes") or "")
                savev=st.form_submit_button("Save Vegetable")
            if savev:
                try:
                    update_row("vegetables", "vegetable_id", vrow["vegetable_id"], {"ingredient_id": ing_id, "common_prep_id": prep_id, "soft_texture_possible": int(soft), "cooks_fast": int(fast), "notes": notes})
                    st.success("Vegetable updated."); st.rerun()
                except Exception as e: st.error(f"Could not update vegetable: {e}")
            with st.expander("Delete selected vegetable"):
                confirm_delete("vegetables", "vegetable_id", vrow["vegetable_id"], vrow["ingredient_name"], f"delete_vegetable_{vrow['vegetable_id']}")
    elif component_tab == "Foundation":
        with st.form("foundation_form"):
            name=st.text_input("Foundation Name")
            c1,c2,c3=st.columns(3)
            ftype=c1.selectbox("Foundation Type", FOUNDATION_TYPE_OPTIONS)
            texture=c2.selectbox("Texture", TEXTURE_OPTIONS)
            pantry_style=c3.selectbox("Pantry Style", PANTRY_STYLE_OPTIONS)
            energy=st.selectbox("Energy Level", LEVEL_OPTIONS); gravy=st.checkbox("Good with Gravy"); sauce=st.checkbox("Good with Sauce"); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Foundation")
        if submitted:
            if row_exists("foundations", "name", name.strip()): st.warning("Foundation already exists.")
            else: insert_row("foundations", {"name": name.strip(), "foundation_type": ftype, "texture": texture, "pantry_style": pantry_style, "energy_level": energy, "good_with_gravy": int(gravy), "good_with_sauce": int(sauce), "notes": notes}); st.success("Foundation added."); st.rerun()
        fdf = df_search("foundations", "SELECT * FROM foundations ORDER BY name")
        st.dataframe(fdf, width="stretch")
        st.subheader("Edit / Delete Foundation")
        frow = row_selector(fdf, "foundation_id", "name", "foundation_edit_select")
        if frow:
            with st.form(f"edit_foundation_{frow['foundation_id']}"):
                ename=st.text_input("Foundation Name", value=frow.get("name", ""))
                c1,c2,c3=st.columns(3)
                eftype=c1.selectbox("Foundation Type", FOUNDATION_TYPE_OPTIONS, index=FOUNDATION_TYPE_OPTIONS.index(frow.get("foundation_type")) if frow.get("foundation_type") in FOUNDATION_TYPE_OPTIONS else 0)
                etexture=c2.selectbox("Texture", TEXTURE_OPTIONS, index=TEXTURE_OPTIONS.index(frow.get("texture")) if frow.get("texture") in TEXTURE_OPTIONS else 0)
                epantry=c3.selectbox("Pantry Style", PANTRY_STYLE_OPTIONS, index=PANTRY_STYLE_OPTIONS.index(frow.get("pantry_style")) if frow.get("pantry_style") in PANTRY_STYLE_OPTIONS else 0)
                eenergy=st.selectbox("Energy Level", LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(frow.get("energy_level")) if frow.get("energy_level") in LEVEL_OPTIONS else 0)
                egravy=st.checkbox("Good with Gravy", value=bool(frow.get("good_with_gravy",0)))
                esauce=st.checkbox("Good with Sauce", value=bool(frow.get("good_with_sauce",0)))
                enotes=st.text_area("Notes", value=frow.get("notes") or "")
                savef=st.form_submit_button("Save Foundation")
            if savef:
                if row_exists("foundations", "name", ename.strip(), "foundation_id", frow["foundation_id"]): st.warning("Foundation name already exists on another row.")
                else:
                    update_row("foundations", "foundation_id", frow["foundation_id"], {"name": ename.strip(), "foundation_type": eftype, "texture": etexture, "pantry_style": epantry, "energy_level": eenergy, "good_with_gravy": int(egravy), "good_with_sauce": int(esauce), "notes": enotes})
                    st.success("Foundation updated."); st.rerun()
            with st.expander("Delete selected foundation"):
                confirm_delete("foundations", "foundation_id", frow["foundation_id"], frow["name"], f"delete_foundation_{frow['foundation_id']}")
    elif component_tab == "Ingredient State":
        st.write("Ingredient state tells SNS how the ingredient exists right now. Energy comes from state + technique, not from the ingredient itself.")
        ingredients = fetch_options("ingredients", "ingredient_id", "name", "active=1")
        if ingredients:
            labels = [x[1] for x in ingredients]
            with st.form("add_ingredient_state"):
                selected = st.selectbox("Ingredient", labels)
                ingredient_id = ingredients[labels.index(selected)][0]
                c1, c2, c3 = st.columns(3)
                state_name = c1.selectbox("State", STATE_OPTIONS)
                storage_location = c2.selectbox("Storage", STORAGE_OPTIONS)
                energy = c3.selectbox("Energy Level", LEVEL_OPTIONS)
                c4, c5, c6, c7 = st.columns(4)
                needs_cooking = c4.checkbox("Needs Cooking")
                ready_to_eat = c5.checkbox("Ready to Eat / Reheat Only")
                prep_minutes = c6.number_input("Prep Minutes", min_value=0, value=0)
                cook_minutes = c7.number_input("Cook Minutes", min_value=0, value=0)
                rank_penalty = st.number_input("Rank Penalty", min_value=0, value=25 if state_name == "Freeze Dried" else 0, help="Freeze-dried should usually rank lower for normal users.")
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Add Ingredient State")
            if submitted:
                try:
                    insert_row("ingredient_states", {
                        "ingredient_id": ingredient_id,
                        "state_name": state_name,
                        "storage_location": storage_location,
                        "needs_cooking": int(needs_cooking),
                        "ready_to_eat": int(ready_to_eat),
                        "typical_prep_minutes": int(prep_minutes),
                        "typical_cook_minutes": int(cook_minutes),
                        "energy_level": energy,
                        "rank_penalty": int(rank_penalty),
                        "notes": notes,
                    })
                    st.success("Ingredient state added."); st.rerun()
                except Exception as e:
                    st.error(f"Could not add ingredient state. It may already exist for this ingredient. Details: {e}")
        st.dataframe(df_search("ingredient_states", lookup_display_sql("ingredient_states")), width="stretch")
        st.subheader("Edit / Delete Ingredient State")
        srow = row_selector(fetch_df("SELECT s.state_id, i.name || ' — ' || s.state_name AS label FROM ingredient_states s JOIN ingredients i ON s.ingredient_id=i.ingredient_id ORDER BY i.name, s.state_name"), "state_id", "label", "state_edit_select")
        if srow:
            full = fetch_df("SELECT * FROM ingredient_states WHERE state_id=?", [srow["state_id"]]).iloc[0].to_dict()
            with st.form(f"edit_state_{srow['state_id']}"):
                ing_id = select_from_options("Ingredient", fetch_options("ingredients", "ingredient_id", "name", "active=1"), full.get("ingredient_id"), key=f"state_ing_{srow['state_id']}")
                c1,c2,c3=st.columns(3)
                state_name = c1.selectbox("State", STATE_OPTIONS, index=STATE_OPTIONS.index(full.get("state_name")) if full.get("state_name") in STATE_OPTIONS else 0)
                storage_location = c2.selectbox("Storage", STORAGE_OPTIONS, index=STORAGE_OPTIONS.index(full.get("storage_location")) if full.get("storage_location") in STORAGE_OPTIONS else 0)
                energy = c3.selectbox("Energy Level", LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(full.get("energy_level")) if full.get("energy_level") in LEVEL_OPTIONS else 0)
                c4,c5,c6,c7=st.columns(4)
                needs_cooking = c4.checkbox("Needs Cooking", value=bool(full.get("needs_cooking",0)))
                ready_to_eat = c5.checkbox("Ready to Eat / Reheat Only", value=bool(full.get("ready_to_eat",0)))
                prep_minutes = c6.number_input("Prep Minutes", min_value=0, value=int(full.get("typical_prep_minutes") or 0))
                cook_minutes = c7.number_input("Cook Minutes", min_value=0, value=int(full.get("typical_cook_minutes") or 0))
                rank_penalty = st.number_input("Rank Penalty", min_value=0, value=int(full.get("rank_penalty") or 0))
                notes = st.text_area("Notes", value=full.get("notes") or "")
                saves = st.form_submit_button("Save Ingredient State")
            if saves:
                try:
                    update_row("ingredient_states", "state_id", srow["state_id"], {"ingredient_id": ing_id, "state_name": state_name, "storage_location": storage_location, "needs_cooking": int(needs_cooking), "ready_to_eat": int(ready_to_eat), "typical_prep_minutes": int(prep_minutes), "typical_cook_minutes": int(cook_minutes), "energy_level": energy, "rank_penalty": int(rank_penalty), "notes": notes})
                    st.success("Ingredient state updated."); st.rerun()
                except Exception as e: st.error(f"Could not update state: {e}")
            with st.expander("Delete selected ingredient state"):
                confirm_delete("ingredient_states", "state_id", srow["state_id"], srow["label"], f"delete_state_{srow['state_id']}")

    elif component_tab == "Ingredient Alias":
        st.write("Aliases let users type normal kitchen words while SNS links them back to one canonical ingredient.")
        ingredients = fetch_options("ingredients", "ingredient_id", "name", "active=1")
        if ingredients:
            labels = [x[1] for x in ingredients]
            with st.form("add_ingredient_alias"):
                selected = st.selectbox("Canonical Ingredient", labels)
                ingredient_id = ingredients[labels.index(selected)][0]
                alias_name = st.text_input("Alias / Synonym")
                alias_type = st.selectbox("Alias Type", ["synonym", "common name", "regional name", "brand shorthand", "misspelling", "search term"])
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Add Alias")
            if submitted:
                clean_alias = alias_name.strip()
                if not clean_alias:
                    st.error("Alias is required.")
                elif row_exists("ingredient_aliases", "alias_name", clean_alias):
                    st.warning(f"{clean_alias} already exists as an alias.")
                else:
                    insert_row("ingredient_aliases", {"ingredient_id": ingredient_id, "alias_name": clean_alias, "alias_type": alias_type, "notes": notes})
                    st.success("Alias added."); st.rerun()
        st.dataframe(df_search("ingredient_aliases", lookup_display_sql("ingredient_aliases")), width="stretch")
        st.subheader("Edit / Delete Ingredient Alias")
        arow = row_selector(fetch_df("SELECT alias_id, alias_name FROM ingredient_aliases ORDER BY alias_name"), "alias_id", "alias_name", "alias_edit_select")
        if arow:
            full = fetch_df("SELECT * FROM ingredient_aliases WHERE alias_id=?", [arow["alias_id"]]).iloc[0].to_dict()
            with st.form(f"edit_alias_{arow['alias_id']}"):
                ing_id = select_from_options("Canonical Ingredient", fetch_options("ingredients", "ingredient_id", "name", "active=1"), full.get("ingredient_id"), key=f"alias_ing_{arow['alias_id']}")
                alias_name = st.text_input("Alias / Synonym", value=full.get("alias_name") or "")
                alias_type = st.selectbox("Alias Type", ALIAS_TYPE_OPTIONS, index=ALIAS_TYPE_OPTIONS.index(full.get("alias_type")) if full.get("alias_type") in ALIAS_TYPE_OPTIONS else 0)
                notes = st.text_area("Notes", value=full.get("notes") or "")
                savea = st.form_submit_button("Save Alias")
            if savea:
                clean_alias=alias_name.strip()
                if row_exists("ingredient_aliases", "alias_name", clean_alias, "alias_id", arow["alias_id"]): st.warning("Alias already exists on another row.")
                else:
                    update_row("ingredient_aliases", "alias_id", arow["alias_id"], {"ingredient_id": ing_id, "alias_name": clean_alias, "alias_type": alias_type, "notes": notes})
                    st.success("Alias updated."); st.rerun()
            with st.expander("Delete selected alias"):
                confirm_delete("ingredient_aliases", "alias_id", arow["alias_id"], arow["alias_name"], f"delete_alias_{arow['alias_id']}")

    elif component_tab == "Equipment":
        with st.form("equipment_form"):
            name=st.text_input("Equipment Name"); etype=st.selectbox("Equipment Type", EQUIPMENT_TYPE_OPTIONS); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Equipment")
        if submitted:
            if row_exists("equipment", "name", name.strip()): st.warning("Equipment already exists.")
            else: insert_row("equipment", {"name": name.strip(), "equipment_type": etype, "notes": notes}); st.success("Equipment added."); st.rerun()
        edf = df_search("equipment", "SELECT * FROM equipment ORDER BY name")
        st.dataframe(edf, width="stretch")
        st.subheader("Edit / Delete Equipment")
        erow = row_selector(edf, "equipment_id", "name", "equipment_edit_select")
        if erow:
            with st.form(f"edit_equipment_{erow['equipment_id']}"):
                ename = st.text_input("Equipment Name", value=erow.get("name", ""))
                etype = st.selectbox("Equipment Type", EQUIPMENT_TYPE_OPTIONS, index=EQUIPMENT_TYPE_OPTIONS.index(erow.get("equipment_type")) if erow.get("equipment_type") in EQUIPMENT_TYPE_OPTIONS else 0)
                enotes = st.text_area("Notes", value=erow.get("notes") or "")
                savee = st.form_submit_button("Save Equipment")
            if savee:
                if row_exists("equipment", "name", ename.strip(), "equipment_id", erow["equipment_id"]): st.warning("Equipment name already exists on another row.")
                else:
                    update_row("equipment", "equipment_id", erow["equipment_id"], {"name": ename.strip(), "equipment_type": etype, "notes": enotes})
                    st.success("Equipment updated."); st.rerun()
            with st.expander("Delete selected equipment"):
                confirm_delete("equipment", "equipment_id", erow["equipment_id"], erow["name"], f"delete_equipment_{erow['equipment_id']}")
    elif component_tab == "Technique":
        st.info("Technique maintenance is basic in this build. Deeper technique mapping is still a later release, but add/edit/delete now works for the technique lookup table.")
        with st.form("technique_form"):
            name=st.text_input("Technique Name")
            eq_id = select_from_options("Equipment", fetch_options("equipment", "equipment_id", "name"), None, key="technique_add_equipment")
            c1,c2,c3=st.columns(3)
            active=c1.number_input("Active Minutes", min_value=0, value=0)
            passive=c2.number_input("Passive Minutes", min_value=0, value=0)
            energy=c3.selectbox("Energy Level", LEVEL_OPTIONS)
            template=st.text_area("Instruction Template")
            notes=st.text_area("Notes")
            submitted=st.form_submit_button("Add Technique")
        if submitted:
            if row_exists("techniques", "name", name.strip()): st.warning("Technique already exists.")
            else: insert_row("techniques", {"name": name.strip(), "equipment_id": eq_id, "active_time_minutes": int(active), "passive_time_minutes": int(passive), "energy_level": energy, "instruction_template": template, "notes": notes}); st.success("Technique added."); st.rerun()
        tdf=df_search("techniques", """SELECT t.technique_id, t.name, e.name AS equipment_name, t.active_time_minutes, t.passive_time_minutes, t.energy_level, t.instruction_template, t.notes FROM techniques t LEFT JOIN equipment e ON t.equipment_id=e.equipment_id ORDER BY t.name""")
        st.dataframe(tdf, width="stretch")
        st.subheader("Edit / Delete Technique")
        trow = row_selector(fetch_df("SELECT technique_id, name FROM techniques ORDER BY name"), "technique_id", "name", "technique_edit_select")
        if trow:
            full = fetch_df("SELECT * FROM techniques WHERE technique_id=?", [trow["technique_id"]]).iloc[0].to_dict()
            with st.form(f"edit_technique_{trow['technique_id']}"):
                tname=st.text_input("Technique Name", value=full.get("name") or "")
                eq_id=select_from_options("Equipment", fetch_options("equipment", "equipment_id", "name"), full.get("equipment_id"), key=f"tech_eq_{trow['technique_id']}")
                c1,c2,c3=st.columns(3)
                active=c1.number_input("Active Minutes", min_value=0, value=int(full.get("active_time_minutes") or 0))
                passive=c2.number_input("Passive Minutes", min_value=0, value=int(full.get("passive_time_minutes") or 0))
                energy=c3.selectbox("Energy Level", LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(full.get("energy_level")) if full.get("energy_level") in LEVEL_OPTIONS else 0)
                template=st.text_area("Instruction Template", value=full.get("instruction_template") or "")
                notes=st.text_area("Notes", value=full.get("notes") or "")
                savet=st.form_submit_button("Save Technique")
            if savet:
                if row_exists("techniques", "name", tname.strip(), "technique_id", trow["technique_id"]): st.warning("Technique name already exists on another row.")
                else:
                    update_row("techniques", "technique_id", trow["technique_id"], {"name": tname.strip(), "equipment_id": eq_id, "active_time_minutes": int(active), "passive_time_minutes": int(passive), "energy_level": energy, "instruction_template": template, "notes": notes})
                    st.success("Technique updated."); st.rerun()
            with st.expander("Delete selected technique"):
                confirm_delete("techniques", "technique_id", trow["technique_id"], trow["name"], f"delete_technique_{trow['technique_id']}")
    elif component_tab == "Sauce":
        st.info("Sauces are now mostly internal/admin data. Users choose Cuisine instead.")
        with st.form("sauce_form"):
            name=st.text_input("Sauce Name"); family=st.text_input("Sauce Family"); dairy=st.text_input("Dairy Status"); thickener=st.text_input("Thickener Type"); energy=st.selectbox("Energy Level", LEVEL_OPTIONS); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Sauce")
        if submitted:
            if row_exists("sauces", "name", name.strip()): st.warning("Sauce already exists.")
            else: insert_row("sauces", {"name": name.strip(), "sauce_family": family, "dairy_status": dairy, "thickener_type": thickener, "energy_level": energy, "notes": notes}); st.success("Sauce added."); st.rerun()
        sdf=df_search("sauces", "SELECT * FROM sauces ORDER BY name")
        st.dataframe(sdf, width="stretch")
        st.subheader("Edit / Delete Sauce")
        srow = row_selector(sdf, "sauce_id", "name", "sauce_edit_select")
        if srow:
            with st.form(f"edit_sauce_{srow['sauce_id']}"):
                sname=st.text_input("Sauce Name", value=srow.get("name", "")); family=st.text_input("Sauce Family", value=srow.get("sauce_family") or ""); dairy=st.text_input("Dairy Status", value=srow.get("dairy_status") or ""); thickener=st.text_input("Thickener Type", value=srow.get("thickener_type") or ""); energy=st.selectbox("Energy Level", LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(srow.get("energy_level")) if srow.get("energy_level") in LEVEL_OPTIONS else 0); notes=st.text_area("Notes", value=srow.get("notes") or ""); saves=st.form_submit_button("Save Sauce")
            if saves:
                if row_exists("sauces", "name", sname.strip(), "sauce_id", srow["sauce_id"]): st.warning("Sauce name already exists on another row.")
                else:
                    update_row("sauces", "sauce_id", srow["sauce_id"], {"name": sname.strip(), "sauce_family": family, "dairy_status": dairy, "thickener_type": thickener, "energy_level": energy, "notes": notes})
                    st.success("Sauce updated."); st.rerun()
            with st.expander("Delete selected sauce"):
                confirm_delete("sauces", "sauce_id", srow["sauce_id"], srow["name"], f"delete_sauce_{srow['sauce_id']}")

with tabs[3]:
    st.header("Cuisines")
    st.write("Cuisine is the user-facing flavor choice. Sauces and seasonings are engine decisions.")
    with st.form("cuisine_form"):
        c1,c2,c3=st.columns(3); name=c1.text_input("Cuisine Name"); family=c2.text_input("Cuisine Family"); spice=c3.selectbox("Spice Level", ["None", "Mild", "Medium", "Hot"])
        default_sauce_family=st.text_input("Default Sauce / Seasoning Direction"); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Cuisine")
    if submitted:
        if row_exists("cuisines", "name", name.strip()): st.warning("Cuisine already exists.")
        else: insert_row("cuisines", {"name": name.strip(), "cuisine_family": family, "spice_level": spice, "default_sauce_family": default_sauce_family, "notes": notes}); st.success("Cuisine added."); st.rerun()
    st.dataframe(df_search("cuisines", "SELECT * FROM cuisines ORDER BY name"), width="stretch")

with tabs[4]:
    st.header("Nutrition")
    st.write("Nutrition scaffold per ingredient per 100g.")
    ingredients=fetch_options("ingredients", "ingredient_id", "name")
    if ingredients:
        labels=[x[1] for x in ingredients]
        with st.form("nutrition_form"):
            selected=st.selectbox("Ingredient", labels); ingredient_id=ingredients[labels.index(selected)][0]
            c1,c2,c3=st.columns(3); calories=c1.number_input("Calories / 100g", min_value=0.0); protein_g=c2.number_input("Protein g / 100g", min_value=0.0); carbs_g=c3.number_input("Carbs g / 100g", min_value=0.0)
            c4,c5,c6=st.columns(3); fat_g=c4.number_input("Fat g / 100g", min_value=0.0); fiber_g=c5.number_input("Fiber g / 100g", min_value=0.0); sodium=c6.number_input("Sodium mg / 100g", min_value=0.0)
            source=st.text_input("Source"); notes=st.text_area("Notes"); submitted=st.form_submit_button("Add Nutrition Row")
        if submitted:
            try: insert_row("ingredient_nutrition", {"ingredient_id": ingredient_id, "calories_per_100g": calories, "protein_g_per_100g": protein_g, "carbs_g_per_100g": carbs_g, "fat_g_per_100g": fat_g, "fiber_g_per_100g": fiber_g, "sodium_mg_per_100g": sodium, "source": source, "notes": notes}); st.success("Nutrition row added."); st.rerun()
            except Exception as e: st.error(f"Could not add nutrition row. It may already exist. Details: {e}")
    st.dataframe(df_search("nutrition", """SELECT n.*, i.name AS ingredient_name FROM ingredient_nutrition n JOIN ingredients i ON n.ingredient_id=i.ingredient_id ORDER BY i.name"""), width="stretch")

with tabs[5]:
    st.header("User Profile")
    st.write("Profile scaffold for exclusions/preferences. Exclusions should remove items from recommendations later.")
    with st.form("user_form"):
        display_name=st.text_input("Display Name"); c1,c2,c3=st.columns(3); default_servings=c1.number_input("Default Servings", 1, 24, 4); budget_preference=c2.selectbox("Budget Preference", BUDGET_OPTIONS); energy_default=c3.selectbox("Default Energy", LEVEL_OPTIONS); leftovers_ok=st.checkbox("Leftovers OK", value=True); submitted=st.form_submit_button("Add User")
    if submitted and display_name.strip(): insert_row("users", {"display_name": display_name.strip(), "default_servings": int(default_servings), "leftovers_ok": int(leftovers_ok), "budget_preference": budget_preference, "energy_default": energy_default}); st.success("User added."); st.rerun()
    st.dataframe(df_search("users", "SELECT * FROM users ORDER BY display_name"), width="stretch")
    st.dataframe(df_search("prefs", "SELECT * FROM user_preferences ORDER BY preference_id DESC"), width="stretch")

with tabs[6]:
    st.header("Signature Recipes")
    st.dataframe(df_search("signature", "SELECT * FROM signature_recipes ORDER BY recipe_name"), width="stretch")


with tabs[7]:
    st.header("Admin Editor")
    st.write("Visible add/edit/delete console for fixing training data without writing SQL. Pick a table, search, choose a row, edit fields, then save or delete.")

    ADMIN_TABLES = {
        "ingredients": "ingredient_id",
        "proteins": "protein_id",
        "vegetables": "vegetable_id",
        "foundations": "foundation_id",
        "cuisines": "cuisine_id",
        "sauces": "sauce_id",
        "equipment": "equipment_id",
        "techniques": "technique_id",
        "prep_forms": "prep_id",
        "ingredient_forms": "form_id",
        "ingredient_aliases": "alias_id",
        "ingredient_states": "state_id",
        "ingredient_nutrition": "nutrition_id",
        "users": "user_id",
        "user_preferences": "preference_id",
        "signature_recipes": "recipe_id",
        "meal_templates": "template_id",
    }

    def _admin_label(table_name, row_dict):
        try:
            if table_name == "proteins":
                return fetch_df("SELECT name FROM ingredients WHERE ingredient_id=?", [row_dict.get("ingredient_id")]).iloc[0]["name"]
            if table_name == "vegetables":
                return fetch_df("SELECT name FROM ingredients WHERE ingredient_id=?", [row_dict.get("ingredient_id")]).iloc[0]["name"]
            if table_name == "ingredient_states":
                nm = fetch_df("SELECT name FROM ingredients WHERE ingredient_id=?", [row_dict.get("ingredient_id")]).iloc[0]["name"]
                return f"{nm} — {row_dict.get('state_name','')}"
            if table_name == "ingredient_aliases":
                return f"{row_dict.get('alias_name','')}"
            if table_name == "ingredient_nutrition":
                nm = fetch_df("SELECT name FROM ingredients WHERE ingredient_id=?", [row_dict.get("ingredient_id")]).iloc[0]["name"]
                return nm
            for c in ["name", "recipe_name", "display_name", "collection_name", "alias_name", "form_name", "prep_name", "state_name"]:
                if c in row_dict and str(row_dict.get(c) or "").strip():
                    return str(row_dict.get(c))
        except Exception:
            pass
        return "row"

    def _select_row_for_admin(table_name, id_col, base_df):
        labels = []
        ids = []
        for _, r in base_df.iterrows():
            rd = r.to_dict()
            rid = int(rd[id_col])
            labels.append(f"{rid}: {_admin_label(table_name, rd)}")
            ids.append(rid)
        choice = st.selectbox("Select row to edit", labels, key=f"admin_{table_name}_row_label")
        return ids[labels.index(choice)]

    def _edit_field(table_name, selected_id, col, val):
        key = f"admin_{table_name}_{selected_id}_{col}"
        if val is None:
            val = ""
        if col == "ingredient_id":
            return select_from_options("Ingredient", fetch_options("ingredients", "ingredient_id", "name"), val, key=key, help_text="Shows ingredient names, stores the linked ingredient ID.")
        if col in ["default_technique_id", "technique_id"]:
            return select_from_options("Technique", fetch_options("techniques", "technique_id", "name"), val, key=key)
        if col in ["equipment_id", "default_equipment_id"]:
            return select_from_options("Equipment", fetch_options("equipment", "equipment_id", "name"), val, key=key)
        if col in ["common_prep_id", "prep_id"]:
            return select_from_options("Prep", fetch_options("prep_forms", "prep_id", "prep_name"), val, key=key)
        if col == "form_id":
            return select_from_options("Form", fetch_options("ingredient_forms", "form_id", "form_name"), val, key=key)
        if col == "user_id":
            return select_from_options("User", fetch_options("users", "user_id", "display_name"), val, key=key)
        if col in ["category"]:
            return st.selectbox(col, CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(val) if val in CATEGORY_OPTIONS else 0, key=key)
        if col in ["default_storage", "storage_location"]:
            return st.selectbox(col, STORAGE_OPTIONS, index=STORAGE_OPTIONS.index(val) if val in STORAGE_OPTIONS else 0, key=key)
        if col in ["energy_level", "energy_default"]:
            return st.selectbox(col, LEVEL_OPTIONS, index=LEVEL_OPTIONS.index(val) if val in LEVEL_OPTIONS else 0, key=key)
        if col in ["cost_level", "budget_preference"]:
            return st.selectbox(col, BUDGET_OPTIONS if col == "budget_preference" else COST_OPTIONS, index=(BUDGET_OPTIONS if col == "budget_preference" else COST_OPTIONS).index(val) if val in (BUDGET_OPTIONS if col == "budget_preference" else COST_OPTIONS) else 0, key=key)
        if col == "animal_source":
            return st.selectbox(col, ANIMAL_SOURCE_OPTIONS, index=ANIMAL_SOURCE_OPTIONS.index(val) if val in ANIMAL_SOURCE_OPTIONS else 0, key=key)
        if col == "meat_color":
            return st.selectbox(col, MEAT_COLOR_OPTIONS, index=MEAT_COLOR_OPTIONS.index(val) if val in MEAT_COLOR_OPTIONS else 0, key=key)
        if col == "default_prep":
            return st.selectbox(col, PREP_OPTIONS, index=PREP_OPTIONS.index(val) if val in PREP_OPTIONS else 0, key=key)
        if col == "state_name":
            return st.selectbox(col, STATE_OPTIONS, index=STATE_OPTIONS.index(val) if val in STATE_OPTIONS else 0, key=key)
        if col == "alias_type":
            return st.selectbox(col, ALIAS_TYPE_OPTIONS, index=ALIAS_TYPE_OPTIONS.index(val) if val in ALIAS_TYPE_OPTIONS else 0, key=key)
        if col == "foundation_type":
            return st.selectbox(col, FOUNDATION_TYPE_OPTIONS, index=FOUNDATION_TYPE_OPTIONS.index(val) if val in FOUNDATION_TYPE_OPTIONS else 0, key=key)
        if col == "texture":
            return st.selectbox(col, TEXTURE_OPTIONS, index=TEXTURE_OPTIONS.index(val) if val in TEXTURE_OPTIONS else 0, key=key)
        if col == "pantry_style":
            return st.selectbox(col, PANTRY_STYLE_OPTIONS, index=PANTRY_STYLE_OPTIONS.index(val) if val in PANTRY_STYLE_OPTIONS else 0, key=key)
        if col == "equipment_type":
            return st.selectbox(col, EQUIPMENT_TYPE_OPTIONS, index=EQUIPMENT_TYPE_OPTIONS.index(val) if val in EQUIPMENT_TYPE_OPTIONS else 0, key=key)
        if isinstance(val, int) and (col.endswith("_flag") or col in ["active", "required", "leftovers_ok", "soft_texture_possible", "cooks_fast", "good_with_gravy", "good_with_sauce", "needs_cooking", "ready_to_eat", "alpha_gal_safe", "would_make_again", "too_hard", "too_bland", "too_spicy", "too_rich", "family_liked"]):
            return int(st.checkbox(col, value=bool(val), key=key))
        if isinstance(val, int):
            return int(st.number_input(col, value=int(val or 0), step=1, key=key))
        if isinstance(val, float):
            return st.number_input(col, value=float(val), key=key)
        if col == "notes" or "notes" in col or col in ["instruction_text", "instruction_template", "why_this_works", "storage_reheat_notes", "comfort_notes", "description"]:
            return st.text_area(col, value=str(val), key=key)
        return st.text_input(col, value=str(val), key=key)

    admin_table = st.selectbox("Table to edit", list(ADMIN_TABLES.keys()), key="admin_table_select")
    admin_id_col = ADMIN_TABLES[admin_table]
    display_query = lookup_display_sql(admin_table) if admin_table in ["proteins", "vegetables", "ingredient_states", "ingredient_aliases", "ingredient_nutrition"] else f"SELECT * FROM {admin_table} ORDER BY {admin_id_col}"
    admin_df = df_search(f"admin_{admin_table}", display_query)
    st.dataframe(admin_df, width="stretch")

    base_df = fetch_df(f"SELECT * FROM {admin_table} ORDER BY {admin_id_col}")
    if not base_df.empty:
        selected_id = _select_row_for_admin(admin_table, admin_id_col, base_df)
        selected_row = fetch_df(f"SELECT * FROM {admin_table} WHERE {admin_id_col} = ?", [selected_id]).iloc[0].to_dict()
        st.subheader(f"Edit {admin_table}: {selected_id} — {_admin_label(admin_table, selected_row)}")
        with st.form(f"admin_edit_{admin_table}_{selected_id}"):
            edited = {}
            for col, val in selected_row.items():
                if col == admin_id_col:
                    st.text_input(col, value=str(val), disabled=True, key=f"admin_{admin_table}_{selected_id}_{col}_locked")
                    continue
                edited[col] = _edit_field(admin_table, selected_id, col, val)
            save_admin = st.form_submit_button("Save Changes")
        if save_admin:
            try:
                if "name" in edited and str(edited.get("name") or "").strip() and row_exists(admin_table, "name", str(edited["name"]).strip(), admin_id_col, selected_id):
                    st.warning("That name already exists on another row.")
                elif admin_table == "ingredient_aliases" and row_exists("ingredient_aliases", "alias_name", str(edited.get("alias_name", "")).strip(), "alias_id", selected_id):
                    st.warning("That alias already exists on another row.")
                else:
                    if admin_table == "ingredients":
                        usages = ingredient_usage(selected_id)
                        if usages:
                            edited["name"] = selected_row.get("name")
                            edited["category"] = selected_row.get("category")
                            st.warning("Ingredient is linked, so name/category were not changed. Linked to: " + usage_text(usages))
                    update_row(admin_table, admin_id_col, selected_id, edited)
                    st.success("Saved.")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")

        with st.expander("Delete this row"):
            st.warning("Deleting rows that are referenced elsewhere may fail. That is safer than breaking the database.")
            if st.button("Delete Selected Row", key=f"admin_delete_{admin_table}_{selected_id}"):
                result = safe_delete(admin_table, admin_id_col, selected_id)
                if result["ok"]:
                    st.success(result["message"])
                    st.rerun()
                else:
                    st.error(result["message"])
                    if admin_table == "ingredients" and st.button("Mark Inactive Instead", key=f"admin_inactive_{selected_id}"):
                        update_row("ingredients", "ingredient_id", selected_id, {"active": 0})
                        st.success("Ingredient marked inactive.")
                        st.rerun()
    else:
        st.info("No rows in this table yet.")

with tabs[8]:
    st.header("Data Browser")
    st.write("General table viewer with search. Use specific admin tabs for safer add/edit/delete.")
    table=st.selectbox("Table", ["ingredients", "ingredient_aliases", "ingredient_forms", "ingredient_states", "ingredient_nutrition", "prep_forms", "proteins", "vegetables", "foundations", "cuisines", "sauces", "flavor_systems", "techniques", "equipment", "meal_templates", "signature_recipes", "users", "user_preferences", "user_inventory", "collections"])
    st.dataframe(df_search(f"browser_{table}", f"SELECT * FROM {table}"), width="stretch")
