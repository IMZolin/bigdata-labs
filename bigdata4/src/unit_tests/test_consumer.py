import unittest
from unittest.mock import patch, MagicMock
from src.kafka.consumer import Consumer


class TestConsumer(unittest.TestCase):
    @patch("src.kafka.consumer.KafkaConsumer")
    @patch("src.kafka.consumer.ClickHouseClient")
    @patch("src.kafka.consumer.get_vault_client")
    def test_consumer_initialization(self, mock_get_vault, mock_db_client, mock_kafka_consumer):
        # Mock DB client
        mock_db = MagicMock()
        mock_db_client.return_value = mock_db
        mock_db.connect.return_value = True
        mock_db.create_table.return_value = True

        # Mock Vault client
        mock_vault = MagicMock()
        mock_vault.setup_database.return_value = mock_db
        mock_vault.db_client = mock_db
        mock_vault.get_kafka_credentials.return_value = (["localhost:9092"], "predictions", "prediction-group")
        mock_get_vault.return_value = mock_vault

        # Mock KafkaConsumer
        mock_kafka_consumer.return_value = MagicMock()
        consumer_instance = Consumer()
        consumer_instance.kafka_connected = True
        self.assertEqual(consumer_instance.topic, "predictions")
        self.assertEqual(consumer_instance.group_id, "prediction-group")
        self.assertTrue(hasattr(consumer_instance.consumer, "__iter__"))

    @patch("src.kafka.consumer.ClickHouseClient")
    def test_setup_database_failure(self, mock_db_client):
        mock_db = MagicMock()
        mock_db.connect.side_effect = Exception("DB fail")
        mock_db_client.return_value = mock_db

        consumer = Consumer.__new__(Consumer)
        consumer.logger = MagicMock()
        consumer._setup_database()
        self.assertFalse(consumer.db_connected)
        consumer.logger.error.assert_called()

    def test_handle_message_inserts_to_db(self):
        consumer = Consumer.__new__(Consumer)  
        consumer.db_client = MagicMock()
        consumer.logger = MagicMock()

        # Standard message
        msg = {"message": "Hello", "prediction": {"sentiment": "positive"}}
        consumer._handle_message(msg)
        consumer.db_client.insert_data.assert_called_once_with(
            "predictions", "Hello", {"sentiment": "positive"}
        )

        # Only sentiment key
        consumer.db_client.reset_mock()
        msg = {"sentiment": "neutral"}
        consumer._handle_message(msg)
        consumer.db_client.insert_data.assert_called_once_with(
            "predictions", str(msg), "neutral"
        )

    def test_handle_message_non_dict(self):
        consumer = Consumer.__new__(Consumer)
        consumer.db_client = MagicMock()
        consumer.logger = MagicMock()

        # Pass a string instead of dict
        consumer._handle_message("raw message")
        consumer.db_client.insert_data.assert_called_once_with(
            "predictions", "raw message", "raw message"
        )

    def test_run_exception_handling(self):
        consumer = Consumer.__new__(Consumer)
        mock_msg = MagicMock()
        mock_msg.value = {"message": "hi", "prediction": "positive"}
        
        consumer.consumer = [mock_msg].__iter__()
        consumer.db_client = MagicMock()
        consumer._handle_message = MagicMock(side_effect=Exception("boom"))
        consumer._stopped = MagicMock()
        consumer._stopped.is_set.side_effect = [False, True] 
        consumer.logger = MagicMock()

        consumer.run()
        consumer.logger.error.assert_called_with('Error processing message: boom', exc_info=True)

    def test_stop_closes_resources(self):
        consumer = Consumer.__new__(Consumer) 
        consumer.consumer = MagicMock()
        consumer.db_client = MagicMock()
        consumer.logger = MagicMock()
        consumer.topic = "predictions"
        consumer._stopped = MagicMock() 

        consumer.stop()
        consumer._stopped.set.assert_called_once()
        consumer.consumer.close.assert_called_once()
        consumer.db_client.close.assert_called_once()
        consumer.logger.info.assert_called_with("Kafka consumer stopped (topic=predictions)")

    def test_stop_no_resources(self):
        consumer = Consumer.__new__(Consumer)
        consumer.logger = MagicMock()
        consumer._stopped = MagicMock()
        # Add the missing attributes
        consumer.consumer = None
        consumer.db_client = None
        consumer.topic = "predictions"

        consumer.stop()
        consumer._stopped.set.assert_called_once()
        consumer.logger.info.assert_called()


if __name__ == "__main__":
    unittest.main()
