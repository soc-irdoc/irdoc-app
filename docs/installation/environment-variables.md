# Environment Variables

All configuration is provided via environment variables in the `.env` file.
Copy `.env.example` to `.env` and edit before starting the stack.

---

## Required

| Variable | Description |
|---|---|
| `DB_PASSWORD` | PostgreSQL password. Use a strong random value. |
| `DATABASE_URL` | Full PostgreSQL connection string. Must match `DB_PASSWORD`. |
| `REDIS_PASSWORD` | Redis password. Use a strong random value. |
| `REDIS_URL` | Full Redis connection string. Must match `REDIS_PASSWORD`. |
| `SECRET_KEY` | JWT and token signing key. Generate: `openssl rand -hex 32`. **Never reuse across environments.** |
| `BASE_URL` | Public URL of your deployment, no trailing slash. E.g. `https://irdoc.example.com` |

---

## Auth / Session

| Variable | Default | Description |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime (HttpOnly cookie). |

---

## Application

| Variable | Default | Description |
|---|---|---|
| `ALLOW_REGISTRATION` | `true` | Set to `false` in production — require admin invites instead. |
| `LICENSE_KEY` | _(empty)_ | Commercial license key. Leave empty for AGPL core features only. |
| `MSSP_MODE` | `false` | Enable MSSP multi-tenant mode (premium). |

---

## Storage

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | Initial storage backend. Cloud backends are configured via the admin panel. |
| `STORAGE_PATH` | `/app/storage` | Path for local storage inside the container. Mount a host volume here. |

---

## Email

| Variable | Default | Description |
|---|---|---|
| `EMAIL_BACKEND` | `console` | `console` (log to stdout) or `smtp` (send real emails). |
| `EMAIL_FROM` | `noreply@localhost` | From address for invite and notification emails. |
| `SMTP_HOST` | _(empty)_ | SMTP server hostname. |
| `SMTP_PORT` | `587` | SMTP server port. |
| `SMTP_USER` | _(empty)_ | SMTP authentication username. |
| `SMTP_PASSWORD` | _(empty)_ | SMTP authentication password. |
| `SMTP_TLS` | `true` | Use STARTTLS. |

---

## AI (Premium)

| Variable | Default | Description |
|---|---|---|
| `AI_BACKEND` | _(empty)_ | `anthropic`, `openai`, or `ollama`. Leave empty to disable AI features. |
| `AI_MODEL` | `claude-sonnet-4-6` | Model name. Depends on chosen backend. |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key (if `AI_BACKEND=anthropic`). |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key (if `AI_BACKEND=openai`). |
| `OLLAMA_BASE_URL` | _(empty)_ | Ollama base URL (if `AI_BACKEND=ollama`). E.g. `http://ollama:11434` |

---

## Webhook / API

| Variable | Default | Description |
|---|---|---|
| `WEBHOOK_RATE_LIMIT` | `20` | Max inbound webhook requests per minute per API key. |
| `WEBHOOK_MAX_PAYLOAD_BYTES` | `65536` | Max inbound webhook payload size (64KB). |

---

## Notes

- Secrets must only be in `.env` — never in code, logs, API responses, or Docker image layers.
- `.env` is in `.gitignore` — never commit it.
- Rotate `SECRET_KEY` will invalidate all active sessions (users must re-login).
