#!/bin/bash
# =============================================================================
# Mise HERo Finance - Deployment Script v2
# Called by GitHub Actions or Claude Code deploy skill
# Usage: bash deploy.sh <environment> [branch]
#   environment: test | stage | production
#   branch: git branch to deploy (auto-detected if not provided)
#
# Features:
#   - Deployment lock (prevents concurrent deploys to same environment)
#   - Automatic rollback on health check failure
#   - Pre-deploy commit saved for rollback
#   - Version verification after deploy
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
LOCK_FILE="/tmp/misehero-deploy-${ENV}.lock"
ROLLBACK_FILE="/tmp/misehero-rollback-${ENV}.txt"

# --- Lock mechanism ---
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
            echo "ERROR: Another deployment to ${ENV} is in progress (PID: ${LOCK_PID})"
            echo "If this is stale, remove: $LOCK_FILE"
            exit 1
        else
            echo "WARNING: Stale lock file found (PID ${LOCK_PID} not running). Removing."
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
    trap release_lock EXIT
}

release_lock() {
    rm -f "$LOCK_FILE"
}

# --- Rollback function ---
rollback() {
    local PREV_COMMIT="$1"
    echo ""
    echo "!!! ROLLING BACK to ${PREV_COMMIT} !!!"
    echo ""
    cd "${APP_DIR}"
    git checkout "${PREV_COMMIT}" -- .
    git checkout "${BRANCH}"
    git reset --hard "${PREV_COMMIT}"
    "${APP_DIR}/venv/bin/python" manage.py migrate --noinput 2>/dev/null || true
    sudo systemctl restart "${SERVICE_NAME}"
    sleep 3
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo "ROLLBACK SUCCESSFUL — service running on ${PREV_COMMIT}"
    else
        echo "ROLLBACK FAILED — manual intervention required!"
        sudo journalctl -u "${SERVICE_NAME}" --no-pager -n 30
    fi
}

# --- Start deployment ---
acquire_lock

echo "=========================================="
echo "Deploying ${ENV} (branch: ${BRANCH})"
echo "=========================================="

cd "${APP_DIR}"

# Save current commit for rollback
PREV_COMMIT=$(git rev-parse HEAD)
echo "${PREV_COMMIT}" > "${ROLLBACK_FILE}"
echo "Pre-deploy commit: ${PREV_COMMIT}"

# Step 1: Pull latest code
echo "[1/7] Pulling latest code..."
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

NEW_COMMIT=$(git rev-parse HEAD)
echo "New commit: ${NEW_COMMIT}"

if [ "${PREV_COMMIT}" = "${NEW_COMMIT}" ]; then
    echo "No new commits to deploy. Continuing anyway (dependencies/migrations may have changed)."
fi

# Step 2: Install/update dependencies
echo "[2/7] Installing dependencies..."
"${APP_DIR}/venv/bin/pip" install -r requirements.txt --quiet

# Step 3: Run migrations
echo "[3/7] Running migrations..."
set -a; source "${APP_DIR}/.env"; set +a
"${APP_DIR}/venv/bin/python" manage.py migrate --noinput

# Step 4: Collect static files
echo "[4/7] Collecting static files..."
"${APP_DIR}/venv/bin/python" manage.py collectstatic --noinput --clear

# Step 5: Restart service
echo "[5/7] Restarting ${SERVICE_NAME}..."
sudo systemctl restart "${SERVICE_NAME}"

# Step 6: Health check with auto-rollback
echo "[6/7] Health check..."
sleep 3

HEALTH_OK=true

if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "ERROR: Service ${SERVICE_NAME} failed to start!"
    sudo journalctl -u "${SERVICE_NAME}" --no-pager -n 30
    HEALTH_OK=false
else
    echo "Service ${SERVICE_NAME} is running"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/api/v1/" 2>/dev/null || echo "000")
    if [ "${HTTP_CODE}" = "200" ]; then
        echo "API health check PASSED (HTTP ${HTTP_CODE})"
    elif [ "${HTTP_CODE}" = "401" ] || [ "${HTTP_CODE}" = "403" ]; then
        echo "API responding (HTTP ${HTTP_CODE} — auth required, expected)"
    else
        echo "ERROR: API returned HTTP ${HTTP_CODE}"
        HEALTH_OK=false
    fi
fi

if [ "${HEALTH_OK}" = "false" ]; then
    echo ""
    echo "!!! HEALTH CHECK FAILED !!!"
    if [ "${PREV_COMMIT}" != "${NEW_COMMIT}" ]; then
        rollback "${PREV_COMMIT}"
        exit 1
    else
        echo "No commit change — skipping rollback. Check logs manually."
        exit 1
    fi
fi

# Step 7: Version verification
echo "[7/7] Version verification..."
if [ -f "${APP_DIR}/frontend/version.json" ]; then
    VERSION_INFO=$(cat "${APP_DIR}/frontend/version.json")
    echo "Deployed version: ${VERSION_INFO}"
else
    echo "WARNING: version.json not found"
fi

echo ""
echo "=========================================="
echo "Deployment of ${ENV} complete!"
echo "Commit: $(git log --oneline -1)"
echo "=========================================="
