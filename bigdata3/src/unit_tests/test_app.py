import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

sys.path.insert(1, os.path.join(os.getcwd(), "src"))
from app import SentimentAPI
from src.logger import Logger

SHOW_LOG = False


class TestSentimentAPI(unittest.TestCase):
    @patch("app.Predictor")
    @patch("app.ClickHouseClient")
    @patch("app.load_dotenv")
    @patch("app.get_vault_client")
    def setUp(self, mock_vault_client, mock_load_dotenv, mock_db_class, mock_predictor_class):
        # Mock predictor
        self.mock_predictor = mock_predictor_class.return_value
        self.mock_predictor.predict.return_value = "Positive sentiment"

        # Mock DB client
        self.mock_db = mock_db_class.return_value
        self.mock_db.connect.return_value = True
        self.mock_db.create_table.return_value = True
        self.mock_db.insert_data.return_value = True
        self.mock_db.get_data.return_value = [
            ("2025-09-05T12:00:00", "Hello world", "Positive sentiment")
        ]

        # Mock Vault client
        self.mock_vault = mock_vault_client.return_value
        self.mock_vault.is_authenticated.return_value = True
        self.mock_vault.get_connection.return_value = ("host", 8123, "user", "pass")
        self.mock_vault.list_mounted_secrets_engines.return_value = {"secret/": {}}

        # Initialize API
        logger = Logger(SHOW_LOG)
        self.api_instance = SentimentAPI()
        self.client = TestClient(self.api_instance.app)

    def test_readiness_check(self):
        response = self.client.get("/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "OK"})

    def test_health_check(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("model_loaded", data)
        self.assertIn("database_connected", data)
        self.assertIn("vault_connected", data)

    def test_predict_success(self):
        payload = {"message": "I love this!"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sentiment": "Positive sentiment"})
        self.api_instance.predictor.predict.assert_called_once_with("I love this!")

    def test_predict_none_result(self):
        self.api_instance.predictor.predict.return_value = None
        payload = {"message": "Hello"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Prediction failed", response.text)

    def test_predict_db_error(self):
        self.api_instance.db_client.insert_data.side_effect = Exception("DB insert fail")
        payload = {"message": "DB test"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 200)  # still returns prediction

    def test_get_predictions_success(self):
        response = self.client.post("/predictions/", json={})
        self.assertEqual(response.status_code, 200)
        preds = response.json()["predictions"]
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0]["message"], "Hello world")

    def test_get_predictions_db_error(self):
        self.api_instance.db_client.get_data.side_effect = Exception("DB fail")
        response = self.client.post("/predictions/", json={})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to fetch predictions", response.text)

    def test_vault_status_success(self):
        response = self.client.get("/vault-status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["connected"])
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["secrets_engine"], "Available")

    def test_vault_status_not_connected(self):
        self.api_instance.vault_connected = False
        response = self.client.get("/vault-status/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to connect to Vault", response.text)

    def test_vault_status_exception(self):
        self.api_instance.vault_client.is_authenticated.side_effect = Exception("Vault fail")
        response = self.client.get("/vault-status/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to get Vault status", response.text)


if __name__ == "__main__":
    unittest.main()
