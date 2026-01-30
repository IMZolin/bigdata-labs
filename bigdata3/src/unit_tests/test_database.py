import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from parameterized import parameterized
from clickhouse_connect.driver.exceptions import ClickHouseError

# Ensure src is in path
sys.path.insert(1, os.path.join(os.getcwd(), "src"))
from src.database import ClickHouseClient


class TestClickHouseClient(unittest.TestCase):
    def setUp(self):
        self.client = ClickHouseClient()
        self.client.get_db_cred(host="localhost")  # Set credentials explicitly

    @patch("sys.exit")
    @patch("clickhouse_connect.get_client", side_effect=ClickHouseError("Connection error"))
    def test_connect_failure(self, mock_get_client, mock_exit):
        client = ClickHouseClient()
        client.get_db_cred(host="fake_host")
        mock_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit):
            client.connect()

        self.assertEqual(mock_get_client.call_count, 5)
        mock_exit.assert_called_once_with(1)


    @patch("clickhouse_connect.get_client")
    def test_connect_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        self.assertTrue(self.client.connect())
        self.assertIs(self.client.client, mock_client)

    def test_close(self):
        # With active client
        mock_client = MagicMock()
        self.client.client = mock_client
        self.client.close()
        mock_client.close.assert_called_once()
        self.assertIsNone(self.client.client)

        # Without active client
        self.client.client = None
        self.client.close()
        self.assertIsNone(self.client.client)

    def test_execute_query_no_connection(self):
        with self.assertRaises(RuntimeError):
            self.client.execute_query("SELECT 1")

    @parameterized.expand([
        ("success", None, [(1,)], False),
        ("failure", Exception("Query failed"), None, True),
    ])
    @patch("clickhouse_connect.get_client")
    def test_execute_query_cases(self, _, side_effect, result_rows, expect_raise, mock_get_client):
        mock_client = MagicMock()
        if not side_effect:
            mock_client.query.return_value = MagicMock(result_rows=result_rows)
        else:
            mock_client.query.side_effect = side_effect
        mock_get_client.return_value = mock_client
        self.client.connect()

        if expect_raise:
            with self.assertRaises(Exception):
                self.client.execute_query("SELECT 1")
        else:
            result = self.client.execute_query("SELECT 1")
            self.assertEqual(result.result_rows, result_rows)

    @parameterized.expand([
        ("create_table_success", None, False),
        ("create_table_failure", Exception("Create failed"), True),
    ])
    @patch("clickhouse_connect.get_client")
    def test_create_table_cases(self, _, side_effect, expect_raise, mock_get_client):
        mock_client = MagicMock()
        mock_client.command.side_effect = side_effect
        mock_get_client.return_value = mock_client
        self.client.connect()

        if expect_raise:
            with self.assertRaises(Exception):
                self.client.create_table("tbl")
        else:
            self.client.create_table("tbl")
            self.assertIn("CREATE TABLE IF NOT EXISTS tbl", mock_client.command.call_args[0][0])

    @parameterized.expand([
        ("insert_success", None, False),
        ("insert_failure", Exception("Insert failed"), True),
    ])
    @patch("clickhouse_connect.get_client")
    def test_insert_data_cases(self, _, side_effect, expect_raise, mock_get_client):
        mock_client = MagicMock()
        mock_client.insert.side_effect = side_effect
        mock_get_client.return_value = mock_client
        self.client.connect()

        if expect_raise:
            with self.assertRaises(Exception):
                self.client.insert_data("tbl", "msg", "pred")
        else:
            self.client.insert_data("tbl", "msg", "pred")
            mock_client.insert.assert_called_once_with(
                table="tbl",
                data=[("msg", "pred")],
                column_names=["message", "prediction"],
            )

    @parameterized.expand([
        ("get_data_success", None, [(1, "msg", "pred")], False),
        ("get_data_failure", Exception("Fetch failed"), None, True),
    ])
    @patch("clickhouse_connect.get_client")
    def test_get_data_cases(self, _, side_effect, result_rows, expect_raise, mock_get_client):
        mock_client = MagicMock()
        if not side_effect:
            mock_client.query.return_value = MagicMock(result_rows=result_rows)
        else:
            mock_client.query.side_effect = side_effect
        mock_get_client.return_value = mock_client
        self.client.connect()

        if expect_raise:
            with self.assertRaises(Exception):
                self.client.get_data("tbl")
        else:
            result = self.client.get_data("tbl", limit=5)
            self.assertEqual(result, result_rows)
            self.assertIn("LIMIT 5", mock_client.query.call_args[0][0])


if __name__ == "__main__":
    unittest.main()