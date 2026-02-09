#!/bin/bash
# =============================================================================
# Mise HERo Finance - Server Setup Script
# Sets up 3 isolated environments (test, stage, production) on a single droplet
# Run as root on a fresh Ubuntu 24.04 droplet
# Usage: bash setup_server.sh
# =============================================================================

set -euo pipefail

DOMAIN_BASE="${DOMAIN_BASE:-misehero.cz}"
DROPLET_IP="46.101.121.250"
REPO_URL="https://github.com/misehero/HeroWizzard_version2.git"
DEPLOY_USER="deploy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Step 1: System packages
# =============================================================================
log_info "Installing system packages..."
apt-get update
apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    git curl build-essential \
    supervisor

# =============================================================================
# Step 2: PostgreSQL - create 3 databases + users
# =============================================================================
log_info "Setting up PostgreSQL databases..."

for ENV in test stage production; do
    DB_NAME="misehero_${ENV}"
    DB_USER="misehero_${ENV}_user"
    DB_PASS_VAR="POSTGRES_PASSWORD_$(echo $ENV | tr '[:lower:]' '[:upper:]')"
    DB_PASS="${!DB_PASS_VAR:-MiseHero_${ENV}_2026!}"

    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

    log_info "  Database '${DB_NAME}' ready (user: ${DB_USER})"
done

# =============================================================================
# Step 3: Create directory structure for 3 environments
# =============================================================================
log_info "Creating directory structure..."

for ENV in test stage production; do
    APP_DIR="/var/www/misehero-${ENV}"
    mkdir -p "${APP_DIR}"

    if [ ! -d "${APP_DIR}/.git" ]; then
        git clone "${REPO_URL}" "${APP_DIR}"
    fi

    # Set branch per environment
    case $ENV in
        test)       BRANCH="develop" ;;
        stage)      BRANCH="stage" ;;
        production) BRANCH="production" ;;
    esac

    cd "${APP_DIR}"
    git fetch origin
    git checkout "${BRANCH}"
    git pull origin "${BRANCH}"

    # Create Python virtual environment
    if [ ! -d "${APP_DIR}/venv" ]; then
        python3 -m venv "${APP_DIR}/venv"
    fi
    "${APP_DIR}/venv/bin/pip" install --upgrade pip
    "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

    # Create necessary directories
    mkdir -p "${APP_DIR}/staticfiles" "${APP_DIR}/media" "${APP_DIR}/logs"

    # Set ownership
    chown -R ${DEPLOY_USER}:${DEPLOY_USER} "${APP_DIR}"

    log_info "  Environment '${ENV}' set up at ${APP_DIR} (branch: ${BRANCH})"
done

# =============================================================================
# Step 4: Create .env files for each environment
# =============================================================================
log_info "Creating environment files..."

for ENV in test stage production; do
    APP_DIR="/var/www/misehero-${ENV}"
    DB_NAME="misehero_${ENV}"
    DB_USER="misehero_${ENV}_user"
    DB_PASS_VAR="POSTGRES_PASSWORD_$(echo $ENV | tr '[:lower:]' '[:upper:]')"
    DB_PASS="${!DB_PASS_VAR:-MiseHero_${ENV}_2026!}"
    SECRET_KEY_VAR="DJANGO_SECRET_KEY_$(echo $ENV | tr '[:lower:]' '[:upper:]')"
    SECRET_KEY="${!SECRET_KEY_VAR:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')}"

    case $ENV in
        test)       PORT=8001; SUBDOMAIN="test" ;;
        stage)      PORT=8002; SUBDOMAIN="stage" ;;
        production) PORT=8003; SUBDOMAIN="app" ;;
    esac

    cat > "${APP_DIR}/.env" << ENVEOF
# Mise HERo Finance - ${ENV} environment
DJANGO_DEBUG=$([ "$ENV" = "test" ] && echo "True" || echo "False")
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_ALLOWED_HOSTS=${SUBDOMAIN}.${DOMAIN_BASE},${DROPLET_IP},localhost,127.0.0.1
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CORS_ALLOWED_ORIGINS=https://${SUBDOMAIN}.${DOMAIN_BASE},http://${SUBDOMAIN}.${DOMAIN_BASE},http://${DROPLET_IP}:${PORT}
GUNICORN_PORT=${PORT}
ENVEOF

    chown ${DEPLOY_USER}:${DEPLOY_USER} "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"

    log_info "  .env created for ${ENV} (port ${PORT})"
done

# =============================================================================
# Step 5: Create systemd services for Gunicorn
# =============================================================================
log_info "Creating systemd services..."

for ENV in test stage production; do
    APP_DIR="/var/www/misehero-${ENV}"

    case $ENV in
        test)       PORT=8001 ;;
        stage)      PORT=8002 ;;
        production) PORT=8003 ;;
    esac

    # Gunicorn workers: 2 * CPU + 1, but limit for 2GB RAM droplet
    WORKERS=2

    cat > "/etc/systemd/system/misehero-${ENV}.service" << SVCEOF
[Unit]
Description=Mise HERo Finance - ${ENV}
After=network.target postgresql.service

[Service]
Type=notify
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn \
    --bind 127.0.0.1:${PORT} \
    --workers ${WORKERS} \
    --timeout 120 \
    --access-logfile ${APP_DIR}/logs/gunicorn-access.log \
    --error-logfile ${APP_DIR}/logs/gunicorn-error.log \
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable "misehero-${ENV}"

    log_info "  Service misehero-${ENV} created (port ${PORT})"
done

# =============================================================================
# Step 6: Nginx configuration for 3 environments
# =============================================================================
log_info "Configuring Nginx..."

# Remove default site
rm -f /etc/nginx/sites-enabled/default

for ENV in test stage production; do
    APP_DIR="/var/www/misehero-${ENV}"

    case $ENV in
        test)       PORT=8001; SUBDOMAIN="test"; SERVER_NAME="test.${DOMAIN_BASE} ${DROPLET_IP}" ;;
        stage)      PORT=8002; SUBDOMAIN="stage"; SERVER_NAME="stage.${DOMAIN_BASE}" ;;
        production) PORT=8003; SUBDOMAIN="app"; SERVER_NAME="app.${DOMAIN_BASE} ${DOMAIN_BASE}" ;;
    esac

    cat > "/etc/nginx/sites-available/misehero-${ENV}" << NGXEOF
server {
    listen 80;
    server_name ${SERVER_NAME};

    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias ${APP_DIR}/media/;
        expires 7d;
    }

    # API - proxy to Gunicorn
    location /api/ {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    # Django admin
    location /admin/ {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Frontend (static HTML)
    location / {
        alias ${APP_DIR}/frontend_demo/;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
NGXEOF

    ln -sf "/etc/nginx/sites-available/misehero-${ENV}" "/etc/nginx/sites-enabled/"
    log_info "  Nginx config for ${ENV} (${SERVER_NAME})"
done

nginx -t && systemctl reload nginx
log_info "Nginx configured and reloaded"

# =============================================================================
# Step 7: Run migrations and collect static for each environment
# =============================================================================
log_info "Running migrations and collecting static files..."

for ENV in test stage production; do
    APP_DIR="/var/www/misehero-${ENV}"

    cd "${APP_DIR}"
    sudo -u ${DEPLOY_USER} bash -c "
        set -a; source ${APP_DIR}/.env; set +a
        ${APP_DIR}/venv/bin/python manage.py migrate --noinput
        ${APP_DIR}/venv/bin/python manage.py collectstatic --noinput --clear
        ${APP_DIR}/venv/bin/python manage.py seed_lookups 2>/dev/null || true
    "

    log_info "  Migrations and static files done for ${ENV}"
done

# =============================================================================
# Step 8: Start all services
# =============================================================================
log_info "Starting all services..."

for ENV in test stage production; do
    systemctl start "misehero-${ENV}"
    log_info "  misehero-${ENV} started"
done

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================"
echo "  Mise HERo Finance - Setup Complete!"
echo "============================================"
echo ""
echo "Environments:"
echo "  TEST:       http://${DROPLET_IP} (port 8001, branch: develop)"
echo "  STAGE:      http://stage.${DOMAIN_BASE} (port 8002, branch: stage)"
echo "  PRODUCTION: http://app.${DOMAIN_BASE} (port 8003, branch: production)"
echo ""
echo "Services:"
echo "  systemctl status misehero-test"
echo "  systemctl status misehero-stage"
echo "  systemctl status misehero-production"
echo ""
echo "Logs:"
echo "  /var/www/misehero-{test,stage,production}/logs/"
echo ""
echo "Next steps:"
echo "  1. Point DNS records to ${DROPLET_IP}"
echo "  2. Run: certbot --nginx (for SSL certificates)"
echo "  3. Create admin users for each environment"
echo "============================================"
