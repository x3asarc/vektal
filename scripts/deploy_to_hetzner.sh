#!/bin/bash
# Deploy Vektal frontend to Hetzner server via SSH.
# This script updates the repo, redeploys gateway services, and validates public health.

set -euo pipefail

SERVER_IP="${SERVER_IP:-}"
SERVER_ID="${SERVER_ID:-}"
REPO_PATH="${REPO_PATH:-/root/vektal}"
PROJECT_NAME="${PROJECT_NAME:-vektal}"
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.vektal.systems}"
ALLOW_DOMAIN_MISMATCH="${ALLOW_DOMAIN_MISMATCH:-0}"

resolve_server_ip_from_hetzner() {
  if [ -z "${HETZNER_CLOUD_API_TOKEN:-}" ] || [ -z "$SERVER_ID" ]; then
    return 1
  fi

  local parser="python3"
  if ! command -v "$parser" >/dev/null 2>&1; then
    parser="python"
  fi
  if ! command -v "$parser" >/dev/null 2>&1; then
    return 1
  fi

  curl -fsS \
    -H "Authorization: Bearer ${HETZNER_CLOUD_API_TOKEN}" \
    "https://api.hetzner.cloud/v1/servers/${SERVER_ID}" \
    | "$parser" -c "import json,sys; print(json.load(sys.stdin)['server']['public_net']['ipv4']['ip'])"
}

resolve_domain_ipv4() {
  local parser="python3"
  if ! command -v "$parser" >/dev/null 2>&1; then
    parser="python"
  fi
  if ! command -v "$parser" >/dev/null 2>&1; then
    return 1
  fi

  "$parser" - "$PUBLIC_DOMAIN" <<'PY'
import socket
import sys

domain = sys.argv[1]
ips = sorted({entry[4][0] for entry in socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)})
for ip in ips:
    print(ip)
PY
}

if [ -z "$SERVER_IP" ]; then
  SERVER_IP="$(resolve_server_ip_from_hetzner || true)"
fi

if [ -z "$SERVER_IP" ]; then
  echo "[ERROR] SERVER_IP is required."
  echo "[HINT] Set SERVER_IP explicitly or provide SERVER_ID + HETZNER_CLOUD_API_TOKEN."
  exit 1
fi

echo "========================================="
echo "Deploying Vektal to Hetzner"
echo "========================================="
echo "Server: $SERVER_IP"
echo "Repo: $REPO_PATH"
echo "Domain: $PUBLIC_DOMAIN"
echo ""

DOMAIN_IPS="$(resolve_domain_ipv4 || true)"
if [ -n "$DOMAIN_IPS" ]; then
  echo "Domain A records:"
  echo "$DOMAIN_IPS"
  if ! echo "$DOMAIN_IPS" | grep -Fxq "$SERVER_IP"; then
    if [ "$ALLOW_DOMAIN_MISMATCH" = "1" ]; then
      echo "[WARN] SERVER_IP ($SERVER_IP) does not match DNS A records for $PUBLIC_DOMAIN."
      echo "[WARN] Continuing because ALLOW_DOMAIN_MISMATCH=1."
    else
      echo "[ERROR] SERVER_IP ($SERVER_IP) does not match DNS A records for $PUBLIC_DOMAIN."
      echo "[HINT] Update DNS or use the correct SERVER_IP. Override with ALLOW_DOMAIN_MISMATCH=1 if intentional."
      exit 1
    fi
  fi
else
  echo "[WARN] Could not resolve domain A records locally; continuing."
fi

ssh root@"$SERVER_IP" \
  "REPO_PATH='$REPO_PATH' PROJECT_NAME='$PROJECT_NAME' PUBLIC_DOMAIN='$PUBLIC_DOMAIN' bash -s" <<'ENDSSH'
set -euo pipefail

echo "[1/5] Navigating to project directory..."
cd "$REPO_PATH" || { echo "Error: Project directory not found at $REPO_PATH"; exit 1; }

echo "[2/5] Pulling latest changes from GitHub..."
git fetch origin
git pull origin master

echo "[3/5] Checking deployment runtime..."
if command -v dokploy >/dev/null 2>&1; then
  echo "[4/5] Triggering Dokploy deployment..."
  dokploy deploy "$PROJECT_NAME" || dokploy deploy "${PROJECT_NAME}-frontend" || echo "Manual trigger may be needed in Dokploy UI"
elif docker compose version >/dev/null 2>&1; then
  echo "[4/5] Rebuilding gateway stack with Docker Compose..."
  docker compose pull frontend nginx backend || true
  docker compose up -d nginx backend frontend --build
else
  echo "[4/5] Manual deployment needed..."
  echo "Please trigger deployment manually from Dokploy dashboard"
fi

echo "[5/5] Checking deployment status..."
if command -v docker >/dev/null 2>&1; then
  docker compose ps nginx frontend backend || true
fi

echo "[5/5] Running local health probes..."
curl -fsS --max-time 10 http://localhost/health >/dev/null
echo "[OK] Local gateway health"
curl -fsS --max-time 10 http://localhost:3000/test >/dev/null
echo "[OK] Local frontend health"

echo "[5/5] Running public health probe with retries..."
PUBLIC_OK=0
for attempt in 1 2 3 4 5 6; do
  if curl -fsS --max-time 15 "https://$PUBLIC_DOMAIN/health" >/dev/null; then
    PUBLIC_OK=1
    break
  fi
  echo "[WARN] Public health probe failed (attempt $attempt/6). Retrying in 10s..."
  sleep 10
done

if [ "$PUBLIC_OK" -eq 1 ]; then
  echo "[OK] Public gateway health"
else
  echo "[ERROR] Public gateway health probe failed after retries."
  echo "[HINT] Check DNS records, firewall ingress on 443, and nginx status."
  exit 1
fi

echo ""
echo "========================================="
echo "Deployment commands executed"
echo "========================================="
ENDSSH

echo ""
echo "[OK] Deployment script completed"
echo "Visit: https://$PUBLIC_DOMAIN/dashboard"
