#!/usr/bin/env bash
# Fill missing AUTH keys in existing .env
# Usage: ./fill-auth-keys.sh

set -euo pipefail

ENV_FILE=".env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found"
    exit 1
fi

# Generate keys
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 32)

# Check if already set
if grep -q "^AUTH_SECRET_KEY=***" "$ENV_FILE"; then
    echo "AUTH_SECRET_KEY already set, skipping"
else
    sed -i "s|^AUTH_SECRET_KEY=.*$|AUTH_SECRET_KEY=${SECRET_KEY}|" "$ENV_FILE"
    echo "✓ AUTH_SECRET_KEY set"
fi

if grep -q "^AUTH_API_KEY=***" "$ENV_FILE"; then
    echo "AUTH_API_KEY already set, skipping"
else
    sed -i "s|^AUTH_API_KEY=.*$|AUTH_API_KEY=${API_KEY}|" "$ENV_FILE"
    echo "✓ AUTH_API_KEY set"
fi

echo ""
echo "Current auth config:"
grep -E "^AUTH_(ENABLED|SECRET|API)_KEY" "$ENV_FILE" | sed 's/=.*/=***REDACTED***/'
