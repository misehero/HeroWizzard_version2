# Test Environment - Default Users & Credentials

**Environment:** TEST
**URL:** https://46.101.121.250
**Note:** Self-signed SSL certificate - browser will show a security warning, click "Advanced" > "Proceed" to continue.

---

## Test User Accounts

| Email | Password | Role | Name | Permissions |
|-------|----------|------|------|-------------|
| admin@misehero.cz | admin | Admin | Admin User | Full access: all CRUD, Django admin panel, user management |
| manager@misehero.cz | manager | Manager | Jan Novak | Import CSV, edit transactions, manage category rules, view reports |
| accountant@misehero.cz | accountant | Accountant | Eva Svobodova | Edit transactions, view reports, export data |
| viewer@misehero.cz | viewer | Viewer | Petr Dvorak | Read-only: view transactions, dashboard, reports |

---

## Role Descriptions

### Admin (admin)
- Full system access
- Access to Django admin panel at `/admin/`
- Can create/delete users
- Can manage all transactions, imports, and category rules
- Can view all reports and export data

### Manager (manager)
- Can import CSV files (Creditas, Raiffeisen, iDoklad)
- Can create, edit, and categorize transactions
- Can create and manage category rules
- Can apply rules to uncategorized transactions
- Can export transactions to Excel/CSV
- Can view dashboard and reports

### Accountant (accountant)
- Can edit and categorize existing transactions
- Can set KMEN splits (MH/SK/XP/FR percentages)
- Can view and export transactions
- Can view dashboard and reports
- Cannot import CSV files or manage category rules

### Viewer (viewer)
- Read-only access to all data
- Can view dashboard and transaction list
- Can use filters and search
- Cannot edit, create, or import anything

---

## Quick Login Test

```bash
# Test admin login
curl -sk -X POST https://46.101.121.250/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@misehero.cz","password":"admin"}'

# Test viewer login
curl -sk -X POST https://46.101.121.250/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"viewer@misehero.cz","password":"viewer"}'
```

---

## Important Notes

- These credentials are for the **TEST environment only**
- Stage and Production environments use different databases with separate user accounts
- The admin user has access to Django admin at `https://46.101.121.250/admin/`
- Passwords are intentionally simple for testing convenience
- **Do NOT use these credentials in stage or production environments**
