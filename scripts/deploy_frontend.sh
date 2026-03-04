#!/bin/bash
# Manual deployment script for Vektal frontend
# Usage: ./scripts/deploy_frontend.sh [production|staging]

set -e

ENVIRONMENT="${1:-production}"
DOCKER_TAG="vektal-frontend:${ENVIRONMENT}"

echo "========================================="
echo "Vektal Frontend Deployment"
echo "========================================="
echo "Environment: $ENVIRONMENT"
echo "Docker Tag: $DOCKER_TAG"
echo ""

# Step 1: Build the Docker image
echo "[1/3] Building Docker image..."
docker build -f Dockerfile.frontend -t "$DOCKER_TAG" .
echo "✓ Docker image built successfully"
echo ""

# Step 2: Test the build
echo "[2/3] Testing build artifacts..."
docker images | grep vektal-frontend
echo "✓ Build artifacts verified"
echo ""

# Step 3: Deployment instructions
echo "[3/3] Deployment options:"
echo ""
echo "Option A - Local Test:"
echo "  docker run -p 3000:3000 -e NODE_ENV=production $DOCKER_TAG"
echo "  Then visit: http://localhost:3000"
echo ""
echo "Option B - Push to Registry:"
echo "  docker tag $DOCKER_TAG registry.your-server.com/vektal-frontend:latest"
echo "  docker push registry.your-server.com/vektal-frontend:latest"
echo ""
echo "Option C - Dokploy Manual Trigger:"
echo "  1. Log into Dokploy dashboard"
echo "  2. Select 'vektal' project"
echo "  3. Click 'Deploy' button"
echo ""

if [ -n "$DOKPLOY_WEBHOOK_URL" ]; then
    echo "Option D - Webhook Trigger:"
    curl -X POST "$DOKPLOY_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d '{"ref":"refs/heads/master","repository":{"full_name":"x3asarc/vektal"}}'
    echo "✓ Webhook triggered"
fi

echo ""
echo "========================================="
echo "Deployment preparation complete!"
echo "========================================="
