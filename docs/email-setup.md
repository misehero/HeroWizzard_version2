# Email Setup Guide — Resend (NOT YET IMPLEMENTED)

## Current State

- **Email backend:** `django.core.mail.backends.console.EmailBackend` (prints to stdout, no actual sending)
- **SMTP ports blocked:** DigitalOcean blocks outbound ports 25, 465, and 587 on all droplets at the platform level. This is not a firewall issue — UFW allows outgoing traffic, but DigitalOcean intercepts SMTP traffic to prevent spam.
- **No mail server** installed on the droplet (no Postfix, sendmail, or exim).
- **DNS:** MX records point to Google Workspace (`aspmx.l.google.com`). No SPF, DKIM, or DMARC records configured for `misehero.cz`.

## Recommended Service: Resend

[Resend](https://resend.com) uses an **HTTP API** (port 443) to send email, bypassing DigitalOcean's SMTP blocking entirely.

| Feature | Detail |
|---------|--------|
| Free tier | 3,000 emails/month |
| Protocol | HTTPS (no SMTP needed) |
| Django package | `django-resend` — drop-in `EMAIL_BACKEND` |
| Setup time | ~15 minutes |

### Why not alternatives?

- **Google Workspace relay** — requires SMTP ports (blocked).
- **SendGrid / Brevo** — heavier setup and account approval process.
- Resend is the simplest path given the constraints.

## Registration & Domain Verification

1. **Sign up** at [resend.com](https://resend.com).
2. **Add domain** `misehero.cz` in the Resend dashboard.
3. **Add DNS records** provided by Resend to your domain registrar:

   | Type | Purpose | Example |
   |------|---------|---------|
   | TXT | SPF — authorizes Resend to send on behalf of misehero.cz | `v=spf1 include:resend.com ~all` |
   | CNAME (x3) | DKIM — cryptographic signature for outgoing mail | Provided by Resend dashboard |
   | TXT | DMARC — policy for failed authentication | `v=DMARC1; p=none; rua=mailto:admin@misehero.cz` |

4. **Wait for verification** — usually takes a few minutes. Resend dashboard shows status per record.

## Django Integration

### Install the package

```bash
pip install django-resend
pip freeze > requirements.txt
```

### Set environment variables

Add to `.env` on each environment (test, stage, production):

```bash
EMAIL_BACKEND=django_resend.EmailBackend
RESEND_API_KEY=re_xxxxxxxxxxxx
DEFAULT_FROM_EMAIL=noreply@misehero.cz
```

### Update settings.py

The existing `config/settings.py` already reads `EMAIL_BACKEND` and `DEFAULT_FROM_EMAIL` from environment variables. The only addition needed is:

```python
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
```

### Test from the shell

```bash
# SSH into server, activate venv, source .env
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail("Test", "Test body", "noreply@misehero.cz", ["your-email@gmail.com"])
```

If the return value is `1`, the email was sent successfully.

## Existing Code (Already Built)

### Backend

- `ForgotPasswordView` in `apps/core/views.py` generates a random password and calls `send_mail()`.
- Falls back gracefully when email sending fails: returns `email_sent: false` with a "contact admin" message.
- Email settings in `config/settings.py` read all values from env vars, defaulting to the console backend.

### Frontend

- `frontend_demo/index.html` — "Zapomenuté heslo?" link appears after a failed login attempt.
- Pre-fills the email address from the login form.
- Handles `email_sent === false` by showing: "Kontaktujte administrátora".
- `frontend_demo/app.js` — `api.forgotPassword(email)` method calls the backend endpoint.

### Current email template (forgot password)

```
Subject: HeroWizzard - Nové heslo
Body:
  Dobrý den,
  Vaše heslo bylo resetováno.
  Nové heslo: {new_password}
  Po přihlášení si heslo můžete změnit.
  HeroWizzard
```

## Future Use Cases

Once Resend is configured, these features can be added incrementally:

- **Welcome email** — sent when an admin creates a new user account, containing login credentials.
- **Password change confirmation** — notify the user after a successful password change.
- **Import notifications** — email the accountant when a CSV import completes (with row count and any errors).
- **Admin alerts** — notify admins of unusual activity (failed logins, large imports, etc.).

## Environment Variables Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `EMAIL_BACKEND` | Yes | `django_resend.EmailBackend` | Defaults to console backend if unset |
| `RESEND_API_KEY` | Yes | `re_xxxxxxxxxxxx` | Get from Resend dashboard > API Keys |
| `DEFAULT_FROM_EMAIL` | No | `noreply@misehero.cz` | Defaults to `noreply@misehero.cz` |
