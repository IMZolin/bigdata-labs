import os
import json
import time
from kafka import KafkaProducer
from src.logger import Logger
from src.vault import get_vault_client

SHOW_LOG = True

class Producer:
    def __init__(self):
        self.logger = Logger(show=SHOW_LOG).get_logger(__name__)
        self.retries = 5
        self._setup_kafka()
    
    def _setup_kafka(self):
        try:
            self.vault = get_vault_client()
            self.bootstrap_servers, self.topic, self.group_id = self.vault.get_kafka_credentials()
            if not self.bootstrap_servers:
                raise ValueError("No Kafka bootstrap servers provided by Vault.")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=self.retries,
                linger_ms=10,
                acks="all"
            )
        except (AttributeError, ValueError) as e:
            # Handles missing methods in vault client or invalid credentials
            self.logger.warning(
                f"Vault client failed to provide Kafka credentials: {e}. Using default localhost:9092."
            )
            try:
                # Attempt to fall back to default Kafka settings
                self.producer = KafkaProducer(
                    bootstrap_servers="localhost:9092",
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    retries=self.retries,
                    linger_ms=10,
                    acks="all"
                )
            except Exception as ex:
                self.logger.error(
                    f"Failed to initialize Kafka producer with default settings: {ex}",
                    exc_info=True
                )
                raise
        except Exception as e:
            # Catch-all for unexpected errors
            self.logger.error(
                f"Unexpected error during Kafka setup: {e}",
                exc_info=True
            )
            raise

    def send(self, payload: dict, key: str = None):
        """Send payload to configured topic. payload must be JSON-serializable."""
        for attempt in range(1, self.retries + 1):
            try:
                future = self.producer.send(self.topic, value=payload, key=(key.encode("utf-8") if key else None))
                result = future.get(timeout=10)
                self.logger.info("Sent message to Kafka topic '%s', partition=%s, offset=%s", self.topic, result.partition, result.offset)
                return True
            except Exception as e:  # pragma: no cover
                self.logger.warning("Kafka send attempt %d/%d failed: %s", attempt, self.retries, e)
                time.sleep(2)
        self.logger.error("Failed to send message to Kafka after %d attempts", self.retries)
        return False

    def close(self):
        try:
            if hasattr(self, "producer") and self.producer:
                self.producer.flush()
                self.producer.close()
                self.logger.info("Kafka producer closed successfully.")
            else:
                self.logger.warning("Kafka producer was not initialized or already closed.")
        except Exception as e:
            self.logger.error(
                f"Failed to close Kafka producer properly: {e}", 
                exc_info=True
            )