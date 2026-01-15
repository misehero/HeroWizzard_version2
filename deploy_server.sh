#!/bin/bash
# Deployment script for Mise HERo Finance on Ubuntu/Debian server
# Run this script on the DigitalOcean droplet as root

set -e

echo "=== Starting Mise HERo Finance Deployment ==="

# Update system
echo ">>> Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo ">>> Installing required packages..."
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git

# Start and enable PostgreSQL
echo ">>> Setting up PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE wizzardhero;
CREATE USER wizzardhero_user WITH PASSWORD 'WizzardHero2024!';
ALTER ROLE wizzardhero_user SET client_encoding TO 'utf8';
ALTER ROLE wizzardhero_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE wizzardhero_user SET timezone TO 'Europe/Prague';
GRANT ALL PRIVILEGES ON DATABASE wizzardhero TO wizzardhero_user;
\c wizzardhero
GRANT ALL ON SCHEMA public TO wizzardhero_user;
EOF

echo ">>> PostgreSQL database created"

# Create app directory
echo ">>> Setting up application directory..."
mkdir -p /var/www
cd /var/www

# Clone repository
if [ -d "HeroWizzard_version2" ]; then
    echo ">>> Repository exists, pulling latest..."
    cd HeroWizzard_version2
    git pull
else
    echo ">>> Cloning repository..."
    git clone https://github.com/misehero/HeroWizzard_version2.git
    cd HeroWizzard_version2
fi

# Create virtual environment
echo ">>> Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ">>> Installing Python dependencies..."
pip install --upgrade pip
pip install gunicorn
pip install -r requirements.txt

# Create production .env file
echo ">>> Creating production environment file..."
cat > .env <<EOF
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DJANGO_ALLOWED_HOSTS=46.101.121.250,localhost,127.0.0.1
POSTGRES_DB=wizzardhero
POSTGRES_USER=wizzardhero_user
POSTGRES_PASSWORD=WizzardHero2024!
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CORS_ALLOWED_ORIGINS=http://46.101.121.250,http://localhost
EOF

# Create production settings
echo ">>> Creating production settings..."
cat > config/settings_production.py <<'SETTINGS'
"""Production settings for Mise HERo Finance."""
from .settings import *
import os
from decouple import config

DEBUG = False
SECRET_KEY = config('DJANGO_SECRET_KEY')
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

STATIC_ROOT = '/var/www/HeroWizzard_version2/staticfiles'
MEDIA_ROOT = '/var/www/HeroWizzard_version2/media'

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SETTINGS

# Run migrations
echo ">>> Running database migrations..."
export DJANGO_SETTINGS_MODULE=config.settings_production
python manage.py migrate

# Collect static files
echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser
echo ">>> Creating admin user..."
python manage.py shell <<PYEOF
from apps.core.models import User
if not User.objects.filter(email='admin@misehero.cz').exists():
    User.objects.create_superuser('admin@misehero.cz', 'AdminHero2024!')
    print('Admin user created: admin@misehero.cz')
else:
    print('Admin user already exists')
PYEOF

# Seed lookup data
echo ">>> Seeding lookup data..."
python manage.py seed_lookups || echo "Seed command not found or failed"

# Create gunicorn service
echo ">>> Setting up Gunicorn systemd service..."
cat > /etc/systemd/system/herowizzard.service <<EOF
[Unit]
Description=HeroWizzard Gunicorn daemon
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/HeroWizzard_version2
Environment="DJANGO_SETTINGS_MODULE=config.settings_production"
EnvironmentFile=/var/www/HeroWizzard_version2/.env
ExecStart=/var/www/HeroWizzard_version2/venv/bin/gunicorn --workers 3 --bind unix:/var/www/HeroWizzard_version2/herowizzard.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
echo ">>> Setting file permissions..."
chown -R www-data:www-data /var/www/HeroWizzard_version2
chmod -R 755 /var/www/HeroWizzard_version2

# Start and enable gunicorn
echo ">>> Starting Gunicorn service..."
systemctl daemon-reload
systemctl start herowizzard
systemctl enable herowizzard

# Configure nginx
echo ">>> Configuring Nginx..."
cat > /etc/nginx/sites-available/herowizzard <<'NGINX'
server {
    listen 80;
    server_name 46.101.121.250;

    # Frontend demo
    location / {
        alias /var/www/HeroWizzard_version2/frontend_demo/;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://unix:/var/www/HeroWizzard_version2/herowizzard.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin
    location /admin/ {
        proxy_pass http://unix:/var/www/HeroWizzard_version2/herowizzard.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /var/www/HeroWizzard_version2/staticfiles/;
    }

    # Media files
    location /media/ {
        alias /var/www/HeroWizzard_version2/media/;
    }
}
NGINX

# Enable site
ln -sf /etc/nginx/sites-available/herowizzard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
echo ">>> Testing Nginx configuration..."
nginx -t

echo ">>> Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Application URL: http://46.101.121.250"
echo "API URL: http://46.101.121.250/api/v1/"
echo "Admin URL: http://46.101.121.250/admin/"
echo ""
echo "Admin credentials:"
echo "  Email: admin@misehero.cz"
echo "  Password: AdminHero2024!"
echo ""
echo "Database credentials:"
echo "  Database: wizzardhero"
echo "  User: wizzardhero_user"
echo "  Password: WizzardHero2024!"
echo ""
