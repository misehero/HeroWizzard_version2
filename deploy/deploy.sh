#!/bin/bash
# =============================================================================
# Mise HERo Finance - Deployment Script
# Called by GitHub Actions to deploy a specific environment
# Usage: bash deploy.sh <environment> [branch]
#   environment: test | stage | production
#   branch: git branch to deploy (auto-detected if not provided)
# =============================================================================

set -euo pipefail

ENV="${1:?Usage: deploy.sh <test|stage|production> [branch]}"
BRANCH="${2:-}"

# Validate environment
case $ENV in
    test)       APP_DIR="/var/www/misehero-test"; BRANCH="${BRANCH:-develop}"; PORT=8001 ;;
    stage)      APP_DIR="/var/www/misehero-stage"; BRANCH="${BRANCH:-stage}"; PORT=8002 ;;
    production) APP_DIR="/var/www/misehero-production"; BRANCH="${BRANCH:-production}"; PORT=8003 ;;
    *)          echo "ERROR: Invalid environment '${ENV}'. Use: test, stage, production"; exit 1 ;;
esac

SERVICE_NAME="misehero-${ENV}"

echo "=========================================="
echo "Deploying ${ENV} (branch: ${BRANCH})"
echo "=========================================="

cd "${APP_DIR}"

# Step 1: Pull latest code
echo "[1/6] Pulling latest code..."
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

# Step 2: Install/update dependencies
echo "[2/6] Installing dependencies..."
"${APP_DIR}/venv/bin/pip" install -r requirements.txt --quiet

# Step 3: Run migrations
echo "[3/6] Running migrations..."
set -a; source "${APP_DIR}/.env"; set +a
"${APP_DIR}/venv/bin/python" manage.py migrate --noinput

# Step 4: Collect static files
echo "[4/6] Collecting static files..."
"${APP_DIR}/venv/bin/python" manage.py collectstatic --noinput --clear

# Step 5: Restart service
echo "[5/6] Restarting ${SERVICE_NAME}..."
sudo systemctl restart "${SERVICE_NAME}"

# Step 6: Health check
echo "[6/6] Health check..."
sleep 3
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "Service ${SERVICE_NAME} is running"
    # Test API endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/api/v1/" 2>/dev/null || echo "000")
    if [ "${HTTP_CODE}" = "200" ]; then
        echo "API health check PASSED (HTTP ${HTTP_CODE})"
    else
        echo "WARNING: API returned HTTP ${HTTP_CODE} (may need authentication)"
    fi
else
    echo "ERROR: Service ${SERVICE_NAME} failed to start!"
    sudo journalctl -u "${SERVICE_NAME}" --no-pager -n 20
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment of ${ENV} complete!"
echo "=========================================="
