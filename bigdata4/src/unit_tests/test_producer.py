import unittest
from unittest.mock import patch, MagicMock
from src.kafka.producer import Producer


class TestProducerCoverage(unittest.TestCase):
    @patch("src.kafka.producer.get_vault_client")
    @patch("src.kafka.producer.KafkaProducer")
    def test_send_success(self, mock_kafka_producer, mock_get_vault):
        # Vault returns valid credentials
        mock_vault = MagicMock()
        mock_vault.get_kafka_credentials.return_value = (["localhost:9092"], "topic", "group")
        mock_get_vault.return_value = mock_vault

        # KafkaProducer returns successful future
        mock_future = MagicMock()
        mock_future.get.return_value.partition = 0
        mock_future.get.return_value.offset = 1
        mock_instance = MagicMock()
        mock_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_instance

        producer = Producer()
        result = producer.send({"message": "ok"})
        self.assertTrue(result)

    @patch("src.kafka.producer.get_vault_client")
    @patch("src.kafka.producer.KafkaProducer")
    def test_send_failure_with_retries(self, mock_kafka_producer, mock_get_vault):
        mock_vault = MagicMock()
        mock_vault.get_kafka_credentials.return_value = (["localhost:9092"], "topic", "group")
        mock_get_vault.return_value = mock_vault

        mock_instance = MagicMock()
        mock_instance.send.side_effect = Exception("Kafka down")
        mock_kafka_producer.return_value = mock_instance

        producer = Producer()
        success = producer.send({"message": "fail"})
        self.assertFalse(success)
        self.assertEqual(mock_instance.send.call_count, producer.retries)

    @patch("src.kafka.producer.KafkaProducer")
    @patch("src.kafka.producer.get_vault_client")
    def test_setup_kafka_fallback_to_default(self, mock_get_vault, mock_kafka_producer):
        # Simulate Vault missing get_kafka_credentials -> triggers AttributeError
        mock_vault = MagicMock()
        del mock_vault.get_kafka_credentials  # remove attribute
        mock_get_vault.return_value = mock_vault

        mock_instance = MagicMock()
        mock_kafka_producer.return_value = mock_instance

        producer = Producer()
        self.assertIsNotNone(producer.producer)
        mock_kafka_producer.assert_called()  


    @patch("src.kafka.producer.get_vault_client")
    @patch("src.kafka.producer.KafkaProducer")
    def test_close_without_producer(self, mock_kafka_producer, mock_get_vault):
        # Vault fails to provide KafkaProducer
        mock_get_vault.side_effect = Exception("Vault unreachable")
        producer = Producer.__new__(Producer)
        producer.logger = MagicMock()
        # _producer attribute does not exist
        producer.close()
        producer.logger.warning.assert_called()

    @patch("src.kafka.producer.get_vault_client")
    @patch("src.kafka.producer.KafkaProducer")
    def test_send_non_dict_message(self, mock_kafka_producer, mock_get_vault):
        # Vault returns valid credentials
        mock_vault = MagicMock()
        mock_vault.get_kafka_credentials.return_value = (["localhost:9092"], "topic", "group")
        mock_get_vault.return_value = mock_vault

        mock_future = MagicMock()
        mock_future.get.return_value.partition = 0
        mock_future.get.return_value.offset = 1
        mock_instance = MagicMock()
        mock_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_instance

        producer = Producer()
        # sending a non-dict value
        result = producer.send("string payload")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
