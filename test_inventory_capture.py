import base64
import json
import unittest
from unittest.mock import patch

from config import DB_PATH
from inventory_capture import (
    InventoryCaptureError,
    normalize_capture_candidates,
    recognize_pantry_photo,
    resolve_barcode,
)


class _JSONResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class InventoryCaptureTests(unittest.TestCase):
    def test_capture_aliases_are_canonical_and_duplicate_rows_are_combined(self):
        items = normalize_capture_candidates([
            {"name": "corn starch", "form": "Shelf-stable", "storage": "Pantry", "quantity": 1, "unit": "box"},
            {"name": "Cornstarch", "form": "Shelf-stable", "storage": "Pantry", "quantity": 2, "unit": "box"},
        ], db_path=DB_PATH)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Cornstarch")
        self.assertEqual(items[0]["quantity"], 3)
        self.assertEqual(items[0]["status"], "matched")

    def test_existing_canonical_item_is_flagged_without_creating_a_second_identity(self):
        items = normalize_capture_candidates(
            [{"name": "ribeye", "form": "Fresh Raw", "storage": "Fridge", "quantity": 2, "unit": "piece"}],
            db_path=DB_PATH,
            existing_inventory=[{"name": "Ribeye steak", "form": "Fresh Raw", "storage": "Fridge", "quantity": 1, "unit": "piece"}],
        )

        self.assertEqual(items[0]["name"], "Ribeye steak")
        self.assertTrue(items[0]["already_on_hand"])
        self.assertEqual(items[0]["existing_quantity"], 1)

    @patch("inventory_capture.urlopen")
    def test_barcode_lookup_uses_product_evidence_and_returns_review_draft(self, mocked_open):
        mocked_open.return_value = _JSONResponse({
            "status": 1,
            "product": {
                "product_name": "Del Monte Cut Green Beans",
                "generic_name": "Green beans",
                "categories": "Green beans, Canned vegetables",
                "packaging": "Can",
            },
        })

        result = resolve_barcode("000240001628", db_path=DB_PATH)

        self.assertEqual(result["source"], "barcode")
        self.assertEqual(result["items"][0]["name"], "Green beans")
        self.assertEqual(result["items"][0]["form"], "Canned")
        self.assertEqual(result["items"][0]["storage_location"], "Pantry")
        self.assertEqual(result["items"][0]["unit"], "can")
        self.assertNotIn("saved", result)

    def test_barcode_validation_rejects_non_gtin_input_before_lookup(self):
        with self.assertRaisesRegex(InventoryCaptureError, "8- to 14-digit"):
            resolve_barcode("not-a-barcode", db_path=DB_PATH)

    @patch("inventory_capture.urlopen")
    def test_photo_recognition_is_structured_transient_and_never_stores_the_photo(self, mocked_open):
        mocked_open.return_value = _JSONResponse({
            "output_text": json.dumps({
                "items": [{
                    "name": "Canned tuna", "form": "Canned", "storage": "Pantry",
                    "quantity": 2, "unit": "can", "confidence": 0.96,
                }]
            })
        })
        image = "data:image/jpeg;base64," + base64.b64encode(b"small-test-image").decode("ascii")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "SNS_PANTRY_VISION_MODEL": "test-vision"}):
            result = recognize_pantry_photo(image, db_path=DB_PATH)

        request = mocked_open.call_args.args[0]
        request_json = json.loads(request.data)
        self.assertFalse(request_json["store"])
        self.assertEqual(request_json["model"], "test-vision")
        self.assertEqual(request_json["text"]["format"]["type"], "json_schema")
        self.assertIn("input_image", {item["type"] for item in request_json["input"][0]["content"]})
        self.assertEqual(result["items"][0]["name"], "Canned tuna")
        self.assertFalse(result["photo_stored"])
        self.assertNotIn("image_data_url", result)

    def test_photo_requires_server_side_api_configuration(self):
        image = "data:image/png;base64," + base64.b64encode(b"small-test-image").decode("ascii")
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(InventoryCaptureError, "not configured"):
                recognize_pantry_photo(image, db_path=DB_PATH)

    def test_photo_size_and_type_are_bounded(self):
        with self.assertRaisesRegex(InventoryCaptureError, "JPEG, PNG, or WebP"):
            recognize_pantry_photo("data:image/gif;base64,R0lGODlh", db_path=DB_PATH)


if __name__ == "__main__":
    unittest.main()
