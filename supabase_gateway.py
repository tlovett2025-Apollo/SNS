"""User-scoped Supabase access for Stock & Stir's durable kitchen data.

The gateway deliberately uses the browser-safe publishable key together with
the signed-in user's JWT. Supabase therefore applies the same RLS policies to
server requests that it applies to browser requests; no service-role bypass is
needed for normal kitchen operations.
"""

from __future__ import annotations

import os
import json
import hashlib
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_SUPABASE_URL = "https://pbsrcqscssumywjhgino.supabase.co"
DEFAULT_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_nlQsaKbHb5TyJGqjB0vbrg_MoePw2ye"


class SupabaseGatewayError(RuntimeError):
    """Raised when identity or durable kitchen access fails."""


def _inventory_identity(item: dict[str, Any]) -> tuple[str, ...]:
    """Return the durable identity for one editable kitchen row."""
    return tuple(
        str(value if value is not None else "").strip().lower()
        for value in (
            item.get("name"),
            item.get("storage", item.get("storage_location")),
            item.get("form", item.get("form_name")),
            item.get("unit"),
            item.get("expiration_date"),
            item.get("opened_at"),
            item.get("refrigerated_after_opening"),
            item.get("package_weight_oz"),
        )
    )


def coalesce_inventory_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine canonical duplicate rows and assign stable client identities.

    Alias resolution can turn two browser rows into the same canonical food.
    My Kitchen currently stores ingredient state rather than a package-lot
    ledger, so equal states are one row whose quantities are combined.
    """
    merged: dict[tuple[str, ...], dict[str, Any]] = {}
    for raw in items:
        item = dict(raw)
        key = _inventory_identity(item)
        if not key[0]:
            continue
        try:
            quantity = float(item.get("quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            continue
        if key in merged:
            total = float(merged[key].get("quantity") or 0) + quantity
            merged[key]["quantity"] = int(total) if total.is_integer() else total
            continue
        item["quantity"] = int(quantity) if quantity.is_integer() else quantity
        item["client_item_id"] = hashlib.sha256(
            "|".join(key).encode("utf-8")
        ).hexdigest()[:32]
        merged[key] = item
    return list(merged.values())


@dataclass(frozen=True)
class SupabaseGateway:
    base_url: str = os.getenv("SNS_SUPABASE_URL", DEFAULT_SUPABASE_URL)
    publishable_key: str = os.getenv(
        "SNS_SUPABASE_PUBLISHABLE_KEY", DEFAULT_SUPABASE_PUBLISHABLE_KEY
    )
    timeout_seconds: float = 12.0

    def _headers(self, access_token: str) -> dict[str, str]:
        if not access_token:
            raise SupabaseGatewayError("Log in to use your shared kitchen.")
        return {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def token_from_authorization(authorization: str | None) -> str:
        scheme, _, token = str(authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return ""
        return token.strip()

    def _post_rpc(self, name: str, access_token: str, payload: dict[str, Any]) -> Any:
        request = Request(
            f"{self.base_url}/rest/v1/rpc/{name}",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(access_token),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise SupabaseGatewayError("Your login expired. Please log in again.") from exc
            try:
                body = json.loads(exc.read().decode("utf-8"))
                detail = body.get("message") or body.get("hint")
            except (ValueError, AttributeError, UnicodeDecodeError):
                detail = ""
            raise SupabaseGatewayError(detail or "The shared kitchen could not be updated.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SupabaseGatewayError("The shared kitchen could not be reached.") from exc

    def kitchen_snapshot(self, access_token: str) -> dict[str, Any]:
        value = self._post_rpc("my_kitchen_snapshot", access_token, {})
        if not isinstance(value, dict):
            raise SupabaseGatewayError("The shared kitchen returned an invalid snapshot.")
        return value

    def sync_kitchen(
        self,
        access_token: str,
        snapshot: dict[str, Any],
        *,
        source_type: str | None = None,
        source_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        value = self._post_rpc(
            "sync_my_kitchen",
            access_token,
            {
                "p_snapshot": snapshot,
                "p_source_type": source_type,
                "p_source_fingerprint": source_fingerprint,
            },
        )
        if not isinstance(value, dict):
            raise SupabaseGatewayError("The shared kitchen returned an invalid snapshot.")
        return value

    def submit_recipe_report(
        self, access_token: str, report: dict[str, Any]
    ) -> dict[str, Any]:
        report_id = self._post_rpc("submit_recipe_report", access_token, report)
        if not isinstance(report_id, str) or not report_id:
            raise SupabaseGatewayError("The recipe report returned an invalid response.")
        return {"report_id": report_id, "status": "received"}


def apply_durable_kitchen(payload: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Replace user-owned kitchen fields while preserving tonight's request."""
    merged = dict(payload)
    merged["household_id"] = snapshot.get("household_id")
    merged["inventory"] = list(snapshot.get("inventory") or snapshot.get("foods") or [])
    merged["equipment"] = [
        {"name": item.get("name"), "available": item.get("available", item.get("active", True))}
        for item in list(snapshot.get("equipment") or [])
        if item.get("name") and item.get("available", item.get("active", True))
    ]
    if not merged.get("servings"):
        merged["servings"] = snapshot.get("servings", 4)
    if not merged.get("energy"):
        merged["energy"] = snapshot.get("energy", "Low")
    if not merged.get("effort"):
        merged["effort"] = merged.get("energy", snapshot.get("effort", "Low"))

    meal_preferences = dict(merged.get("meal_preferences") or {})
    meal_preferences["household_members"] = list(snapshot.get("household_members") or [])
    stored_preferences = list(snapshot.get("preferences") or [])
    exclusions = [
        item.get("target_value")
        for item in stored_preferences
        if item.get("target_value")
        and item.get("preference_type") in {
            "allergy", "medical_exclusion", "religious_exclusion", "exclusion"
        }
        and item.get("severity") in {"never", "avoid"}
    ]
    if exclusions:
        meal_preferences["excluded_items"] = exclusions
    meal_preferences["stored_preferences"] = stored_preferences
    merged["meal_preferences"] = meal_preferences
    return merged
