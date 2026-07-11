from culinary_opportunities import discover_opportunities
from recipe_engine import build_recipe_from_candidate, generate_candidates


def candidate(protein="", vegetables=None, foundation=""):
    vegetables = list(vegetables or [])
    return generate_candidates(
        protein,
        " & ".join(vegetables),
        foundation,
        "Comfort Food",
        "Low",
        "Budget",
        45,
        4,
        1,
        vegetable_names=vegetables,
    )[0]


def opportunity_ids(value):
    return {item["opportunity_id"] for item in value.get("opportunities", [])}


def test_mushrooms_publish_fond_opportunity():
    value = candidate("Chicken breast", ["Mushrooms"], "Rice")
    assert "fond_mushroom_browning" in opportunity_ids(value)


def test_chicken_and_mushrooms_publish_relationship_opportunity():
    value = candidate("Chicken breast", ["Mushrooms"], "Rice")
    assert "chicken_mushroom_savory_pairing" in opportunity_ids(value)


def test_chicken_without_mushrooms_does_not_publish_fond_opportunity():
    value = candidate("Chicken breast", ["Broccoli"], "Rice")
    assert "fond_mushroom_browning" not in opportunity_ids(value)
    assert "chicken_mushroom_savory_pairing" not in opportunity_ids(value)


def test_multiple_resources_can_unlock_economy_opportunity():
    value = candidate("Ground beef", [], "")
    value["available_resources"] = ["Oatmeal"]
    discovered = discover_opportunities(value)
    assert "ground_beef_oatmeal_extension" in {item.opportunity_id for item in discovered}


def test_opportunities_flow_into_generated_recipe_debug_without_changing_score():
    value = candidate("Chicken breast", ["Mushrooms"], "Rice")
    original_score = value["score"]
    result = build_recipe_from_candidate(value)
    assert result["opportunities"] == value["opportunities"]
    assert value["score"] == original_score
