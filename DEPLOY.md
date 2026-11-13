# Server Deployment Guide

## 1. Pull Code

```bash
git clone https://github.com/just1bite/hindsight.git
cd hindsight
```

## 2. Install Dependencies

### Option A: Docker (Recommended for Server)

```bash
# Create .env from template
cp .env.example .env

# Generate secure keys
SECRET=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 32)
PASSWORD=$(openssl rand -base64 16)

# Configure .env (replace placeholders)
# LLM: openai, anthropic, or TokenHarbor (https://tokenharbor.ai/v1)
# Auth: enable with generated credentials

# Deploy
docker compose -f docker/docker-compose.yml up -d

# Verify
curl http://localhost:8888/health
```

### Option B: Systemd User Service (Local Development)

```bash
# Install uv
curl -LsFf https://astral.sh/uv/install.sh | sh

# Create .env, sync dependencies
cp .env.example .env
uv sync

# Create systemd service (see start-hindsight.sh)
systemctl --user daemon-reload
systemctl --user enable hindsight.service
systemctl --user start hindsight.service
```

## 3. Configure External Agents

All agents connect via `AUTH_API_KEY` from `.env`.

### Environment Variables

```bash
HINDSIGHT_URL=http://your-server:8888
HINDSIGHT_BANK=fuahari
HINDSIGHT_USERNAME=admin
HINDSIGHT_PASSWORD=your-password
HINDSIGHT_API_KEY=your-auth-api-key  # From .env AUTH_API_KEY
```

### Python Agent Example

```python
import os
import requests

HINDSIGHT_URL = os.environ.get("HINDSIGHT_URL", "http://localhost:8888")
API_KEY = os.environ["HINDSIGHT_API_KEY"]

def save_memory(bank_id: str, content: str):
    """Save memory to Hindsight."""
    auth = requests.post(
        f"{HINDSIGHT_URL}/auth/login",
        json={"username": "admin", "password": os.environ["HINDSIGHT_PASSWORD"]}
    ).json()
    token = auth["access_token"]
    
    resp = requests.post(
        f"{HINDSIGHT_URL}/v1/default/banks/{bank_id}/memories",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"content": content}]}
    )
    return resp.json()

# Usage
save_memory("fuahari", "Conversation summary from session")
```

### Curl Quick Test

```bash
# Login
TOKEN=$(curl -s -X POST http://your-server:8888/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}' | jq -r '.access_token')

# Save
curl -s -X POST http://your-server:8888/v1/default/banks/fuahari/memories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"content":"Test from server"}]}'

# Verify
curl -s http://your-server:8888/v1/default/banks/fuahari/memories/list \
  -H "Authorization: Bearer $TOKEN" | jq '.total'
```

## 4. Verify Deployment

```bash
# API Health
curl http://localhost:8888/health

# UI Access
# http://localhost:9999 (login: admin / your-password)
```

## 5. Firewall (If Exposing Externally)

```bash
# Ubuntu/Debian
sudo ufw allow 8888/tcp  # API
sudo ufw allow 9999/tcp  # UI

# RHEL/CentOS
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --permanent --add-port=9999/tcp
sudo firewall-cmd --reload
```

## 6. Database Backup

Hindsight uses embedded PostgreSQL.

```bash
# Stop service
systemctl --user stop hindsight  # or sudo systemctl stop hindsight

# Backup data
cp -r /home/hindsight/.pg0 ~/hindsight-backup-$(date +%Y%m%d)

# Start service
systemctl --user start hindsight
```

## 7. Sync Between Local and Server

Update `~/.hermes/scripts/hindsight_retain.py` to point to server:

```bash
export HINDSIGHT_API_URL="http://your-server:8888"
```

Or use `.env` on server for shared credentials.
