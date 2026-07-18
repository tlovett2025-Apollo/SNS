"""Review-first barcode and pantry-photo inventory capture.

External recognition is deliberately separated from persistence.  Every
result from this module is a draft: callers must show it to the cook and the
existing authenticated kitchen save path remains the only way to persist it.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import sqlite3
from contextlib import closing
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from config import DB_PATH


MAX_PHOTO_BYTES = 6 * 1024 * 1024
MAX_CAPTURE_ITEMS = 50
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
BARCODE_PATTERN = re.compile(r"^[0-9]{8,14}$")
DATA_URL_PATTERN = re.compile(
    r"^data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=\r\n]+)$",
    re.IGNORECASE,
)
OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
CAPTURE_NAME_ALIASES = {
    "chicken breasts": "Chicken breast",
    "cooking oil": "Vegetable oil",
    "corn starch": "Cornstarch",
    "rib eye": "Ribeye steak",
    "ribeye": "Ribeye steak",
}


class InventoryCaptureError(ValueError):
    """Raised when capture input or a recognition service cannot be used."""


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


def _float(value: Any, default: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _catalog_version(db_path: str | Path) -> tuple[str, int]:
    path = Path(db_path)
    return str(path), path.stat().st_mtime_ns


@lru_cache(maxsize=4)
def _catalog(path: str, _mtime_ns: int) -> tuple[dict[str, dict], tuple[tuple[str, dict], ...]]:
    exact: dict[str, dict] = {}
    phrases: list[tuple[str, dict]] = []
    with closing(sqlite3.connect(path)) as con:
        con.row_factory = sqlite3.Row
        ingredients = con.execute(
            "SELECT ingredient_id,name,category,default_storage FROM ingredients WHERE active=1"
        ).fetchall()
        aliases = con.execute(
            "SELECT ingredient_id,alias_name FROM ingredient_aliases"
        ).fetchall()
    by_id = {
        int(row["ingredient_id"]): {
            "name": str(row["name"]),
            "category": str(row["category"] or ""),
            "default_storage": str(row["default_storage"] or ""),
        }
        for row in ingredients
    }
    for item in by_id.values():
        exact[_key(item["name"])] = item
    for row in aliases:
        item = by_id.get(int(row["ingredient_id"]))
        if item:
            exact[_key(row["alias_name"])] = item
    for name_key, item in exact.items():
        if len(name_key) >= 4:
            phrases.append((name_key, item))
    phrases.sort(key=lambda pair: len(pair[0]), reverse=True)
    return exact, tuple(phrases)


def _match_name(names: list[str], db_path: str | Path) -> tuple[dict | None, str, float]:
    exact, phrases = _catalog(*_catalog_version(db_path))
    keys = [
        _key(CAPTURE_NAME_ALIASES.get(_key(name), name))
        for name in names if _key(name)
    ]
    for name_key in keys:
        if name_key in exact:
            return exact[name_key], "matched", 1.0
    for name_key in keys:
        padded = f" {name_key} "
        for phrase, item in phrases:
            if f" {phrase} " in padded:
                return item, "matched", 0.94

    best: tuple[float, dict | None] = (0.0, None)
    for name_key in keys:
        for candidate, item in exact.items():
            score = SequenceMatcher(None, name_key, candidate).ratio()
            if score > best[0]:
                best = (score, item)
    if best[1] is not None and best[0] >= 0.78:
        return best[1], "needs_review", round(best[0], 2)
    return None, "unrecognized", 0.0


def _form_and_storage(candidate: dict, matched: dict | None) -> tuple[str, str]:
    raw_form = _clean(candidate.get("form"))
    raw_storage = _clean(candidate.get("storage") or candidate.get("storage_location"))
    evidence = _key(" ".join([
        raw_form,
        _clean(candidate.get("name")),
        _clean(candidate.get("category")),
        _clean(candidate.get("packaging")),
    ]))
    if raw_form:
        form = raw_form
    elif "frozen" in evidence:
        form = "Frozen"
    elif any(word in evidence for word in ("canned", "can", "tinned")):
        form = "Canned"
    elif any(word in evidence for word in ("dry", "dried", "pasta", "rice", "flour")):
        form = "Dry"
    else:
        form = "Fresh" if raw_storage in {"Fresh", "Fridge"} else "Shelf-stable"

    storage_names = {"pantry": "Pantry", "fridge": "Fridge", "freezer": "Freezer", "fresh": "Fresh"}
    if _key(raw_storage) in storage_names:
        storage = storage_names[_key(raw_storage)]
    elif "frozen" in _key(form):
        storage = "Freezer"
    elif "canned" in _key(form) or "shelf stable" in _key(form) or "dry" in _key(form):
        storage = "Pantry"
    else:
        default = storage_names.get(_key((matched or {}).get("default_storage")))
        storage = default or "Fresh"
    return form, storage


def _unit(value: Any, form: str) -> str:
    key = _key(value)
    aliases = {
        "items": "item", "cans": "can", "jars": "jar", "boxes": "box",
        "bags": "bag", "packages": "package", "pieces": "piece",
        "pounds": "lb", "pound": "lb", "lbs": "lb", "ounces": "oz",
        "ounce": "oz", "cups": "cup", "cartons": "carton",
        "bottles": "bottle", "bunches": "bunch", "loaves": "loaf",
    }
    allowed = {
        "item", "can", "jar", "box", "bag", "package", "egg", "piece",
        "lb", "oz", "cup", "carton", "bottle", "bunch", "loaf", "portion", "meal",
    }
    normalized = aliases.get(key, key)
    if normalized in allowed:
        return normalized
    if "canned" in _key(form):
        return "can"
    return "package"


def normalize_capture_candidates(
    candidates: list[dict],
    *,
    db_path: str | Path = DB_PATH,
    existing_inventory: list[dict] | None = None,
) -> list[dict]:
    """Turn uncertain recognition into canonical, deduplicated review rows."""
    if not isinstance(candidates, list):
        raise InventoryCaptureError("The recognition result was not an item list.")
    if len(candidates) > MAX_CAPTURE_ITEMS:
        raise InventoryCaptureError(f"Review no more than {MAX_CAPTURE_ITEMS} items at once.")

    existing: dict[tuple[str, str], dict] = {}
    for raw in existing_inventory or []:
        names = [_clean(raw.get("name"))]
        matched, _status, _confidence = _match_name(names, db_path)
        name = (matched or {}).get("name") or names[0]
        form, storage = _form_and_storage(raw, matched)
        existing[(_key(name), storage)] = {
            "quantity": _float(raw.get("quantity"), 0.0),
            "unit": _unit(raw.get("unit"), form),
        }

    drafts: dict[tuple[str, str], dict] = {}
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        source_name = _clean(raw.get("name") or raw.get("product_name"))
        if not source_name:
            continue
        alternates = [
            source_name,
            _clean(raw.get("generic_name")),
            *([_clean(value) for value in raw.get("candidate_names", [])]
              if isinstance(raw.get("candidate_names"), list) else []),
        ]
        matched, status, match_confidence = _match_name(alternates, db_path)
        canonical_name = (matched or {}).get("name") or source_name
        form, storage = _form_and_storage(raw, matched)
        confidence = min(1.0, max(0.0, _float(raw.get("confidence"), match_confidence)))
        unit = _unit(raw.get("unit"), form)
        quantity = _float(raw.get("quantity"), 1.0)
        key = (_key(canonical_name), storage)
        prior = drafts.get(key)
        if prior and prior["unit"] == unit:
            prior["quantity"] = round(prior["quantity"] + quantity, 2)
            prior["source_name"] = f'{prior["source_name"]}; {source_name}'
            prior["confidence"] = min(prior["confidence"], confidence)
            continue
        current = existing.get(key)
        drafts[key] = {
            "source_name": source_name,
            "name": canonical_name,
            "form": form,
            "storage_location": storage,
            "quantity": quantity,
            "unit": unit,
            "confidence": round(confidence, 2),
            "status": status,
            "already_on_hand": bool(current),
            "existing_quantity": current["quantity"] if current else 0,
            "existing_unit": current["unit"] if current else None,
            "barcode": _clean(raw.get("barcode")) or None,
        }
    return list(drafts.values())


def _json_request(url: str, *, headers: dict[str, str], body: bytes | None = None, timeout: float = 15.0) -> dict:
    request = Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise InventoryCaptureError(
            f"The recognition service is temporarily unavailable ({exc.code}). Try again or enter the item manually."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise InventoryCaptureError("The recognition service could not be reached. Try again or enter the item manually.") from exc


def resolve_barcode(
    barcode: str,
    *,
    db_path: str | Path = DB_PATH,
    existing_inventory: list[dict] | None = None,
) -> dict:
    clean_barcode = re.sub(r"\D", "", _clean(barcode))
    if not BARCODE_PATTERN.fullmatch(clean_barcode):
        raise InventoryCaptureError("Enter an 8- to 14-digit UPC or EAN barcode.")
    template = os.getenv("SNS_BARCODE_LOOKUP_URL", OPEN_FOOD_FACTS_URL)
    url = template.format(barcode=quote(clean_barcode))
    separator = "&" if "?" in url else "?"
    url += separator + "fields=code,product_name,product_name_en,generic_name,categories,quantity,packaging"
    payload = _json_request(url, headers={
        "Accept": "application/json",
        "User-Agent": os.getenv("SNS_BARCODE_USER_AGENT", "StockAndStir/1.0 (pantry capture)"),
    })
    product = payload.get("product") if isinstance(payload, dict) else None
    if payload.get("status") != 1 or not isinstance(product, dict):
        raise InventoryCaptureError("That barcode was not found. Enter the item manually instead.")
    name = _clean(product.get("product_name_en") or product.get("product_name") or product.get("generic_name"))
    if not name:
        raise InventoryCaptureError("That barcode has no usable product name. Enter the item manually instead.")
    category_names = [part.strip() for part in _clean(product.get("categories")).split(",") if part.strip()]
    draft = normalize_capture_candidates([{
        "name": name,
        "generic_name": product.get("generic_name"),
        "candidate_names": category_names,
        "category": product.get("categories"),
        "packaging": product.get("packaging"),
        "quantity": 1,
        "unit": "package",
        "confidence": 0.98,
        "barcode": clean_barcode,
    }], db_path=db_path, existing_inventory=existing_inventory)
    if not draft:
        raise InventoryCaptureError("That product could not be turned into a pantry item.")
    return {"source": "barcode", "barcode": clean_barcode, "items": draft}


PHOTO_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "maxItems": MAX_CAPTURE_ITEMS,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "maxLength": 120},
                    "form": {"type": "string", "maxLength": 60},
                    "storage": {"type": "string", "enum": ["Pantry", "Fridge", "Freezer", "Fresh"]},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string", "maxLength": 30},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["name", "form", "storage", "quantity", "unit", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def _validated_image_data_url(value: Any) -> str:
    data_url = _clean(value)
    if len(data_url) > (MAX_PHOTO_BYTES * 4 // 3) + 256:
        raise InventoryCaptureError("Choose a pantry photo smaller than 6 MB.")
    match = DATA_URL_PATTERN.fullmatch(data_url)
    if not match or match.group(1).lower() not in ALLOWED_IMAGE_TYPES:
        raise InventoryCaptureError("Choose a JPEG, PNG, or WebP pantry photo.")
    try:
        binary = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InventoryCaptureError("The pantry photo could not be read.") from exc
    if not binary or len(binary) > MAX_PHOTO_BYTES:
        raise InventoryCaptureError("Choose a pantry photo smaller than 6 MB.")
    return data_url


def _response_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise InventoryCaptureError("The photo service returned no item list. Try a clearer photo.")


def recognize_pantry_photo(
    image_data_url: str,
    *,
    db_path: str | Path = DB_PATH,
    existing_inventory: list[dict] | None = None,
) -> dict:
    image_data_url = _validated_image_data_url(image_data_url)
    api_key = _clean(os.getenv("OPENAI_API_KEY"))
    if not api_key:
        raise InventoryCaptureError("Pantry photo recognition is not configured yet. Add the item manually for now.")
    request_body = {
        "model": os.getenv("SNS_PANTRY_VISION_MODEL", "gpt-5-mini"),
        "store": False,
        "max_output_tokens": 2500,
        "input": [{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Identify only grocery or pantry items visibly present. Do not infer hidden items. "
                        "Use common ingredient names rather than marketing copy. Count visible packages when possible. "
                        "Mark uncertain readings with lower confidence. This is an inventory draft a cook will review."
                    ),
                },
                {"type": "input_image", "image_url": image_data_url, "detail": "low"},
            ],
        }],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "pantry_photo_inventory",
                "strict": True,
                "schema": PHOTO_SCHEMA,
            }
        },
    }
    payload = _json_request(
        os.getenv("SNS_OPENAI_RESPONSES_URL", OPENAI_RESPONSES_URL),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        body=json.dumps(request_body).encode("utf-8"),
        timeout=float(os.getenv("SNS_PANTRY_VISION_TIMEOUT", "35")),
    )
    try:
        raw_items = json.loads(_response_output_text(payload)).get("items")
    except (json.JSONDecodeError, AttributeError) as exc:
        raise InventoryCaptureError("The photo result could not be reviewed safely. Try a clearer photo.") from exc
    items = normalize_capture_candidates(
        raw_items, db_path=db_path, existing_inventory=existing_inventory
    )
    if not items:
        raise InventoryCaptureError("No pantry items were clear enough to review in that photo.")
    return {"source": "photo", "items": items, "photo_stored": False}
