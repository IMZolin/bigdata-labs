#!/bin/sh

# Wait for Vault to start
sleep 5

# Set Vault address
export VAULT_ADDR='http://vault:8200'

# Check if Vault is already initialized
INIT_STATUS=$(vault status -format=json 2>/dev/null | jq -r '.initialized')

if [ "$INIT_STATUS" = "true" ]; then
  echo "Vault is already initialized. Using existing configuration."

  # Check if we have a root token
  if [ -f /vault/data/root_token.txt ]; then
    VAULT_ROOT_TOKEN=$(cat /vault/data/root_token.txt)

    # Check if Vault is sealed
    SEAL_STATUS=$(vault status -format=json 2>/dev/null | jq -r '.sealed')

    if [ "$SEAL_STATUS" = "true" ] && [ -f /vault/data/unseal_key.txt ]; then
      VAULT_UNSEAL_KEY=$(cat /vault/data/unseal_key.txt)
      echo "Unsealing Vault..."
      vault operator unseal $VAULT_UNSEAL_KEY
    fi

    # Login with root token
    echo "Logging in with root token..."
    vault login $VAULT_ROOT_TOKEN

    if [ -z "${CLICKHOUSE_USER}" ] || [ -z "${CLICKHOUSE_PASSWORD}" ] || [ -z "${CLICKHOUSE_DATABASE}" ] || [ -z "${CLICKHOUSE_PORT}" ]; then
      echo "Warning: One or more database environment variables are not set."
      echo "CLICKHOUSE_USER: ${CLICKHOUSE_USER:-not set}"
      echo "CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-not set}"
      echo "CLICKHOUSE_DATABASE: ${CLICKHOUSE_DATABASE:-not set}"
      echo "CLICKHOUSE_PORT: ${CLICKHOUSE_PORT:-not set}"
      echo "CLICKHOUSE_HOST: ${CLICKHOUSE_HOST:-not set}"
      echo "Using default values for missing variables."

      # Set default values if not provided
    CLICKHOUSE_USER=${CLICKHOUSE_USER:-model_user}
    CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-strongpassword}
    CLICKHOUSE_DATABASE=${CLICKHOUSE_DATABASE:-mydb}
    CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-8123}
    CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-clickhouse}
    fi

    # Update database credentials in Vault
    echo "Updating database credentials in Vault..."
    vault kv put kv/database/credentials \
      username=${CLICKHOUSE_USER} \
      password=${CLICKHOUSE_PASSWORD} \
      dbname=${CLICKHOUSE_DATABASE} \
      port=${CLICKHOUSE_PORT} \
      host=${CLICKHOUSE_HOST}

    echo "Vault configuration updated!"
  else
    echo "Root token not found. Cannot configure Vault."
    exit 1
  fi
else
  echo "Vault is not initialized. Please run init.sh first."
  exit 1
fi
