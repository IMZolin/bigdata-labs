import os
import time
import hvac
import configparser
from src.logger import Logger

SHOW_LOG = True

class VaultClient:
    """
    Wrapper for HashiCorp Vault client (hvac).
    Handles authentication and secret retrieval.
    """

    def __init__(self, addr=None, token=None, token_path="/vault/data/app_token.txt", config_path="config.ini"):
        """
        Args:
            addr (str): Vault server address. Defaults to env VAULT_ADDR or http://vault:8200
            token (str): Vault token. Defaults to env VAULT_TOKEN or read from file.
            token_path (str): Path to token file if env var not set.
        """
        self.addr = addr or os.environ.get("VAULT_ADDR", "http://vault:8200")
        self.token = token or os.environ.get("VAULT_TOKEN", None)
        self.logger = Logger(show=SHOW_LOG).get_logger(__name__)
        self.config = configparser.ConfigParser()
        self.config_path = config_path
        self.config.read(config_path)

        if not self.token and os.path.exists(token_path):
            try:
                with open(token_path, "r") as f:
                    self.token = f.read().strip()
                    self.logger.info(f"Loaded Vault token from {token_path}")
            except Exception as e:
                self.logger.warning(f"Failed to read token from {token_path}: {e}")

        if not self.token:
            self.logger.warning("No Vault token provided, falling back to 'root' (for testing only).")
            self.token = "root"
        self.logger.info(f"Connecting to Vault at {self.addr}")
        self.client = hvac.Client(url=self.addr, token=self.token)
        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")
        self.logger.info("Vault client successfully authenticated")

    def get_client(self):
        """Return the underlying hvac.Client"""
        return self.client

    def get_db_credentials(self, path="database/credentials", mount_point="secret"):
        """
        Retrieve database credentials from Vault KV v2.

        Args:
            path (str): Path to the secret in Vault.
            mount_point (str): KV engine mount point.
        
        Returns:
            dict | None: Secret data or None if not found.
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point
            )
            vault_credentials = response.get("data", {}).get("data")
            db_config = self.config["DATABASE"] if "DATABASE" in self.config else {}
            if vault_credentials:
                try:
                    host = vault_credentials.get("host", db_config.get("host", "clickhouse"))
                    port = int(vault_credentials.get("port", db_config.get("port", "8123")))
                    user = vault_credentials.get("username", db_config.get("user", "default"))
                    password = vault_credentials.get("password", db_config.get("password", ""))
                    self.logger.info("Using database credentials from Vault")
                except AttributeError:
                    self.logger.warning("Vault client missing get_connection method. Using defaults.")
                    host = "localhost"
                    port = 8123
                    user = "default"
                    password = ""
            else:
                # Fall back to environment variables
                self.logger.warning("Vault client unavailable. Using environment/default credentials.")
                host = os.environ.get("CLICKHOUSE_HOST", db_config.get("host", "clickhouse"))
                port = int(os.environ.get("CLICKHOUSE_PORT", db_config.get("port", "8123")))
                user = os.environ.get("CLICKHOUSE_USER", db_config.get("user", "default"))
                password = os.environ.get("CLICKHOUSE_PASSWORD", db_config.get("password", ""))
                self.logger.info("Using database credentials from environment variables")
            return host, port, user, password
        except Exception as e:
            self.logger.error(f"Error retrieving database credentials from Vault: {e}")
            return None
        
    def get_kafka_credentials(self, path="kafka/credentials", mount_point="secret"):
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point
            )
            vault_credentials = response.get("data", {}).get("data")
            if vault_credentials:
                try:
                    bootstrap_servers = vault_credentials.get("bootstrap_servers", 'kafka:9092')
                    topic = vault_credentials.get("topic", 'predictions')
                    group = vault_credentials.get("group", 'prediction-group')
                except AttributeError:
                    self.logger.warning("Vault client missing get_connection method. Using defaults.")
                    bootstrap_servers = "kafka:9092"
                    topic = "predictions"
                    group = "prediction-group"
            else:
                # Fall back to environment variables
                self.logger.warning("Vault client unavailable. Using environment/default credentials.")
                bootstrap_servers  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
                topic = int(os.getenv("KAFKA_TOPIC", "predictions"))
                group = os.getenv("KAFKA_CONSUMER_GROUP", "prediction-group")
            return bootstrap_servers, topic, group
        except Exception as e:
            self.logger.error(f"Error retrieving kafka credentials from Vault: {e}")
            return None

    def is_authenticated(self):
        return self.client and self.client.is_authenticated()

    def list_mounted_secrets_engines(self):
        return self.client and self.client.sys.list_mounted_secrets_engines()
    

# Singleton helper
_vault_client = None

def get_vault_client():
    logger = Logger(show=SHOW_LOG).get_logger(__name__)
    global _vault_client
    if _vault_client is None:
        try:
            client = VaultClient()
            if not client.is_authenticated():
                logger.warning("Vault not authenticated, returning None.")
            _vault_client = client
        except Exception as e:
            logger.error(f"Failed to create Vault client: {e}")
            _vault_client = None
    return _vault_client 