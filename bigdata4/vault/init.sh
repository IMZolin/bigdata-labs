#!/bin/sh
set -e

# Wait for Vault to start
sleep 5

# Set Vault address
export VAULT_ADDR='http://127.0.0.1:8200'

# Initialize Vault with 1 key share and 1 key threshold
vault operator init -key-shares=1 -key-threshold=1 > /vault/data/init.txt

# Extract root token and unseal key
VAULT_UNSEAL_KEY=$(grep 'Unseal Key 1:' /vault/data/init.txt | awk '{print $NF}')
VAULT_ROOT_TOKEN=$(grep 'Initial Root Token:' /vault/data/init.txt | awk '{print $NF}')

# Save tokens to files for later use
echo "$VAULT_UNSEAL_KEY" > /vault/data/unseal_key.txt
echo "$VAULT_ROOT_TOKEN" > /vault/data/root_token.txt

# Unseal Vault
vault operator unseal "$VAULT_UNSEAL_KEY"

# Authenticate non-interactively
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

# Enable the KV secrets engine (v2) idempotently
vault secrets enable -version=2 kv || true

# Create a policy for our application (read access to kv v2 paths)
cat > /tmp/app-policy.hcl << 'EOF'
path "kv/data/database/*" {
  capabilities = ["read"]
}
path "kv/data/kafka/*" {
  capabilities = ["read"]
}
EOF

# Write the policy
vault policy write app-policy /tmp/app-policy.hcl

# Create an app token with the app-policy
vault token create -policy=app-policy -format=json | jq -r '.auth.client_token' > /vault/data/app_token.txt

# Check for environment variables or use defaults
# Check if environment variables are set
if [ -z "${CLICKHOUSE_USER}" ] || [ -z "${CLICKHOUSE_PASSWORD}" ] || [ -z "${CLICKHOUSE_DATABASE}" ] || [ -z "${CLICKHOUSE_PORT}" ] || [ -z "${CLICKHOUSE_HOST}" ] || [ -z "${KAFKA_BOOTSTRAP_SERVERS}" ]; then
  echo "Warning: One or more database environment variables are not set."
  echo "CLICKHOUSE_USER: ${CLICKHOUSE_USER:-not set}"
  echo "CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-not set}"
  echo "CLICKHOUSE_DATABASE: ${CLICKHOUSE_DATABASE:-not set}"
  echo "CLICKHOUSE_PORT: ${CLICKHOUSE_PORT:-not set}"
  echo "CLICKHOUSE_HOST: ${CLICKHOUSE_HOST:-not set}"
  echo "KAFKA_BOOTSTRAP_SERVERS: ${KAFKA_BOOTSTRAP_SERVERS:-not set}"
  echo "Using default values for missing variables."

  # Set default values if not provided
  CLICKHOUSE_USER=${CLICKHOUSE_USER:-model_user}
  CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-strongpassword}
  CLICKHOUSE_DATABASE=${CLICKHOUSE_DATABASE:-mydb}
  CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-8123}
  CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-clickhouse}
  KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}
fi

if [ -z "${KAFKA_BOOTSTRAP_SERVERS}" ] || [ -z "${KAFKA_TOPIC}" ] || [ -z "${KAFKA_CONSUMER_GROUP}" ]; then
  echo "Warning: One or more database environment variables are not set."
  echo "KAFKA_BOOTSTRAP_SERVERS: ${KAFKA_BOOTSTRAP_SERVERS:-not set}"
  echo "KAFKA_TOPIC: ${KAFKA_TOPIC:-not set}"
  echo "KAFKA_CONSUMER_GROUP: ${KAFKA_CONSUMER_GROUP:-not set}"
  echo "Using default values for missing variables."

  # Set default values if not provided
  KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}
  KAFKA_TOPIC=${KAFKA_TOPIC:-predictions}
  KAFKA_CONSUMER_GROUP=${KAFKA_CONSUMER_GROUP:-prediction-group}
fi

# Store database credentials in Vault
vault kv put kv/database/credentials \
  username="${CLICKHOUSE_USER}" \
  password="${CLICKHOUSE_PASSWORD}" \
  dbname="${CLICKHOUSE_DATABASE}" \
  port="${CLICKHOUSE_PORT}" \
  host=${CLICKHOUSE_HOST}
  host=postgres

# Store Kafka credentials in Vault
vault kv put secret/kafka/credentials \
  bootstrap_servers=${KAFKA_BOOTSTRAP_SERVERS} \
  topic="${KAFKA_TOPIC}" \
  group="${KAFKA_CONSUMER_GROUP}" 

echo "Vault has been initialized and configured!"
echo "App token: $(cat /vault/data/app_token.txt)"
