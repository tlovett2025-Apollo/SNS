"""FastAPI transport for the Stock & Stir application service boundary.

The functions in :mod:`api_service` remain framework-independent. This
module translates HTTP/JSON requests, requires managed identity for
user-owned data, and maps domain errors to stable HTTP responses.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from api_service import (
    APIContractError,
    get_meal_builder_options,
    get_recipe,
    get_recipe_list,
    normalize_kitchen_snapshot,
    resolve_inventory,
)
from build_provenance import DEPLOYED_BUILD_PROVENANCE, public_build_provenance
from config import DB_PATH
from household_inventory import InventoryAccessError, InventoryError
from inventory_capture import (
    InventoryCaptureError,
    recognize_pantry_photo,
    resolve_barcode,
)
from inventory_contract import inventory_catalog
from recipe_reports import RecipeReportError, normalize_recipe_report
from supabase_gateway import (
    SupabaseGateway,
    SupabaseGatewayError,
    apply_durable_kitchen,
)


_PUBLIC_FRONTEND_ORIGINS = (
    "https://sns-web-um3d.onrender.com",
    "https://stockandstir.co",
    "https://www.stockandstir.co",
    "https://getstockandstir.co",
    "https://www.getstockandstir.co",
)


def _cors_origins() -> list[str]:
    configured = os.getenv("SNS_CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    for origin in _PUBLIC_FRONTEND_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    return origins


app = FastAPI(
    title="Stock & Stir API",
    version="1.0.0",
    description="Tester API for My Kitchen and the current trained meal planner.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Build identity is constant for the lifetime of a deployed process. Compute
# it once so readiness probes never repeat filesystem and Git inspection.
_BUILD_PROVENANCE = DEPLOYED_BUILD_PROVENANCE
_SUPABASE = SupabaseGateway()


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InventoryAccessError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, SupabaseGatewayError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, (APIContractError, InventoryError, InventoryCaptureError, RecipeReportError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="The Stock & Stir API could not complete the request.")


@app.get("/")
def api_information() -> dict:
    return {
        "service": "Stock & Stir API",
        "api_version": "1.0",
        "status": "available",
        "docs": "/docs",
        "build": public_build_provenance(_BUILD_PROVENANCE),
    }


@app.head("/", status_code=200)
def api_head() -> Response:
    """Allow Render's initial port probe to confirm the API is responsive."""
    return Response(status_code=200)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "sns-api",
        "build_id": _BUILD_PROVENANCE["build_id"],
    }


@app.head("/health", status_code=200)
def health_head() -> Response:
    """Return a body-free success response for infrastructure health probes."""
    return Response(status_code=200)


def _access_token(authorization: str | None) -> str:
    return _SUPABASE.token_from_authorization(authorization)


def _durable_payload(payload: dict, authorization: str | None) -> dict:
    token = _access_token(authorization)
    if not token:
        return payload
    snapshot = _SUPABASE.kitchen_snapshot(token)
    if isinstance(payload.get("kitchen"), dict):
        hydrated = dict(payload)
        hydrated["kitchen"] = apply_durable_kitchen(payload["kitchen"], snapshot)
        return hydrated
    return apply_durable_kitchen(payload, snapshot)


def _canonical_sync_payload(payload: dict) -> dict:
    """Resolve known aliases before they become the household source of truth."""
    normalized = normalize_kitchen_snapshot(payload)
    resolved, _pending = resolve_inventory(
        normalized, DB_PATH, strict_contract=True
    )
    canonical = {
        str(item.source.get("_requested_name") or item.source.get("name") or "").strip().lower(): item
        for item in resolved
    }
    inventory = []
    for item in normalized["inventory_lots"]:
        resolved_item = canonical.get(str(item.get("name") or "").strip().lower())
        source = resolved_item.source if resolved_item else item
        inventory.append({
            "name": resolved_item.name if resolved_item else item.get("name"),
            "form": resolved_item.form_name if resolved_item else item.get("form"),
            "storage": source.get("storage_location"),
            "quantity": source.get("quantity"),
            "unit": source.get("unit"),
            "origin": source.get("origin"),
            "opened_at": source.get("opened_at"),
            "refrigerated_after_opening": source.get("refrigerated_after_opening"),
            "package_weight_oz": source.get("package_weight_oz"),
            "expiration_date": source.get("expiration_date"),
        })
    canonical_payload = dict(payload)
    canonical_payload["inventory"] = inventory
    return canonical_payload


@app.get("/api/MyKitchen")
def get_kitchen_endpoint(
    authorization: str | None = Header(default=None),
    include_contracts: bool = False,
) -> dict:
    """Return the signed-in user's RLS-protected household kitchen."""
    try:
        snapshot = _SUPABASE.kitchen_snapshot(_access_token(authorization))
        if include_contracts:
            snapshot["inventory_contracts"] = inventory_catalog(DB_PATH)
        return snapshot
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/SaveMyKitchen")
def save_kitchen_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    """Save only the authenticated user's RLS-protected household."""
    try:
        token = _access_token(authorization)
        if not token:
            raise SupabaseGatewayError("Log in to save your shared kitchen.")
        response = _SUPABASE.sync_kitchen(
            token,
            _canonical_sync_payload(payload),
            source_type=payload.get("sync_source_type"),
            source_fingerprint=payload.get("sync_source_fingerprint"),
        )
        response["storage_mode"] = "supabase_household"
        return response
    except Exception as exc:
        raise _domain_error(exc) from exc


def _signed_in_kitchen(authorization: str | None) -> dict:
    """Validate the user JWT and return only that user's RLS-protected kitchen."""
    token = _access_token(authorization)
    if not token:
        raise SupabaseGatewayError("Log in to scan items into your shared kitchen.")
    return _SUPABASE.kitchen_snapshot(token)


def _snapshot_inventory(snapshot: dict) -> list[dict]:
    values = snapshot.get("inventory") or snapshot.get("foods") or []
    return values if isinstance(values, list) else []


@app.post("/api/ResolveBarcode")
def resolve_barcode_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    """Return a canonical review draft for a UPC/EAN; never save it."""
    try:
        snapshot = _signed_in_kitchen(authorization)
        return resolve_barcode(
            payload.get("barcode"),
            db_path=DB_PATH,
            existing_inventory=_snapshot_inventory(snapshot),
        )
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/RecognizePantryPhoto")
def recognize_pantry_photo_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    """Return a transient pantry-photo review draft; never store image bytes."""
    try:
        snapshot = _signed_in_kitchen(authorization)
        return recognize_pantry_photo(
            payload.get("image_data_url"),
            db_path=DB_PATH,
            existing_inventory=_snapshot_inventory(snapshot),
        )
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/GetRecipeList")
def recipe_list_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        return get_recipe_list(_durable_payload(payload, authorization), db_path=DB_PATH)
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/GetMealBuilderOptions")
def meal_builder_options_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        return get_meal_builder_options(_durable_payload(payload, authorization), db_path=DB_PATH)
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/GetRecipe")
def recipe_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        return get_recipe(_durable_payload(payload, authorization), db_path=DB_PATH)
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/ReportRecipe")
def report_recipe_endpoint(
    payload: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    """Store a signed-in cook's recipe snapshot for human review."""
    try:
        token = _access_token(authorization)
        if not token:
            raise SupabaseGatewayError("Log in to report a recipe.")
        return _SUPABASE.submit_recipe_report(token, normalize_recipe_report(payload))
    except Exception as exc:
        raise _domain_error(exc) from exc
