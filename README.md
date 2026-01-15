# Mise HERo Finance

Finanční aplikace pro správu transakcí organizace Mise HERo.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (for frontend)

### Local Development Setup

1. **Clone and setup environment:**

```bash
cd mise_hero_finance
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. **Setup database:**

```bash
# Create PostgreSQL database
createdb mise_hero_finance

# Run migrations
python manage.py migrate

# Seed initial lookup data
python manage.py seed_lookups

# Create admin user
python manage.py createsuperuser
```

4. **Run the server:**

```bash
python manage.py runserver
```

### Using Docker

```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Authentication

The API uses JWT (JSON Web Tokens) for authentication.

**Login:**
```bash
POST /api/v1/auth/token/
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response:**
```json
{
    "access": "eyJ...",
    "refresh": "eyJ...",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "role": "accountant"
    }
}
```

**Use token in requests:**
```bash
Authorization: Bearer <access_token>
```

### API Endpoints

#### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/transactions/` | List transactions (paginated) |
| GET | `/api/v1/transactions/{id}/` | Get transaction detail |
| PATCH | `/api/v1/transactions/{id}/` | Update transaction |
| POST | `/api/v1/transactions/bulk_update/` | Bulk update transactions |
| GET | `/api/v1/transactions/stats/` | Get statistics |
| GET | `/api/v1/transactions/trends/` | Get monthly trends |
| GET | `/api/v1/transactions/export/` | Export to CSV |

**Filtering options:**
- `date_from`, `date_to` - Date range
- `amount_min`, `amount_max` - Amount range
- `status` - Transaction status
- `prijem_vydaj` - P (income) / V (expense)
- `projekt` - Project ID
- `produkt` - Product ID
- `search` - Full-text search
- `is_categorized` - Boolean

#### CSV Import

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/imports/upload/` | Upload CSV file |
| GET | `/api/v1/imports/` | List import batches |
| GET | `/api/v1/imports/{id}/` | Get batch details |
| GET | `/api/v1/imports/{id}/transactions/` | Get batch transactions |

#### Category Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/category-rules/` | List rules |
| POST | `/api/v1/category-rules/` | Create rule |
| PATCH | `/api/v1/category-rules/{id}/` | Update rule |
| DELETE | `/api/v1/category-rules/{id}/` | Delete rule |
| POST | `/api/v1/category-rules/{id}/test/` | Test rule |
| POST | `/api/v1/category-rules/apply_to_uncategorized/` | Apply all rules |

#### Lookup Data

| Endpoint | Description |
|----------|-------------|
| `/api/v1/projects/` | Project lookup |
| `/api/v1/products/` | Product lookup (with subgroups) |
| `/api/v1/subgroups/` | Product subgroups |
| `/api/v1/cost-details/` | Cost type/detail lookup |

#### Users (Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/` | List users |
| POST | `/api/v1/users/` | Create user |
| GET | `/api/v1/auth/me/` | Current user profile |
| POST | `/api/v1/auth/change-password/` | Change password |

## 🗄️ Data Structure

### Transaction Fields

**22 Bank Columns (from CSV import, read-only):**
- `datum`, `ucet`, `typ`, `poznamka_zprava`, `variabilni_symbol`, `castka`
- `datum_zauctovani`, `cislo_protiuctu`, `nazev_protiuctu`, `typ_transakce`
- `konstantni_symbol`, `specificky_symbol`, `puvodni_castka`, `puvodni_mena`
- `poplatky`, `id_transakce`, `vlastni_poznamka`, `nazev_merchanta`
- `mesto`, `mena`, `banka_protiuctu`, `reference`

**14 App Columns (user-managed):**
- `status` - Importováno, Zpracováno, Schváleno, Upraveno, Chyba
- `prijem_vydaj` - P (Příjem) / V (Výdaj)
- `vlastni_nevlastni` - V (Vlastní) / N (Nevlastní) / — 
- `dane` - Boolean
- `druh` - Fixní, Variabilní, Mzdy, etc.
- `detail` - Free text detail
- `kmen` - MH, ŠK, XP, FR
- `mh_pct`, `sk_pct`, `xp_pct`, `fr_pct` - KMEN % split (must sum to 100)
- `projekt` - FK to Project
- `produkt` - FK to Product
- `podskupina` - FK to ProductSubgroup

### Auto-Detection Rules

Rules are applied in priority order with hierarchy:
1. **Protiúčet** (counterparty account number)
2. **Merchant** (merchant name)
3. **Keyword** (regex/contains match on description fields)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test file
pytest apps/transactions/tests/test_transactions.py

# Run marked tests
pytest -m "not slow"
```

## 📁 Project Structure

```
mise_hero_finance/
├── config/                     # Django configuration
│   ├── settings.py            # Main settings
│   ├── urls.py                # Root URL config
│   └── wsgi.py
├── apps/
│   ├── core/                  # Users, auth, audit
│   │   ├── models.py         # User, AuditLog
│   │   ├── views.py          # Auth endpoints
│   │   ├── serializers.py
│   │   └── permissions.py
│   ├── transactions/          # Main business logic
│   │   ├── models.py         # Transaction, Project, Product, etc.
│   │   ├── views.py          # API ViewSets
│   │   ├── serializers.py
│   │   ├── services.py       # TransactionImporter
│   │   ├── filters.py        # Query filters
│   │   └── tests/
│   ├── analytics/            # Reports (future)
│   └── predictions/          # ML forecasting (future)
├── frontend/                  # React app (separate)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

## 🔐 User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access to everything |
| `manager` | Manage rules, users, approve transactions |
| `accountant` | Import, categorize, export transactions |
| `viewer` | Read-only access |

## 🇨🇿 Czech Localization

- Language: Czech (`cs`)
- Timezone: Europe/Prague
- CSV format: Semicolon delimiter, Czech number format (1 234,56)
- Date format: DD.MM.YYYY

## License

Proprietary - Mise HERo © 2024
