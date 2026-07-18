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

    def test_default_cors_preflight_allows_tester_site(self):
        response = self.client.options(
            "/api/GetRecipeList",
            headers={
                "Origin": "https://getstockandstir.co",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")

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
