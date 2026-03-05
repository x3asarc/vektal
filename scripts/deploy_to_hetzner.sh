#!/bin/bash
# Deploy Vektal frontend to Hetzner server via SSH.
# This script updates the repo, redeploys gateway services, and validates public health.

set -euo pipefail

SERVER_IP="${SERVER_IP:-89.167.74.58}"
REPO_PATH="${REPO_PATH:-/root/vektal}"
PROJECT_NAME="${PROJECT_NAME:-vektal}"
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.vektal.systems}"

echo "========================================="
echo "Deploying Vektal to Hetzner"
echo "========================================="
echo "Server: $SERVER_IP"
echo "Repo: $REPO_PATH"
echo "Domain: $PUBLIC_DOMAIN"
echo ""

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
