from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import time
from src.predict import Predictor
from logger import Logger
from src.database import ClickHouseClient  
from src.vault import get_vault_client
import configparser
import os
from dotenv import load_dotenv

class Message(BaseModel):
    message: str


class SentimentAPI:
    def __init__(self):
        self.app = FastAPI()
        self.logger = Logger(show=True).get_logger(__name__)
        self.predictor = Predictor()
        load_dotenv()  # load .env file into environment variables
        self.db_client = None
        self.vault_client = None
        self.vault_connected = False
        self._setup_vault()
        self._setup_database()
        self._setup_routes()

    def _setup_vault(self):
        try:
            self.vault_client = get_vault_client()
            if self.vault_client and self.vault_client.is_authenticated():
                self.vault_connected = True
                self.logger.info("Vault client initialized successfully")
            else:
                self.vault_connected = False
                self.logger.error("Failed to initialize Vault client")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vault client: {e}")
            self.vault_connected = False

    def _setup_database(self):
        max_db_connection_attempts = 5
        self.db_connected = False

        for attempt in range(max_db_connection_attempts):
            try:
                if not self.vault_client:
                    self.logger.warning("Vault client is not available, falling back to env vars")
                self.db_client = ClickHouseClient()
                self.db_client.get_db_cred()
                self.db_client.connect()
                self.db_client.create_table("predictions")
                self.db_connected = True
                self.logger.info("Database setup completed successfully")
                break
            except Exception as e:
                self.logger.error(
                    f"Failed to create database tables (attempt {attempt + 1} of {max_db_connection_attempts}): {e}"
                )
                time.sleep(3)
        if not self.db_connected:
            self.logger.warning(f"Failed to connect to database after {max_db_connection_attempts} attempts")
            self.logger.warning("Continuing without database support")

    def _setup_routes(self):
        @self.app.post("/predict/")
        async def predict_sentiment(message: Message):
            try:
                self.logger.info("Received message: %s", message.message)
                result = self.predictor.predict(message.message)
                self.logger.info("Prediction result: %s", result)

                try:
                    self.db_client.insert_data("predictions", message.message, result)
                    self.logger.info("Saved prediction to DB with message: %s and result: %s", message.message, result)
                except Exception as e:
                    self.logger.error(f"Failed to save prediction to DB: {e}")

                if result:
                    return {"sentiment": result}
                else:
                    raise HTTPException(status_code=500, detail="Error during prediction")
            except Exception as e:
                self.logger.error(f"Error in prediction: {e}")
                raise HTTPException(status_code=500, detail="Prediction failed")
            
        @self.app.post("/predictions/")
        async def get_predictions(limit: int = 10):
            try:
                if not self.db_connected:
                    raise HTTPException(status_code=503, detail="Database not available")
                self.logger.info(f"Fetching last {limit} predictions from DB")
                rows = self.db_client.get_data("predictions", limit)
                predictions = [
                    {
                        "timestamp": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                        "message": row[1],
                        "prediction": row[2]
                    }
                    for row in rows
                ]
                return {"predictions": predictions}
            except Exception as e:
                self.logger.error(f"Error fetching predictions: {e}")
                raise HTTPException(status_code=500, detail="Failed to fetch predictions")

        @self.app.get("/vault-status/")
        async def vault_status():
            if not self.vault_connected:
                raise HTTPException(status_code=500, detail="Failed to connect to Vault")
            try:
                vault_status = {
                    "connected": self.vault_connected,
                    "authenticated": self.vault_client.is_authenticated() if self.vault_client else False,
                    "secrets_engine": "Available" if self.vault_client.list_mounted_secrets_engines() else "Not available"
                }
                self.logger.info(f"Vault status: {vault_status}")
                return vault_status
            except Exception as e:
                self.logger.error(f"Error getting Vault status: {e}")
                raise HTTPException(status_code=500, detail="Failed to get Vault status")
        
        @self.app.get("/health/")
        async def health_check():
            status = {
                "status": "healthy",
                "model_loaded": getattr(self, "predictor", None) is not None,
                "database_connected": getattr(self, "db_connected", False),
                "vault_connected": getattr(self, "vault_connected", False),
            }
            self.logger.info(f"Health check: {status}")
            return status

        @self.app.get("/ready/")
        async def readiness_check():
            return {"status": "OK"}

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


def main():
    sentiment_api = SentimentAPI()
    sentiment_api.run()

if __name__ == "__main__":
    main()
