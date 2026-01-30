import json
import os
import time
import threading
from kafka import KafkaConsumer
from src.logger import Logger
from src.vault import get_vault_client
from src.database import ClickHouseClient

SHOW_LOG = True

class Consumer:
    def __init__(self, host=None):
        self.logger = Logger(show=SHOW_LOG).get_logger(__name__)
        self.db_client = None
        self.db_connected = False
        self._setup_database()
        self._setup_kafka(host=host)

    def _setup_database(self):
        try:
            self.db_client = ClickHouseClient()
            self.db_client.get_db_cred()
            self.db_client.connect()
            self.db_client.create_table("predictions")
            self.db_connected = True
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            self.db_connected = False

    def _setup_kafka(self, host=None):
        self.vault = get_vault_client()
        # --- Get Kafka credentials ---
        try:
            self.bootstrap_servers, self.topic, self.group_id = self.vault.get_kafka_credentials()
        except ValueError as e:
            self.logger.warning(
                f"Vault client could not provide Kafka credentials: {e}. Using default values."
            )
            self.bootstrap_servers = ["localhost:9092"]
            self.topic = "default-topic"
            self.group_id = "default-group"

        self._stopped = threading.Event()

        self.logger.info(
            f"Initializing Kafka consumer: {self.bootstrap_servers}, topic={self.topic}, group={self.group_id}"
        )

        # --- Retry Kafka connection ---
        retries = 5
        for attempt in range(1, retries + 1):
            try:
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                )
                self.logger.info("Kafka consumer connected successfully.")
                break
            except Exception as e:
                self.logger.warning(f"Kafka not available (attempt {attempt}/{retries}): {e}")
                time.sleep(5)
        else:
            raise RuntimeError("Failed to connect to Kafka after retries.")

    def _handle_message(self, msg_value):
        """
        Extracts fields and saves message to ClickHouse.
        Expected format: {'message': '...', 'prediction': '...'}.
        """
        try:
            if not isinstance(msg_value, dict):
                msg_value = {"message": str(msg_value), "prediction": str(msg_value)}

            message = msg_value.get("message")
            prediction = msg_value.get("prediction") or msg_value.get("sentiment")

            self.db_client.insert_data(
                "predictions", message or str(msg_value), prediction or str(msg_value)
            )
            self.logger.info(f"Saved message to ClickHouse: {msg_value}")
        except Exception as e:
            self.logger.error(f"Error handling incoming message: {e}", exc_info=True)

    def run(self):
        self.logger.info("Starting Kafka consumer loop...")
        for msg in self.consumer:
            if self._stopped.is_set():
                break
            try:
                payload = msg.value
                self.logger.info(f"Received message from Kafka: {payload}")
                if self.db_client:
                    self._handle_message(payload)
                else:
                    self.logger.warning("No DB client available. Skipping message.")
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
        self.logger.info("Consumer loop stopped.")

    def stop(self):
        self._stopped.set()
        if hasattr(self, "consumer") and self.consumer:
            self.consumer.close()
        if hasattr(self, "db_client") and self.db_client:
            self.db_client.close()
        self.logger.info(f"Kafka consumer stopped (topic={getattr(self, 'topic', 'unknown')})")


if __name__ == "__main__":  
    consumer = Consumer()
    consumer.run()
