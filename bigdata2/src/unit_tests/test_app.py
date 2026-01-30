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
    def setUp(self, mock_load_dotenv, mock_db_class, mock_predictor_class):
        # Mock predictor
        self.mock_predictor = mock_predictor_class.return_value
        self.mock_predictor.predict.return_value = "Positive sentiment"

        # Mock database client
        self.mock_db = mock_db_class.return_value
        self.mock_db.connect.return_value = True
        self.mock_db.create_table.return_value = True
        self.mock_db.insert_data.return_value = True
        self.mock_db.get_data.return_value = [
            ("2025-09-05T12:00:00", "Hello world", "Positive sentiment")
        ]

        # Initialize API
        logger = Logger(SHOW_LOG)
        self.api_instance = SentimentAPI()
        self.client = TestClient(self.api_instance.app)

    def test_health_check(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "OK"})

    def test_predict_success(self):
        payload = {"message": "I love this!"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sentiment": "Positive sentiment"})
        self.api_instance.predictor.predict.assert_called_once_with("I love this!")
        self.api_instance.db_client.insert_data.assert_called_once()

    def test_predict_none_result(self):
        self.api_instance.predictor.predict.return_value = None
        payload = {"message": "Hello"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Prediction failed", response.text) 

    def test_predict_db_error(self):
        self.api_instance.db_client.insert_data.side_effect = Exception("DB insert fail")
        payload = {"message": "Test DB error"}
        response = self.client.post("/predict/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sentiment": "Positive sentiment"})

    def test_get_predictions_success(self):
        response = self.client.post("/predictions/", json={})
        self.assertEqual(response.status_code, 200)
        preds = response.json()["predictions"]
        self.assertEqual(len(preds), 1)
        self.assertEqual(preds[0]["message"], "Hello world")
        self.assertEqual(preds[0]["prediction"], "Positive sentiment")

    def test_get_predictions_db_error(self):
        self.api_instance.db_client.get_data.side_effect = Exception("DB fetch fail")
        response = self.client.post("/predictions/", json={})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to fetch predictions", response.text)


if __name__ == "__main__":
    unittest.main()
