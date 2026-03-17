# API Reference

IRDoc's REST API is fully documented via OpenAPI (Swagger UI).

---

## Interactive Docs

With IRDoc running, open:

```
http://your-irdoc/api/docs
```

The Swagger UI lets you explore all endpoints, view request/response schemas, and make test calls directly from the browser.

An alternative ReDoc view is available at:

```
http://your-irdoc/api/redoc
```

---

## Authentication

The API supports two authentication methods:

### JWT (user sessions)

Obtained by posting to `POST /api/v1/auth/login`. Returns an access token (15-minute lifetime) and sets an HttpOnly refresh cookie.

Include in requests:
```
Authorization: Bearer <access_token>
```

### API Key (service-to-service)

Created in Settings → API Keys. Include in requests:
```
Authorization: ApiKey irp_key_<key_value>
```

API keys have scoped permissions. The inbound webhook endpoint (`POST /api/v1/external/incidents`) requires a key with the `incidents:create` scope.

---

## Response Envelope

All endpoints return a consistent envelope:

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 143
  },
  "error": null
}
```

On error:

```json
{
  "data": null,
  "meta": {},
  "error": "Incident not found"
}
```

---

## Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Login, get access token |
| `POST` | `/api/v1/auth/refresh` | Refresh access token using cookie |
| `GET` | `/api/v1/incidents` | List incidents |
| `POST` | `/api/v1/incidents` | Create incident |
| `GET` | `/api/v1/incidents/{id}/timeline` | List timeline entries |
| `POST` | `/api/v1/incidents/{id}/timeline` | Add timeline entry |
| `GET` | `/api/v1/incidents/{id}/iocs` | List IOCs |
| `POST` | `/api/v1/incidents/{id}/iocs` | Add IOC |
| `POST` | `/api/v1/incidents/{id}/iocs/bulk` | Bulk add IOCs |
| `POST` | `/api/v1/incidents/{id}/reports` | Generate report |
| `GET` | `/api/v1/incidents/{id}/graph` | Get investigation graph |
| `POST` | `/api/v1/external/incidents` | Inbound webhook (API key auth) |
| `GET` | `/api/v1/features` | Get feature flags for current org |
| `GET` | `/api/health` | Health check |

For the complete reference with request/response schemas, use the Swagger UI.

---

## Rate Limits

| Endpoint group | Limit |
|---|---|
| Auth endpoints (`/auth/login`, `/auth/register`) | 5 requests/minute |
| Inbound webhook (`/external/incidents`) | 20 requests/minute per API key |
| All other API endpoints | 100 requests/minute |

Rate limit responses return HTTP `429` with a `Retry-After` header.
