# Mise HERo Finance - Makefile
# ==============================
# Common development commands

.PHONY: help install run migrate seed test lint clean docker-up docker-down

# Default target
help:
	@echo "Mise HERo Finance - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make migrate     - Run database migrations"
	@echo "  make seed        - Seed initial lookup data"
	@echo "  make superuser   - Create admin superuser"
	@echo ""
	@echo "Development:"
	@echo "  make run         - Start development server"
	@echo "  make shell       - Open Django shell_plus"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run code linters"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up   - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"
	@echo "  make docker-logs - View Docker logs"
	@echo ""
	@echo "Database:"
	@echo "  make dbshell     - Open PostgreSQL shell"
	@echo "  make dbreset     - Reset database (DANGER!)"
	@echo ""
	@echo "Other:"
	@echo "  make stats       - Show transaction statistics"
	@echo "  make clean       - Clean generated files"

# Setup
install:
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

seed:
	python manage.py seed_lookups
	@echo "Loading sample rules..."
	python manage.py loaddata apps/transactions/fixtures/sample_rules.json || true

superuser:
	python manage.py createsuperuser

# Development
run:
	python manage.py runserver 0.0.0.0:8000

shell:
	python manage.py shell_plus

test:
	pytest -v

test-cov:
	pytest --cov=apps --cov-report=html --cov-report=term-missing

lint:
	black --check apps/ config/
	isort --check-only apps/ config/
	flake8 apps/ config/

format:
	black apps/ config/
	isort apps/ config/

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

# Database
dbshell:
	python manage.py dbshell

dbreset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	python manage.py flush --no-input
	python manage.py migrate
	python manage.py seed_lookups

# Utilities
stats:
	python manage.py transaction_stats --by-month

import-sample:
	python manage.py import_csv docs/sample_import.csv

export:
	python manage.py export_transactions export_$(shell date +%Y%m%d).csv

collectstatic:
	python manage.py collectstatic --no-input

# Clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
