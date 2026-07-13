"""UI adapter for the canonical household inventory service."""

from household_inventory import (
    bootstrap_local_household,
    get_household_inventory,
    replace_household_inventory,
    submit_pending_items,
)


def local_context(db_path):
    user_id, household_id = bootstrap_local_household(db_path)
    return {"user_id": user_id, "household_id": household_id}


def load_saved_form_ids(db_path, context):
    return {
        int(item["form_id"])
        for item in get_household_inventory(
            db_path, context["household_id"], context["user_id"]
        )
        if item["form_id"] is not None
    }


def save_inventory(selected, custom_selected, db_path, context):
    saved = replace_household_inventory(
        db_path, context["household_id"], context["user_id"], selected
    )
    pending = submit_pending_items(
        db_path, context["household_id"], context["user_id"], custom_selected
    ) if custom_selected else 0
    return saved, pending


def inventory_payload(context, selected, custom_selected):
    """API-shaped write request; the recipe request needs only household_id."""
    return {
        "household_id": context["household_id"],
        "acting_user_id": context["user_id"],
        "items": selected,
        "pending_items": custom_selected,
        "recipe_request": {"household_id": context["household_id"]},
    }
