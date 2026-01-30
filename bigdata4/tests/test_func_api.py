import configparser
import sys
import time
import json
import os
import httpx
import pytest
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.database import ClickHouseClient
from src.logger import Logger
from dotenv import load_dotenv
load_dotenv()

SHOW_LOG = True
logger = Logger(SHOW_LOG)
log = logger.get_logger(__name__)


TESTS_DIR = os.path.join(os.path.dirname(__file__), "test_data")

log.info(f"{TESTS_DIR}")
SERVER_URL = "http://localhost:8000"
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", None)

if CLICKHOUSE_HOST == "clickhouse":
    CLICKHOUSE_HOST = "localhost"


# Ensure API server is running before tests
@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    log.info("Waiting for API to start...")
    timeout = 15
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"{SERVER_URL}/ready/")
            if response.status_code == 200:
                log.info("API is up and running.")
                return
        except httpx.RequestError:
            pass
        time.sleep(1)
    log.error("API did not start in time")
    raise RuntimeError("API did not start in time")

@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_URL}/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["database_connected"], bool)
        assert isinstance(data["vault_connected"], bool)

@pytest.mark.asyncio
async def test_vault_status():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_URL}/vault-status/")
        if response.status_code == 200:
            data = response.json()
            assert "connected" in data
            assert "authenticated" in data
            assert "secrets_engine" in data
            log.info(f"Vault status: {data}")
        else:
            assert response.status_code == 500
            log.warning("Vault not available, got 500 as expected")

@pytest.fixture(scope="session")
def db_client():
    log.info("Connecting to ClickHouse...")
    client = ClickHouseClient()
    client.get_db_cred(host=CLICKHOUSE_HOST)
    client.connect()
    log.info("Connected to ClickHouse successfully.")
    yield client
    client.close()
    log.info("ClickHouse connection closed.")


# ============================
# Functional Test
# ============================
@pytest.mark.asyncio
async def test_predictions_saved_in_db(db_client):
    log.info("Starting functional test for predictions...")

    test_files = [f for f in os.listdir(TESTS_DIR) if f.endswith(".json")]
    assert test_files, "No test files found in test_data directory."

    async with httpx.AsyncClient() as client:
        for file_name in test_files:
            file_path = os.path.join(TESTS_DIR, file_name)
            with open(file_path, "r") as f:
                test_case = json.load(f)

            X_dict = test_case["X"][0]  # {id: text}
            y_dict = test_case["y"][0]  # {id: label}

            # Collect predictions for accuracy calculation
            y_true = []
            y_pred_int = []

            for idx, message in X_dict.items():
                expected_label = y_dict.get(idx)
                log.info(f"Sending message: '{message}' from {file_name} (id={idx})")

                response = await client.post(f"{SERVER_URL}/predict/", json={"message": message})
                log.info(f"Response status: {response.status_code}, body: {response.text}")
                assert response.status_code == 200, f"Failed for {file_name}, id={idx}: {response.text}"

                data = response.json()
                prediction_str = data["sentiment"]
                log.info(f"Received prediction: {prediction_str}")

                # Convert API string to integer
                prediction_int = 1 if "positive" in prediction_str.lower() else 0
                y_pred_int.append(prediction_int)
                y_true.append(int(expected_label))

                # Save to DB
                db_client.insert_data("predictions", message, prediction_str)
                rows = db_client.get_data("predictions", limit=1)
                last_row = rows[0]
                log.info(f"Last DB row: {last_row}")
            
             # Fetch predictions from API
            fetch_response = await client.post(f"{SERVER_URL}/predictions/", json={})
            assert fetch_response.status_code == 200, f"Fetching predictions failed: {fetch_response.text}"
            data = fetch_response.json()
            fetched_predictions = data.get("predictions", [])
            log.info(f"Fetched {len(fetched_predictions)} predictions from API")

            # Calculate functional metrics like in func_test
            y_true = np.array(y_true)
            y_pred_int = np.array(y_pred_int)
            accuracy = accuracy_score(y_true, y_pred_int)
            report = classification_report(y_true, y_pred_int)
            log.info(f"Functional test results for {file_name}: Accuracy={accuracy}")
            log.info(f"Classification Report:\n{report}")

    log.info("Functional test completed successfully.")