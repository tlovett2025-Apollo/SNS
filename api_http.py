"""FastAPI transport for the Stock & Stir application service boundary.

The functions in :mod:`api_service` remain framework-independent.  This
module only translates HTTP/JSON requests, establishes the explicit shared
tester household used before managed authentication exists, and maps domain
errors to stable HTTP responses.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api_service import APIContractError, get_recipe, get_recipe_list, save_my_kitchen
from config import DB_PATH
from household_inventory import (
    InventoryAccessError,
    InventoryError,
    bootstrap_local_household,
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
    allow_headers=["Content-Type"],
)


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InventoryAccessError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (APIContractError, InventoryError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="The Stock & Stir API could not complete the request.")


@app.get("/")
def api_information() -> dict:
    return {
        "service": "Stock & Stir API",
        "api_version": "1.0",
        "status": "available",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "sns-api"}


@app.post("/api/SaveMyKitchen")
def save_kitchen_endpoint(payload: dict) -> dict:
    """Save to the shared pre-authentication tester household.

    Recipe requests carry their own kitchen snapshot, so testers do not rely
    on this shared saved state to generate or open a meal.  Managed identity
    will replace this bootstrap before production billing is enabled.
    """
    try:
        user_id, household_id = bootstrap_local_household(DB_PATH)
        response = save_my_kitchen(
            payload,
            household_id=household_id,
            acting_user_id=user_id,
            db_path=DB_PATH,
        )
        response["storage_mode"] = "shared_tester_household"
        return response
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/GetRecipeList")
def recipe_list_endpoint(payload: dict) -> dict:
    try:
        return get_recipe_list(payload, db_path=DB_PATH)
    except Exception as exc:
        raise _domain_error(exc) from exc


@app.post("/api/GetRecipe")
def recipe_endpoint(payload: dict) -> dict:
    try:
        return get_recipe(payload, db_path=DB_PATH)
    except Exception as exc:
        raise _domain_error(exc) from exc
