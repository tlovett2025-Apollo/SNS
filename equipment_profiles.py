"""Equipment-owned timing and activity graphs for SNS."""

from dataclasses import dataclass
from typing import List

from ingredient_profiles import KitchenActivity
from ko_behavior import resolve_behavior
from config import DB_PATH


@dataclass(frozen=True)
class EquipmentProfile:
    name: str
    lane_name: str
    attention_penalty: int = 0
    notes: str = ""


RICE_COOKER = EquipmentProfile(
    "Rice cooker", "Rice Cooker", 0,
    "Off-burner, low-attention rice cooking.",
)
PRESSURE_COOKER = EquipmentProfile(
    "Pressure cooker", "Pressure Cooker", 1,
    "Off-burner cooking with pressurize, cook, and natural-release phases.",
)


def build_rice_equipment_activities(rice_name: str, equipment_name: str) -> List[KitchenActivity]:
    equipment = equipment_name.lower()
    prep_id = f"prep:{rice_name}"
    if equipment == "rice cooker":
        return [
            KitchenActivity(rice_name, "prep", "Measure the rice and water.", 2, True,
                            equipment="counter", stage="early", activity_id=prep_id),
            KitchenActivity(rice_name, "start", "Load the measured rice and water into the rice cooker, close it, and press Start.", 2, True,
                            attention_load=1.0, equipment="rice cooker", stage="early", depends_on=[prep_id], activity_id=f"start:{rice_name}"),
            KitchenActivity(rice_name, "cook", "Let the rice cooker complete its approximately 18-minute white-rice cycle without opening the lid.", 18, False,
                            attention_load=0.0, equipment="rice cooker", stage="early", depends_on=[f"start:{rice_name}"], activity_id=f"cook:{rice_name}"),
            KitchenActivity(rice_name, "rest", "Leave the rice covered for 5 minutes, then fluff it with a fork.", 5, False,
                            attention_load=0.0, equipment="counter", stage="finish", depends_on=[f"cook:{rice_name}"], activity_id=f"rest:{rice_name}"),
        ]
    if equipment == "pressure cooker":
        behavior = resolve_behavior(rice_name, "foundation", db_path=DB_PATH)
        pressure_minutes = int(behavior.attributes.get("pressure_minutes", 4))
        cooked_elapsed_minutes = int(
            behavior.attributes.get(
                "pressure_cooked_elapsed_minutes",
                10 + pressure_minutes,
            )
        )
        release_minutes = int(behavior.attributes.get("pressure_release_minutes", 10))
        return [
            KitchenActivity(rice_name, "prep", "Measure the rice and water for the pressure cooker.", 2, True,
                            equipment="counter", stage="early", activity_id=prep_id),
            KitchenActivity(rice_name, "start", "Load the rice and water, lock the lid, close the valve, and start high pressure.", 2, True,
                            equipment="pressure cooker", stage="early", depends_on=[prep_id], activity_id=f"start:{rice_name}"),
            # The appliance still owns this entire interval, so scheduling and
            # service timing remain honest.  The cook already pressed Start;
            # narrating pressurizing, cooking, and release as three more recipe
            # steps only creates noise.
            KitchenActivity(
                rice_name,
                "pressure cycle",
                "Pressure-cooker rice cycle (including natural release).",
                cooked_elapsed_minutes + release_minutes,
                False,
                attention_load=0.0,
                equipment="pressure cooker",
                stage="early",
                depends_on=[f"start:{rice_name}"],
                activity_id=f"pressure cycle:{rice_name}",
                show_in_plan=False,
            ),
        ]
    return []


def choose_rice_equipment(available_equipment) -> str:
    available = {str(item).strip().lower() for item in (available_equipment or [])}
    if "rice cooker" in available:
        return "rice cooker"
    if "pressure cooker" in available:
        return "pressure cooker"
    return "stovetop"
