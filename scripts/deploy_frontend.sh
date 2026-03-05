#!/bin/bash
# Manual deployment script for Vektal frontend.
# Usage: ./scripts/deploy_frontend.sh [production|staging]

set -euo pipefail

ENVIRONMENT="${1:-production}"
DOCKER_TAG="vektal-frontend:${ENVIRONMENT}"
PROJECT_NAME="${PROJECT_NAME:-vektal}"
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-app.vektal.systems}"

echo "========================================="
echo "Vektal Frontend Deployment"
echo "========================================="
echo "Environment: $ENVIRONMENT"
echo "Docker Tag: $DOCKER_TAG"
echo "Domain: $PUBLIC_DOMAIN"
echo ""

echo "[1/4] Building Docker image..."
docker build -f Dockerfile.frontend -t "$DOCKER_TAG" .
echo "[OK] Docker image built successfully"
echo ""

echo "[2/4] Testing build artifacts..."
docker images | grep vektal-frontend
echo "[OK] Build artifacts verified"
echo ""

echo "[3/4] Deployment options:"
echo "Option A - Local test:"
echo "  docker run -p 3000:3000 -e NODE_ENV=production $DOCKER_TAG"
echo "  Then visit: http://localhost:3000"
echo ""
echo "Option B - Stack rollout:"
echo "  docker compose up -d nginx backend frontend --build"
echo "  curl -I https://$PUBLIC_DOMAIN/health"
echo ""
echo "Option C - Dokploy manual trigger:"
echo "  1. Log into Dokploy dashboard"
echo "  2. Select '$PROJECT_NAME' project"
echo "  3. Trigger deploy"
echo ""

if [ -n "${DOKPLOY_WEBHOOK_URL:-}" ]; then
  echo "[4/4] Triggering Dokploy webhook..."
  curl -X POST "$DOKPLOY_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{"ref":"refs/heads/master","repository":{"full_name":"x3asarc/vektal"}}'
  echo "[OK] Webhook triggered"
else
  echo "[4/4] DOKPLOY_WEBHOOK_URL not set. Skipping webhook trigger."
fi

echo ""
echo "========================================="
echo "Deployment preparation complete"
echo "========================================="