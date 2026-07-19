import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_http import _cors_origins, app
from test_api_service import kitchen_payload


class APIHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["service"], "sns-api")
        self.assertRegex(response.json()["build_id"], r"^SNS-[0-9a-f]{12}$")

    def test_head_probes_are_accepted(self):
        self.assertEqual(self.client.head("/").status_code, 200)
        self.assertEqual(self.client.head("/health").status_code, 200)

    def test_service_information_points_to_openapi_docs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["docs"], "/docs")
        self.assertNotIn("files", response.json()["build"])
        self.assertNotIn(".venv", response.text)
        self.assertLess(len(response.content), 2048)

    def test_recipe_list_endpoint_exposes_current_contract(self):
        response = self.client.post("/api/GetRecipeList", json=kitchen_payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "1.0")
        self.assertTrue(body["candidates"])

    def test_signed_in_kitchen_is_loaded_from_supabase(self):
        snapshot = {
            "household_id": "house-1",
            "inventory": kitchen_payload()["inventory"],
            "equipment": kitchen_payload().get("equipment", [{"name": "Stovetop"}]),
            "household_members": [],
            "preferences": [],
        }
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.kitchen_snapshot.return_value = snapshot
            response = self.client.get(
                "/api/MyKitchen",
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["household_id"], "house-1")

    def test_my_kitchen_can_request_server_owned_inventory_contracts(self):
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.kitchen_snapshot.return_value = {
                "household_id": "house-1", "inventory": [], "equipment": []
            }
            response = self.client.get(
                "/api/MyKitchen?include_contracts=true",
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        contracts = {item["name"]: item for item in response.json()["inventory_contracts"]}
        self.assertIn("Chicken breast", contracts)
        self.assertIn("lb", contracts["Chicken breast"]["allowed_units"])
        self.assertEqual(contracts["Chicken broth"]["contract_version"], "inventory-2.0")

    def test_shared_kitchen_save_canonicalizes_alias_form_and_legacy_unit(self):
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.sync_kitchen.return_value = {"household_id": "house-1"}
            response = self.client.post(
                "/api/SaveMyKitchen",
                json={
                    "inventory": [{
                        "name": "ribeye", "form": "Refrigerated",
                        "quantity": 2, "unit": "items", "storage": "Fridge",
                    }]
                },
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        saved = gateway.sync_kitchen.call_args.args[1]["inventory"][0]
        self.assertEqual(saved["name"], "Ribeye steak")
        self.assertEqual(saved["unit"], "piece")

    def test_shared_kitchen_save_coalesces_aliases_before_supabase(self):
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.sync_kitchen.return_value = {"household_id": "house-1"}
            response = self.client.post(
                "/api/SaveMyKitchen",
                json={"inventory": [
                    {
                        "name": "ribeye", "form": "Refrigerated",
                        "quantity": 1, "unit": "items", "storage": "Fridge",
                    },
                    {
                        "name": "Ribeye steak", "form": "Refrigerated",
                        "quantity": 2, "unit": "piece", "storage": "Fridge",
                    },
                ]},
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        saved = gateway.sync_kitchen.call_args.args[1]["inventory"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Ribeye steak")
        self.assertEqual(saved[0]["quantity"], 3)
        self.assertRegex(saved[0]["client_item_id"], r"^[0-9a-f]{32}$")

    def test_shared_kitchen_save_rejects_an_impossible_unit(self):
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            response = self.client.post(
                "/api/SaveMyKitchen",
                json={
                    "inventory": [{
                        "name": "Chicken breast", "form": "Fresh Raw",
                        "quantity": 1, "unit": "jar", "storage": "Fridge",
                    }]
                },
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be stored", response.json()["detail"])

    def test_anonymous_kitchen_save_is_rejected(self):
        response = self.client.post("/api/SaveMyKitchen", json=kitchen_payload())

        self.assertEqual(response.status_code, 401)
        self.assertIn("Log in", response.json()["detail"])

    def test_signed_in_recipe_request_uses_the_durable_inventory(self):
        kitchen = kitchen_payload()
        snapshot = {
            "household_id": "house-1",
            "inventory": kitchen["inventory"],
            "equipment": kitchen.get("equipment", [{"name": "Stovetop"}]),
            "household_members": [],
            "preferences": [],
        }
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.kitchen_snapshot.return_value = snapshot
            response = self.client.post(
                "/api/GetRecipeList",
                json={**kitchen, "inventory": [{"name": "Stale browser food", "quantity": 1}]},
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["candidates"])
        gateway.kitchen_snapshot.assert_called_once_with("user-token")

    def test_meal_builder_options_endpoint_marks_owned_choices(self):
        response = self.client.post("/api/GetMealBuilderOptions", json=kitchen_payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["proteins"])
        self.assertTrue(next(item for item in body["proteins"] if item["name"] == "Chicken breast")["owned"])
        self.assertFalse(next(item for item in body["serving_temperatures"] if item["id"] == "cold")["available"])
        self.assertEqual(
            {item["id"] for item in body["meal_structures"]},
            {"integrated", "composed_plate", "layered_bowl"},
        )

    def test_recipe_round_trip_over_http(self):
        kitchen = kitchen_payload()
        choices = self.client.post("/api/GetRecipeList", json=kitchen).json()
        candidate_id = choices["candidates"][0]["candidate_id"]
        response = self.client.post(
            "/api/GetRecipe",
            json={"candidate_id": candidate_id, "kitchen": kitchen},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidate_id"], candidate_id)
        self.assertNotIn("files", response.json()["build_provenance"])
        self.assertNotIn(".venv", response.text)

    def test_contract_errors_are_http_400(self):
        response = self.client.post(
            "/api/GetRecipe",
            json={"candidate_id": "not-real", "kitchen": kitchen_payload()},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown or unavailable candidate_id", response.json()["detail"])

    def test_signed_in_cook_can_report_the_exact_recipe(self):
        recipe = {
            "candidate_id": "candidate-1",
            "title": "Dinner",
            "ingredients": ["Chicken breast"],
            "steps": ["Cook safely."],
            "build_provenance": {"build_id": "SNS-test", "git": {"commit": "abc"}},
        }
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.submit_recipe_report.return_value = {
                "report_id": "report-1", "status": "received"
            }
            response = self.client.post(
                "/api/ReportRecipe",
                json={
                    "recipe_snapshot": recipe,
                    "rendered_recipe_text": "The full visible recipe",
                    "issue_categories": ["weird_instructions"],
                },
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "received")
        report = gateway.submit_recipe_report.call_args.args[1]
        self.assertEqual(report["p_candidate_id"], "candidate-1")
        self.assertEqual(report["p_build_id"], "SNS-test")
        self.assertEqual(report["p_issue_categories"], ["weird_instructions"])
        self.assertEqual(report["p_report_outcome"], "NG")

    def test_signed_in_cook_can_record_a_recipe_as_ok(self):
        recipe = {
            "candidate_id": "candidate-ok",
            "title": "Dinner",
            "ingredients": ["Chicken breast"],
            "steps": ["Cook safely."],
        }
        with patch("api_http._SUPABASE") as gateway:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.submit_recipe_report.return_value = {
                "report_id": "report-ok", "status": "received"
            }
            response = self.client.post(
                "/api/ReportRecipe",
                json={"recipe_snapshot": recipe, "report_outcome": "OK"},
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        report = gateway.submit_recipe_report.call_args.args[1]
        self.assertEqual(report["p_report_outcome"], "OK")
        self.assertEqual(report["p_issue_categories"], ["recipe_ok"])

    def test_anonymous_recipe_report_is_not_stored(self):
        response = self.client.post(
            "/api/ReportRecipe",
            json={"recipe_snapshot": {"candidate_id": "candidate-1"}},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Log in", response.json()["detail"])

    def test_anonymous_inventory_capture_is_rejected_before_external_lookup(self):
        barcode = self.client.post("/api/ResolveBarcode", json={"barcode": "000240001628"})
        photo = self.client.post(
            "/api/RecognizePantryPhoto",
            json={"image_data_url": "data:image/jpeg;base64,c21hbGw="},
        )

        self.assertEqual(barcode.status_code, 401)
        self.assertEqual(photo.status_code, 401)
        self.assertIn("Log in", barcode.json()["detail"])

    def test_signed_in_barcode_capture_uses_rls_kitchen_and_returns_only_a_draft(self):
        with patch("api_http._SUPABASE") as gateway, patch("api_http.resolve_barcode") as resolver:
            gateway.token_from_authorization.return_value = "user-token"
            gateway.kitchen_snapshot.return_value = {
                "inventory": [{"name": "Green beans", "quantity": 1, "unit": "can"}]
            }
            resolver.return_value = {"source": "barcode", "items": [{"name": "Green beans"}]}
            response = self.client.post(
                "/api/ResolveBarcode",
                json={"barcode": "000240001628"},
                headers={"Authorization": "Bearer user-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("saved", response.json())
        gateway.kitchen_snapshot.assert_called_once_with("user-token")
        self.assertEqual(
            resolver.call_args.kwargs["existing_inventory"][0]["name"], "Green beans"
        )

    def test_default_cors_preflight_allows_tester_site(self):
        origin = "https://getstockandstir.co"
        response = self.client.options(
            "/api/GetRecipeList",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Local development defaults to the wildcard. Render supplies the
        # explicit production allowlist, in which case Starlette echoes the
        # requesting allowed origin. Both are valid configurations; the test
        # must not require the less restrictive local default in production.
        configured_origins = _cors_origins()
        expected_origin = "*" if "*" in configured_origins else origin
        self.assertIn(origin, configured_origins)
        self.assertEqual(
            response.headers["access-control-allow-origin"], expected_origin
        )

    def test_cors_preflight_allows_the_user_authorization_header(self):
        response = self.client.options(
            "/api/MyKitchen",
            headers={
                "Origin": "https://stockandstir.co",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Authorization", response.headers["access-control-allow-headers"])

    def test_configured_cors_origins_are_parsed_for_fastapi(self):
        configured = "https://sns-web-um3d.onrender.com"

        with patch.dict("os.environ", {"SNS_CORS_ORIGINS": configured}):
            origins = _cors_origins()

        self.assertIn("https://sns-web-um3d.onrender.com", origins)
        self.assertIn("https://stockandstir.co", origins)
        self.assertIn("https://www.stockandstir.co", origins)

    def test_render_blueprint_allows_the_live_custom_domain(self):
        blueprint = (Path(__file__).parent / "render.yaml").read_text(encoding="utf-8")

        self.assertIn("https://stockandstir.co", blueprint)


if __name__ == "__main__":
    unittest.main()
