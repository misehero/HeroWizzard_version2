# ✅ Mise HERo Finance - Setup Complete!

## 🎉 Your Django Application is Running!

The application has been successfully set up and is now running on your Windows 11 machine using Docker.

---

## 🌐 Access the Application

### API Endpoints

- **API Root**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: Available through browsable API (when logged in)

### Database

- **PostgreSQL**: Running on localhost:5432
- **Redis**: Running on localhost:6379

---

## 🔑 Create Your Admin Account

**IMPORTANT:** You need to create a superuser account to access the admin panel.

Open a new terminal and run:

```cmd
docker-compose exec backend python manage.py createsuperuser
```

You'll be prompted to enter:

- **Email**: (e.g., admin@misehero.cz)
- **Password**: (choose a secure password)
- **Password confirmation**: (re-enter password)

---

## 📊 What's Already Set Up

✅ **Docker containers running:**

- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Django backend (port 8000)

✅ **Database migrations applied:**

- User authentication system
- Transaction models
- Lookup tables (Projects, Products, etc.)
- Category rules system
- Import batch tracking

✅ **Initial data seeded:**

- 10 Projects (4CFuture, POLCOM, GAP, etc.)
- 4 Products (ŠKOLY and FIRMY categories)
- 17 Product subgroups
- 10 Cost detail types

---

## 🚀 Quick Start Guide

### 1. Create Superuser (Required)

```cmd
docker-compose exec backend python manage.py createsuperuser
```

### 2. Access Admin Panel

1. Open browser: http://localhost:8000/admin/
2. Login with your superuser credentials
3. Explore the admin interface

### 3. Test API Endpoints

Open browser: http://localhost:8000/api/v1/

You'll see available endpoints:

- `/api/v1/auth/token/` - Login
- `/api/v1/transactions/` - Transactions
- `/api/v1/projects/` - Projects
- `/api/v1/products/` - Products
- `/api/v1/category-rules/` - Auto-categorization rules

### 4. Get API Token (for testing)

```cmd
curl -X POST http://localhost:8000/api/v1/auth/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"your-email@example.com\",\"password\":\"your-password\"}"
```

---

## 🛠️ Common Commands

### Container Management

```cmd
# View running containers
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop containers
docker-compose down

# Start containers
docker-compose up -d

# Restart containers
docker-compose restart
```

### Django Management

```cmd
# Run any Django command
docker-compose exec backend python manage.py <command>

# Examples:
docker-compose exec backend python manage.py shell
docker-compose exec backend python manage.py dbshell
docker-compose exec backend python manage.py transaction_stats
```

### Database Operations

```cmd
# Create new migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Seed lookup data again
docker-compose exec backend python manage.py seed_lookups
```

### Import Sample Data

```cmd
# Import CSV file
docker-compose exec backend python manage.py import_csv docs/sample_import.csv
```

---

## 🧪 Running Tests

```cmd
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=apps --cov-report=html

# Run specific test file
docker-compose exec backend pytest apps/transactions/tests/test_transactions.py
```

---

## 📁 Project Structure

```
HeroWizzard_version2/
├── apps/
│   ├── core/              # User authentication & audit
│   ├── transactions/      # Main business logic
│   ├── analytics/         # Reports (future)
│   └── predictions/       # ML forecasting (future)
├── config/                # Django settings
├── docs/                  # Documentation & samples
├── plans/                 # Setup guides
├── docker-compose.yml     # Docker configuration
└── requirements.txt       # Python dependencies
```

---

## 🔍 Verify Everything Works

### 1. Check Container Status

```cmd
docker-compose ps
```

All three containers should show "Up" status.

### 2. Check API Root

Open: http://localhost:8000/api/v1/
Should see JSON response with available endpoints.

### 3. Check Admin Panel

Open: http://localhost:8000/admin/
Should see Django admin login page.

### 4. Check Database

```cmd
docker-compose exec backend python manage.py dbshell
```

Type `\dt` to list tables, then `\q` to exit.

---

## 📚 Next Steps

1. **Create your superuser account** (see above)
2. **Login to admin panel** and explore the interface
3. **Import sample transactions** from `docs/sample_import.csv`
4. **Create category rules** for auto-categorization
5. **Test API endpoints** using Postman or curl
6. **Review documentation** in `plans/WINDOWS_11_LOCAL_TESTING_GUIDE.md`

---

## 🆘 Troubleshooting

### Container won't start

```cmd
docker-compose down
docker-compose up -d --build
```

### Database connection issues

```cmd
docker-compose restart db
docker-compose restart backend
```

### View detailed logs

```cmd
docker-compose logs -f
```

### Reset everything (DANGER - deletes all data!)

```cmd
docker-compose down -v
docker-compose up -d --build
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_lookups
docker-compose exec backend python manage.py createsuperuser
```

---

## 📖 Documentation

- **Full Setup Guide**: `plans/WINDOWS_11_LOCAL_TESTING_GUIDE.md`
- **Project README**: `README.md`
- **API Documentation**: Available in browsable API at http://localhost:8000/api/v1/

---

## 🎯 Summary

Your Mise HERo Finance application is now:

- ✅ Running on Docker
- ✅ Database configured and migrated
- ✅ Initial data seeded
- ✅ Accessible at http://localhost:8000

**Next action required:** Create your superuser account to start using the application!

```cmd
docker-compose exec backend python manage.py createsuperuser
```

Then open http://localhost:8000/admin/ in your browser (Firefox or Chrome) and login!

---

## 💡 Tips

- Keep the Docker containers running while you work
- Use `docker-compose logs -f backend` to monitor server activity
- The database persists even when containers are stopped
- Use `docker-compose down -v` only if you want to completely reset

**Enjoy using Mise HERo Finance! 🚀**
