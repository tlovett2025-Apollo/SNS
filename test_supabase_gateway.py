import unittest
from pathlib import Path
from io import BytesIO
from urllib.error import HTTPError, URLError
from unittest.mock import Mock, patch

from supabase_gateway import (
    SupabaseGateway,
    SupabaseGatewayError,
    apply_durable_kitchen,
)


class SupabaseGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = SupabaseGateway(
            base_url="https://example.supabase.co",
            publishable_key="sb_publishable_test",
        )

    def test_extracts_only_bearer_tokens(self):
        self.assertEqual(
            self.gateway.token_from_authorization("Bearer user.jwt.here"),
            "user.jwt.here",
        )
        self.assertEqual(self.gateway.token_from_authorization("Basic nope"), "")
        self.assertEqual(self.gateway.token_from_authorization(None), "")

    @patch("supabase_gateway.urlopen")
    def test_snapshot_uses_publishable_key_and_user_jwt(self, open_url):
        response = Mock()
        response.read.return_value = b'{"household_id":"house-1","inventory":[]}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        open_url.return_value = response

        result = self.gateway.kitchen_snapshot("signed-user-token")

        self.assertEqual(result["household_id"], "house-1")
        request = open_url.call_args.args[0]
        self.assertEqual(request.headers["Apikey"], "sb_publishable_test")
        self.assertEqual(
            request.headers["Authorization"],
            "Bearer signed-user-token",
        )
        self.assertNotIn("service_role", str(request))

    @patch("supabase_gateway.urlopen")
    def test_expired_login_has_a_human_message(self, open_url):
        open_url.side_effect = HTTPError(
            "https://example.supabase.co", 401, "Unauthorized", {}, BytesIO(b"{}")
        )
        with self.assertRaisesRegex(SupabaseGatewayError, "login expired"):
            self.gateway.kitchen_snapshot("expired")

    @patch("supabase_gateway.urlopen")
    def test_network_failure_does_not_leak_transport_details(self, open_url):
        open_url.side_effect = URLError("private network detail")
        with self.assertRaisesRegex(SupabaseGatewayError, "could not be reached"):
            self.gateway.kitchen_snapshot("token")

    @patch("supabase_gateway.urlopen")
    def test_recipe_report_uses_rls_protected_rpc(self, open_url):
        response = Mock()
        response.read.return_value = b'"report-uuid"'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        open_url.return_value = response

        result = self.gateway.submit_recipe_report("signed-user-token", {
            "p_candidate_id": "candidate-1",
            "p_recipe_snapshot": {"title": "Dinner"},
        })

        self.assertEqual(result, {"report_id": "report-uuid", "status": "received"})
        request = open_url.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/rest/v1/rpc/submit_recipe_report"))
        self.assertEqual(request.headers["Authorization"], "Bearer signed-user-token")

    def test_durable_inventory_replaces_browser_inventory_but_keeps_tonight(self):
        request = {
            "inventory": [{"name": "Wrong device food"}],
            "equipment": [],
            "servings": 7,
            "energy": "High",
            "selections": {"protein": "Chicken breast"},
            "meal_preferences": {"recent_meals": [{"title": "Soup"}]},
        }
        snapshot = {
            "household_id": "house-1",
            "inventory": [{"name": "White beans", "quantity": 2, "unit": "can"}],
            "equipment": [{"name": "Stovetop", "available": True}],
            "household_members": [{"name": "Taylor", "appetite": "standard"}],
            "preferences": [{
                "preference_type": "allergy",
                "target_value": "Peanuts",
                "severity": "never",
            }],
        }

        merged = apply_durable_kitchen(request, snapshot)

        self.assertEqual(merged["inventory"][0]["name"], "White beans")
        self.assertEqual(merged["servings"], 7)
        self.assertEqual(merged["energy"], "High")
        self.assertEqual(merged["selections"], request["selections"])
        self.assertEqual(merged["meal_preferences"]["excluded_items"], ["Peanuts"])
        self.assertEqual(merged["meal_preferences"]["recent_meals"], [{"title": "Soup"}])

    def test_migrations_enable_rls_and_keep_privileged_helpers_private(self):
        migration_dir = Path(__file__).parent / "supabase" / "migrations"
        sql = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(migration_dir.glob("*.sql"))
        ).lower()

        for table in (
            "profiles", "households", "household_members", "inventory_lots",
            "household_equipment", "household_preferences", "recipe_reports",
        ):
            self.assertIn(f"alter table public.{table} enable row level security", sql)
        self.assertIn("create or replace function private.is_household_member", sql)
        self.assertIn("revoke all on function public.create_new_user_kitchen()", sql)
        self.assertIn("grant execute on function public.my_kitchen_snapshot() to authenticated", sql)
        self.assertIn("grant execute on function public.submit_recipe_report", sql)
        self.assertIn("recipe_reports_issue_categories_check", sql)


if __name__ == "__main__":
    unittest.main()
