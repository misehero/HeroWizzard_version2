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
