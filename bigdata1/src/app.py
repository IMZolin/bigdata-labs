from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from src.predict import Predictor, parse_args
import logging


class Message(BaseModel):
    message: str

class SentimentAPI:
    def __init__(self, args=None):
        self.app = FastAPI()
        self.predictor = Predictor()
        self.args = args or parse_args()
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.post("/predict/")
        async def predict_sentiment(message: Message):
            try:
                logging.info("Received message: %s", message.message)  
                result = self.predictor.predict(message.message)
                logging.info("Prediction result: %s", result)  
                if result:
                    return {"sentiment": result} 
                else:
                    raise HTTPException(status_code=500, detail="Error during prediction")
            except Exception as e:
                logging.error(f"Error in prediction: {e}")
                raise HTTPException(status_code=500, detail="Prediction failed")

        @self.app.get("/health/")
        async def health_check():
            return {"status": "OK"}
        
    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    args = parse_args()
    sentiment_api = SentimentAPI(args)
    sentiment_api.run()