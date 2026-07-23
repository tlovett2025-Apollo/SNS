from database import insert_row, fetch_df


def exists(table, name_col, value):
    df = fetch_df(f"SELECT 1 FROM {table} WHERE {name_col} = ? LIMIT 1", [value])
    return not df.empty


def seed():
    for prep in ["diced", "sliced", "chopped", "shredded", "whole", "drained", "rehydrated", "cubed", "ground", "pulled"]:
        if not exists("prep_forms", "prep_name", prep):
            insert_row("prep_forms", {"prep_name": prep, "notes": ""})

    equipment_rows = [
        ("Stock Pot", "pot"),
        ("Saucepan", "pot"),
        ("Frying Pan", "pan"),
        ("Large Skillet", "pan"),
        ("Dutch Oven", "dutch oven"),
        ("Cookie Sheet", "sheet pan"),
        ("9x13 Casserole Dish", "baking dish"),
        ("9x9 Casserole Dish", "baking dish"),
        ("Pizza Pan", "pizza pan"),
        ("Grill", "grill"),
        ("Sous Vide", "sous vide"),
        ("Rice Cooker", "rice cooker"),
        ("Grain Cooker", "grain cooker"),
        ("Wok", "wok"),
        ("Toaster", "toaster"),
        ("Blender", "blender"),
        ("Mixer", "mixer"),
        ("Air Fryer", "small appliance"),
        ("Slow Cooker", "small appliance"),
        ("Instant Pot", "small appliance"),
        ("Microwave", "small appliance"),
        ("Accessory", "accessory"),
        ("Steamer Basket", "accessory"),
        ("Immersion Blender", "blender"),
        ("Food Processor", "small appliance"),
        ("Electric Griddle", "small appliance"),
        ("Roasting Pan", "pan"),
    ]
    for eq, eq_type in equipment_rows:
        if not exists("equipment", "name", eq):
            insert_row("equipment", {"name": eq, "equipment_type": eq_type, "notes": ""})

    for foundation in [("Mashed Potatoes", "potato", "creamy"), ("Rice", "rice", "fluffy"), ("Egg Noodles", "pasta", "tender"), ("Beans", "bean", "hearty"), ("Polenta", "corn", "creamy")]:
        if not exists("foundations", "name", foundation[0]):
            insert_row("foundations", {"name": foundation[0], "foundation_type": foundation[1], "texture": foundation[2], "pantry_style": "Pantry Friendly", "energy_level": "Low", "good_with_gravy": 1, "good_with_sauce": 1, "notes": ""})

    for sauce in [("Mushroom Gravy", "gravy"), ("Tomato Sauce", "tomato"), ("Lemon Sauce", "lemon"), ("Cream Sauce", "cream"), ("Broth Sauce", "broth"), ("Taco Sauce", "mexican"), ("Garlic Butter Sauce", "butter")]:
        if not exists("sauces", "name", sauce[0]):
            insert_row("sauces", {"name": sauce[0], "sauce_family": sauce[1], "dairy_status": "dairy-optional", "thickener_type": "", "energy_level": "Low", "notes": ""})

    for cuisine in [("American", "comfort", "Mild", "gravy"), ("Comfort Food", "comfort", "Mild", "gravy"), ("Italian", "european", "Mild", "tomato/cream"), ("Mexican", "latin", "Medium", "taco"), ("Chinese", "asian", "Mild", "stir-fry"), ("Indian", "asian", "Medium", "curry"), ("Mediterranean", "mediterranean", "Mild", "lemon/herb"), ("BBQ", "american", "Mild", "bbq"), ("Cajun", "american", "Medium", "spiced"), ("Kid Friendly", "family", "None", "dip"), ("Surprise Me", "system", "Mild", "")]:
        if not exists("cuisines", "name", cuisine[0]):
            insert_row("cuisines", {"name": cuisine[0], "cuisine_family": cuisine[1], "spice_level": cuisine[2], "default_sauce_family": cuisine[3], "notes": ""})

    for flavor in ["Woodland", "Taco", "Tagine", "Lemon Herb", "Country Gravy", "Garlic"]:
        if not exists("flavor_systems", "name", flavor):
            insert_row("flavor_systems", {"name": flavor, "cuisine_hint": "", "spice_level": "Mild", "notes": ""})


if __name__ == "__main__":
    seed()
    print("Seed complete.")
