import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open

from src.vault import VaultClient, get_vault_client


class TestVaultClient(unittest.TestCase):

    @patch("src.vault.hvac.Client")
    def test_init_with_env_token(self, mock_hvac):
        os.environ["VAULT_TOKEN"] = "envtoken"
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True

        client = VaultClient()
        self.assertEqual(client.token, "envtoken")
        self.assertTrue(client.is_authenticated())

        del os.environ["VAULT_TOKEN"]

    @patch("src.vault.hvac.Client")
    def test_init_with_file_token(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True

        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("filetoken")
            f.flush()
            client = VaultClient(token_path=f.name)
        self.assertEqual(client.token, "filetoken")
        self.assertTrue(client.is_authenticated())

    @patch("src.vault.hvac.Client")
    def test_init_no_token_fallback_root(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        client = VaultClient(token=None)
        self.assertEqual(client.token, "root")

    @patch("src.vault.hvac.Client")
    def test_init_auth_failure(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = False
        with self.assertRaises(RuntimeError):
            VaultClient()

    @patch("src.vault.hvac.Client")
    def test_get_db_credentials_success(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"host": "h", "port": "1234", "username": "u", "password": "p"}}
        }
        client = VaultClient(token="t")
        creds = client.get_db_credentials()
        self.assertEqual(creds["host"], "h")

    @patch("src.vault.hvac.Client")
    def test_get_db_credentials_failure(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("fail")
        client = VaultClient(token="t")
        creds = client.get_db_credentials()
        self.assertIsNone(creds)

    @patch("src.vault.hvac.Client")
    def test_get_connection_with_vault(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"host": "vault-host", "port": "8123", "username": "user", "password": "pw"}}
        }
        client = VaultClient(token="t")
        conn = client.get_connection()
        self.assertEqual(conn[0], "vault-host")
        self.assertEqual(conn[2], "user")

    @patch("src.vault.hvac.Client")
    def test_get_connection_env_fallback(self, mock_hvac):
        os.environ["CLICKHOUSE_HOST"] = "envhost"
        os.environ["CLICKHOUSE_USER"] = "envuser"
        os.environ["CLICKHOUSE_PASSWORD"] = "envpw"

        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("fail")

        client = VaultClient(token="t")
        host, port, user, password = client.get_connection()
        self.assertEqual(host, "envhost")
        self.assertEqual(user, "envuser")
        self.assertEqual(password, "envpw")

        del os.environ["CLICKHOUSE_HOST"]
        del os.environ["CLICKHOUSE_USER"]
        del os.environ["CLICKHOUSE_PASSWORD"]

    @patch("src.vault.hvac.Client")
    def test_is_authenticated_and_list_secrets(self, mock_hvac):
        mock_client = mock_hvac.return_value
        mock_client.is_authenticated.return_value = True
        mock_client.sys.list_mounted_secrets_engines.return_value = {"kv/": {}}

        client = VaultClient(token="t")
        self.assertTrue(client.is_authenticated())
        self.assertTrue(client.list_mounted_secrets_engines())

    @patch("src.vault.VaultClient")
    def test_get_vault_client_singleton(self, mock_vault_class):
        mock_instance = mock_vault_class.return_value
        mock_instance.is_authenticated.return_value = True
        c1 = get_vault_client()
        c2 = get_vault_client()
        self.assertIs(c1, c2)
        mock_vault_class.assert_called_once()



if __name__ == "__main__":
    unittest.main()
