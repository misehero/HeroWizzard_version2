# Windows 11 Local Testing Guide - Mise HERo Finance

Complete guide for setting up and testing the Django project locally on Windows 11.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Database Setup](#database-setup)
4. [Environment Configuration](#environment-configuration)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Verification Steps](#verification-steps)
8. [Troubleshooting](#troubleshooting)
9. [Alternative: Docker Setup](#alternative-docker-setup)

---

## Prerequisites

### Required Software

1. **Python 3.11 or higher**

   - Download from: https://www.python.org/downloads/
   - ⚠️ **Important**: During installation, check "Add Python to PATH"
   - Verify installation:
     ```cmd
     python --version
     ```

2. **PostgreSQL 14 or higher**

   - Download from: https://www.postgresql.org/download/windows/
   - During installation:
     - Remember the password you set for the `postgres` user
     - Default port: 5432
     - Install pgAdmin 4 (included) for database management
   - Verify installation:
     ```cmd
     psql --version
     ```

3. **Git for Windows** (if not already installed)

   - Download from: https://git-scm.com/download/win
   - Use default settings during installation

4. **Node.js 18+ (Optional - for frontend)**
   - Download from: https://nodejs.org/
   - Only needed if you plan to run the React frontend

### Optional Tools

- **Visual Studio Code**: Recommended IDE
- **Windows Terminal**: Better terminal experience
- **Docker Desktop**: For containerized setup (alternative method)

---

## Installation Steps

### Step 1: Clone the Repository (if needed)

```cmd
cd C:\MiseHero
git clone <repository-url> HeroWizzard_version2
cd HeroWizzard_version2
```

### Step 2: Create Python Virtual Environment

```cmd
python -m venv venv
```

### Step 3: Activate Virtual Environment

```cmd
venv\Scripts\activate
```

You should see `(venv)` prefix in your command prompt.

### Step 4: Install Python Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:

- Django 5.0+
- Django REST Framework
- PostgreSQL adapter (psycopg2-binary)
- JWT authentication
- Testing tools (pytest, pytest-django, factory-boy)
- Data processing (pandas, openpyxl)
- Code quality tools (black, isort, flake8)

---

## Database Setup

### Step 1: Create PostgreSQL Database

**Option A: Using pgAdmin 4**

1. Open pgAdmin 4
2. Connect to PostgreSQL server (localhost)
3. Right-click "Databases" → "Create" → "Database"
4. Database name: `mise_hero_finance`
5. Owner: `postgres`
6. Click "Save"

**Option B: Using Command Line**

```cmd
psql -U postgres
```

Enter your PostgreSQL password, then:

```sql
CREATE DATABASE mise_hero_finance;
\q
```

### Step 2: Verify Database Connection

Test connection with psql:

```cmd
psql -U postgres -d mise_hero_finance
```

If successful, you'll see the PostgreSQL prompt. Type `\q` to exit.

---

## Environment Configuration

### Step 1: Create Environment File

Copy the example environment file:

```cmd
copy .env.example .env
```

### Step 2: Edit `.env` File

Open `.env` in your text editor and configure:

```env
# Django Settings
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-super-secret-key-change-in-production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Database
POSTGRES_DB=mise_hero_finance
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

⚠️ **Important**: Replace `your_postgres_password_here` with your actual PostgreSQL password.

### Step 3: Run Database Migrations

```cmd
python manage.py migrate
```

This creates all necessary database tables.

### Step 4: Seed Initial Data

```cmd
python manage.py seed_lookups
```

This loads initial lookup data (projects, products, cost details).

### Step 5: Create Admin User

```cmd
python manage.py createsuperuser
```

Follow the prompts to create an admin account:

- Email: your-email@example.com
- Password: (enter a secure password)
- Confirm password

---

## Running the Application

### Start Development Server

```cmd
python manage.py runserver
```

The server will start at: **http://localhost:8000**

### Access Points

1. **API Root**: http://localhost:8000/api/v1/
2. **Admin Panel**: http://localhost:8000/admin/
3. **API Documentation**: Available through browsable API when logged in

### Keep Server Running

Leave this terminal window open. Open a new terminal for running tests.

---

## Testing

### Activate Virtual Environment (in new terminal)

```cmd
cd C:\MiseHero\HeroWizzard_version2
venv\Scripts\activate
```

### Run All Tests

```cmd
pytest
```

### Run Tests with Verbose Output

```cmd
pytest -v
```

### Run Tests with Coverage Report

```cmd
pytest --cov=apps --cov-report=html --cov-report=term-missing
```

Coverage report will be generated in `htmlcov/index.html`

### Run Specific Test File

```cmd
pytest apps/transactions/tests/test_transactions.py
```

### Run Tests by Marker

```cmd
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

### Run Tests with Output

```cmd
pytest -v --tb=short
```

### Test Configuration

Tests are configured in:

- [`pytest.ini`](pytest.ini:1) - Pytest settings
- [`conftest.py`](conftest.py:1) - Shared fixtures

Available fixtures:

- `api_client` - REST API client
- `user` - Regular user
- `admin_user` - Admin user
- `authenticated_client` - Authenticated API client
- `admin_client` - Admin-authenticated client

---

## Verification Steps

### 1. Verify Database Connection

```cmd
python manage.py dbshell
```

Should open PostgreSQL shell. Type `\dt` to list tables, then `\q` to exit.

### 2. Verify Django Installation

```cmd
python manage.py check
```

Should show: "System check identified no issues (0 silenced)."

### 3. Verify API Endpoints

With server running, visit:

- http://localhost:8000/api/v1/
- Should see API root with available endpoints

### 4. Verify Admin Panel

1. Go to: http://localhost:8000/admin/
2. Login with superuser credentials
3. You should see:
   - Users
   - Transactions
   - Projects
   - Products
   - Category Rules

### 5. Test API Authentication

```cmd
curl -X POST http://localhost:8000/api/v1/auth/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"your-email@example.com\",\"password\":\"your-password\"}"
```

Should return JWT tokens.

### 6. Run Sample Import (Optional)

```cmd
python manage.py import_csv docs/sample_import.csv
```

### 7. View Transaction Statistics

```cmd
python manage.py transaction_stats --by-month
```

---

## Troubleshooting

### Issue: "python: command not found"

**Solution**: Python not in PATH

```cmd
# Use full path
C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\python.exe --version

# Or add to PATH via System Environment Variables
```

### Issue: "psycopg2 installation failed"

**Solution**: Install Visual C++ Build Tools

1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++"
3. Retry: `pip install psycopg2-binary`

### Issue: "could not connect to server: Connection refused"

**Solution**: PostgreSQL not running

```cmd
# Check PostgreSQL service
services.msc
# Find "postgresql-x64-14" and start it
```

Or restart via pgAdmin 4.

### Issue: "FATAL: password authentication failed"

**Solution**: Check PostgreSQL credentials in `.env`

- Verify `POSTGRES_PASSWORD` matches your PostgreSQL password
- Try connecting with psql to confirm credentials

### Issue: "Port 8000 already in use"

**Solution**: Kill existing process or use different port

```cmd
# Use different port
python manage.py runserver 8001

# Or find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### Issue: "No module named 'apps'"

**Solution**: Ensure you're in project root directory

```cmd
cd C:\MiseHero\HeroWizzard_version2
python manage.py runserver
```

### Issue: Tests fail with database errors

**Solution**: Use test database

```cmd
# Django automatically creates test database
# Ensure PostgreSQL user has CREATE DATABASE permission

# Grant permission in psql:
psql -U postgres
ALTER USER postgres CREATEDB;
\q
```

### Issue: "ModuleNotFoundError" when running tests

**Solution**: Reinstall dependencies

```cmd
pip install -r requirements.txt --force-reinstall
```

### Issue: Line ending problems (Git)

**Solution**: Configure Git for Windows

```cmd
git config --global core.autocrlf true
```

### Issue: Permission denied on venv\Scripts\activate

**Solution**: Enable script execution in PowerShell

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
venv\Scripts\Activate.ps1
```

---

## Alternative: Docker Setup

If you prefer containerized development:

### Prerequisites

- Docker Desktop for Windows
- WSL 2 (Windows Subsystem for Linux)

### Setup Steps

1. **Install Docker Desktop**

   - Download from: https://www.docker.com/products/docker-desktop/
   - Enable WSL 2 backend during installation

2. **Start Docker Containers**

   ```cmd
   docker-compose up -d
   ```

3. **Verify Containers Running**

   ```cmd
   docker-compose ps
   ```

4. **View Logs**

   ```cmd
   docker-compose logs -f backend
   ```

5. **Access Application**

   - API: http://localhost:8000
   - Database: localhost:5432

6. **Run Migrations in Container**

   ```cmd
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py seed_lookups
   docker-compose exec backend python manage.py createsuperuser
   ```

7. **Run Tests in Container**

   ```cmd
   docker-compose exec backend pytest
   ```

8. **Stop Containers**
   ```cmd
   docker-compose down
   ```

### Docker Benefits

- ✅ No need to install PostgreSQL locally
- ✅ Consistent environment across machines
- ✅ Easy cleanup and reset
- ✅ Includes Redis for caching

### Docker Drawbacks

- ❌ Slower on Windows (WSL 2 overhead)
- ❌ More complex debugging
- ❌ Requires Docker Desktop license for business use

---

## Quick Reference Commands

### Virtual Environment

```cmd
# Activate
venv\Scripts\activate

# Deactivate
deactivate
```

### Django Management

```cmd
# Run server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Enhanced shell (with django-extensions)
python manage.py shell_plus

# Database shell
python manage.py dbshell
```

### Testing

```cmd
# All tests
pytest

# Verbose
pytest -v

# With coverage
pytest --cov=apps --cov-report=html

# Specific file
pytest apps/transactions/tests/test_transactions.py

# Skip slow tests
pytest -m "not slow"
```

### Code Quality

```cmd
# Format code
black apps/ config/
isort apps/ config/

# Check formatting
black --check apps/ config/
isort --check-only apps/ config/

# Lint
flake8 apps/ config/
```

### Database

```cmd
# Reset database (DANGER!)
python manage.py flush --no-input
python manage.py migrate
python manage.py seed_lookups

# Export transactions
python manage.py export_transactions export.csv

# Import CSV
python manage.py import_csv path/to/file.csv

# Transaction statistics
python manage.py transaction_stats --by-month
```

---

## Project Structure Reference

```
HeroWizzard_version2/
├── config/                 # Django configuration
│   ├── settings.py        # Main settings (uses .env)
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI application
├── apps/
│   ├── core/              # Users, authentication, audit
│   ├── transactions/      # Main business logic
│   ├── analytics/         # Reports (future)
│   └── predictions/       # ML forecasting (future)
├── tests/                 # Test files
├── docs/                  # Documentation
├── logs/                  # Application logs
├── media/                 # Uploaded files
├── static/                # Static files
├── templates/             # HTML templates
├── .env                   # Environment variables (create from .env.example)
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── conftest.py            # Pytest fixtures
└── docker-compose.yml     # Docker configuration
```

---

## Next Steps

After successful setup:

1. **Explore the Admin Panel**

   - Create projects, products, and category rules
   - Import sample transactions

2. **Test API Endpoints**

   - Use Postman or curl to test endpoints
   - Review API documentation in browsable API

3. **Run the Frontend** (if available)

   ```cmd
   cd frontend
   npm install
   npm run dev
   ```

4. **Import Real Data**

   - Prepare CSV file in correct format (see `docs/sample_import.csv`)
   - Import via admin panel or management command

5. **Configure Category Rules**
   - Create auto-categorization rules
   - Test rules on uncategorized transactions

---

## Support & Resources

- **Project README**: [`README.md`](../README.md)
- **Django Documentation**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **PostgreSQL Windows**: https://www.postgresql.org/docs/current/tutorial-install.html

---

## Summary Checklist

- [ ] Python 3.11+ installed and in PATH
- [ ] PostgreSQL 14+ installed and running
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements.txt
- [ ] PostgreSQL database created
- [ ] `.env` file configured with correct credentials
- [ ] Database migrations applied
- [ ] Initial lookup data seeded
- [ ] Superuser created
- [ ] Development server starts successfully
- [ ] Tests run successfully
- [ ] Admin panel accessible
- [ ] API endpoints responding

Once all items are checked, your local development environment is ready! 🎉
