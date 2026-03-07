#!/bin/bash
# Find and deploy Vektal on Hetzner server

SERVER_IP="89.167.74.58"

echo "Connecting to Hetzner server to find project..."
echo ""

ssh root@$SERVER_IP << 'ENDSSH'
set -e

echo "=== Finding Vektal/Synthex project directory ==="
echo ""

# Search common locations
SEARCH_PATHS=(
    "/root/vektal"
    "/root/synthex"
    "/opt/vektal"
    "/opt/synthex"
    "/home/*/vektal"
    "/home/*/synthex"
    "/var/www/vektal"
    "/var/www/synthex"
)

PROJECT_DIR=""

for path in "${SEARCH_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "[FOUND] $path"
        PROJECT_DIR="$path"
        break
    fi
done

# If not found in common locations, search entire filesystem
if [ -z "$PROJECT_DIR" ]; then
    echo "Searching filesystem for docker-compose.yml or package.json..."
    echo ""

    # Find by docker-compose.yml with frontend service
    COMPOSE_FILES=$(find / -name "docker-compose.yml" -type f 2>/dev/null | head -5)

    for file in $COMPOSE_FILES; do
        if grep -q "frontend:" "$file" 2>/dev/null; then
            PROJECT_DIR=$(dirname "$file")
            echo "[FOUND] Project at: $PROJECT_DIR"
            break
        fi
    done
fi

if [ -z "$PROJECT_DIR" ]; then
    echo "[ERROR] Could not find project directory!"
    echo ""
    echo "Please manually locate your project directory"
    echo "Common commands to explore:"
    echo "  ls -la /root/"
    echo "  ls -la /opt/"
    echo "  docker ps"
    exit 1
fi

echo ""
echo "=== Project found at: $PROJECT_DIR ==="
echo ""

# Show current git status
cd "$PROJECT_DIR" || exit 1
echo "[Current Status]"
echo "Git branch: $(git branch --show-current 2>/dev/null || echo 'Not a git repo')"
echo "Last commit: $(git log -1 --oneline 2>/dev/null || echo 'N/A')"
echo ""

# Ask user if they want to deploy
echo "=== Ready to deploy ==="
echo ""
echo "Commands to run:"
echo "  cd $PROJECT_DIR"
echo "  git pull origin master"
echo "  docker compose up -d frontend --build"
echo ""
echo "Do you want to continue? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "[1/3] Pulling latest changes..."
    git pull origin master

    echo ""
    echo "[2/3] Rebuilding frontend..."
    docker compose up -d frontend --build

    echo ""
    echo "[3/3] Checking status..."
    docker ps | grep frontend

    echo ""
    echo "========================================="
    echo "Deployment complete!"
    echo "Visit: https://app.vektal.systems/dashboard"
    echo "Hard refresh: Ctrl+Shift+R"
    echo "========================================="
else
    echo "Deployment cancelled. Project location: $PROJECT_DIR"
fi

ENDSSH
