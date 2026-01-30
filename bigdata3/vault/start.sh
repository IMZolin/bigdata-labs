#!/bin/sh

# Start Vault server in dev mode
vault server -dev -dev-root-token-id=root -dev-listen-address=0.0.0.0:8200 &

# Wait for Vault to start
sleep 5

echo "Vault started in dev mode. Configuring..."

# Set Vault address
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

# Run the initialization script if Vault is not already initialized
# if [ ! -f /vault/data/init.txt ]; then
#   echo "Initializing Vault..."
#   /vault/init.sh
# else
#   echo "Vault already initialized. Configuring..."
#   /vault/configure.sh
# fi

if [ -z "${CLICKHOUSE_USER}" ] || [ -z "${CLICKHOUSE_PASSWORD}" ] || [ -z "${CLICKHOUSE_DATABASE}" ] || [ -z "${CLICKHOUSE_PORT}" ] || [ -z "${CLICKHOUSE_HOST}" ]; then
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

vault kv put secret/database/credentials \
  username="${CLICKHOUSE_USER}" \
  password="${CLICKHOUSE_PASSWORD}" \
  dbname="${CLICKHOUSE_DATABASE}" \
  port="${CLICKHOUSE_PORT}" \
  host="${CLICKHOUSE_HOST}"


echo "Vault has been configured!"
echo "========== Secret Path =========="
vault kv get secret/database/credentials

# Keep the container running
tail -f /dev/null