"""Audit regional sample pantries against the operational SNS knowledge base.

The sample pantry file is deliberately browser-native JavaScript.  This
module reads its simple declarative lists so CI can prove that every sample
item resolves to one canonical ingredient and an operational behavior family.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
from io import TextIOWrapper
import json
from pathlib import Path
import re
import sqlite3
from zipfile import ZipFile

from config import DB_PATH
from ko_behavior import default_form_for, resolve_behavior


REPO_ROOT = Path(__file__).resolve().parent
SAMPLE_PANTRY_PATH = REPO_ROOT / "web" / "public-site" / "sample-pantries.js"
SAMPLE_PANTRY_ZIP = REPO_ROOT / "data" / "SNS_Regional_Sample_Pantry_CSVs.zip"
PUBLIC_METHODS = (
    "skillet", "soup", "casserole", "handheld", "grill", "braise", "oven_braise"
)


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("-", " ").split())


def sample_pantry_names(path: str | Path = SAMPLE_PANTRY_PATH) -> tuple[str, ...]:
    """Return each unique ingredient named by the shared and regional lists."""
    source = Path(path).read_text(encoding="utf-8")
    common_match = re.search(r"const common = \[(.*?)\];", source, re.DOTALL)
    definitions_match = re.search(
        r"const definitions = \[(.*?)\n\s*\];", source, re.DOTALL
    )
    if not common_match or not definitions_match:
        raise ValueError("The regional sample pantry declarations could not be read.")
    quoted = re.compile(r'"((?:[^"\\]|\\.)*)"')
    common = quoted.findall(common_match.group(1))
    regional = []
    for line in definitions_match.group(1).splitlines():
        # Each definition contains id, label, description, then its ingredient
        # array.  Only values inside the final array belong to the pantry.
        match = re.search(r",\s*\[(.*)\]\],?\s*$", line)
        if match:
            regional.extend(quoted.findall(match.group(1)))
    return tuple(dict.fromkeys([*common, *regional]))


@dataclass(frozen=True)
class PantryKnowledgeRow:
    sample_name: str
    canonical_name: str
    role: str
    default_form: str
    sample_forms: tuple[str, ...]
    family_codes: tuple[str, ...]
    trained_methods: tuple[str, ...]
    source: str

    @property
    def resolved(self) -> bool:
        return bool(self.canonical_name)

    @property
    def operational(self) -> bool:
        return bool(self.family_codes)


def sample_pantry_forms(path: str | Path = SAMPLE_PANTRY_ZIP) -> dict[str, tuple[str, ...]]:
    """Return the real forms used by the downloadable regional pantries."""
    forms: dict[str, list[str]] = {}
    with ZipFile(path) as archive:
        filenames = sorted(
            name for name in archive.namelist()
            if name.startswith("csv/") and name.endswith(".csv")
        )
        for filename in filenames:
            with archive.open(filename) as raw:
                for row in csv.DictReader(TextIOWrapper(raw, encoding="utf-8-sig")):
                    name = str(row.get("name") or "").strip()
                    form = str(row.get("form") or "").strip()
                    if name and form and form not in forms.setdefault(name, []):
                        forms[name].append(form)
    return {name: tuple(values) for name, values in forms.items()}


def audit_sample_pantries(
    db_path: str | Path = DB_PATH,
    sample_path: str | Path = SAMPLE_PANTRY_PATH,
) -> tuple[PantryKnowledgeRow, ...]:
    names = sample_pantry_names(sample_path)
    forms_by_name = sample_pantry_forms()
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        ingredient_rows = {
            _key(row["name"]): row
            for row in con.execute(
                "SELECT ingredient_id,name,category FROM ingredients WHERE active=1"
            )
        }
        aliases = {
            _key(row["alias_name"]): row["name"]
            for row in con.execute(
                """SELECT a.alias_name,i.name
                     FROM ingredient_aliases a
                     JOIN ingredients i USING (ingredient_id)
                    WHERE i.active=1"""
            )
        }
        protein_ids = {
            int(row[0]) for row in con.execute("SELECT ingredient_id FROM proteins WHERE verified=1")
        }
        vegetable_ids = {
            int(row[0]) for row in con.execute("SELECT ingredient_id FROM vegetables WHERE verified=1")
        }
        foundation_names = {
            _key(row[0]) for row in con.execute("SELECT name FROM foundations WHERE verified=1")
        }

    result = []
    for name in names:
        row = ingredient_rows.get(_key(name))
        canonical = name if row else aliases.get(_key(name), "")
        row = row or ingredient_rows.get(_key(canonical))
        if not row:
            result.append(PantryKnowledgeRow(name, "", "", "", (), (), (), "missing"))
            continue
        ingredient_id = int(row["ingredient_id"])
        if ingredient_id in protein_ids:
            role = "protein"
        elif ingredient_id in vegetable_ids or _key(row["category"]) == "fruit":
            role = "vegetable"
        elif _key(canonical) in foundation_names:
            role = "foundation"
        else:
            role = "ingredient"
        form = default_form_for(canonical, role, db_path)
        sample_forms = forms_by_name.get(name, (form,))
        behavior = resolve_behavior(canonical, role, sample_forms[0], db_path=db_path)
        trained_methods = tuple(
            method for method in PUBLIC_METHODS
            if any(
                resolve_behavior(canonical, role, sample_form, method, db_path).method
                for sample_form in sample_forms
            )
        ) if role in {"protein", "vegetable", "foundation"} else ()
        result.append(PantryKnowledgeRow(
            name,
            canonical,
            role,
            form,
            sample_forms,
            tuple(behavior.family_codes),
            trained_methods,
            behavior.source,
        ))
    return tuple(result)


def audit_summary(rows: tuple[PantryKnowledgeRow, ...]) -> dict:
    return {
        "sample_items": len(rows),
        "resolved_items": sum(row.resolved for row in rows),
        "operational_items": sum(row.operational for row in rows),
        "missing_catalog": [row.sample_name for row in rows if not row.resolved],
        "missing_behavior": [
            row.canonical_name for row in rows if row.resolved and not row.operational
        ],
        "food_role_without_public_method": [
            row.canonical_name
            for row in rows
            if row.role in {"protein", "vegetable", "foundation"}
            and not row.trained_methods
        ],
        "rows": [asdict(row) for row in rows],
    }


if __name__ == "__main__":
    print(json.dumps(audit_summary(audit_sample_pantries()), indent=2))
