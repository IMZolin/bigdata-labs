from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from src.predict import Predictor
from logger import Logger
from src.database import ClickHouseClient  
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
        self._setup_database()
        self._setup_routes()

    def _setup_database(self):
        try:
            self.db_client = ClickHouseClient()
            self.db_client.get_db_cred()
            self.db_client.connect()
            self.db_client.create_table("predictions")
        except Exception as e:
            self.logger.error(f"Error in database initialization: {e}")

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

        @self.app.get("/health/")
        async def health_check():
            return {"status": "OK"}

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


def main():
    sentiment_api = SentimentAPI()
    sentiment_api.run()

if __name__ == "__main__":
    main()
