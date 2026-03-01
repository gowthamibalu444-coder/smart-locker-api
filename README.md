# 🔐 Smart Storage Locker Management System

A production-ready Django REST Framework backend for managing smart storage lockers with JWT authentication, Redis caching, and ELK stack logging.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 5.0 + Django REST Framework |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Authentication | JWT via `djangorestframework-simplejwt` |
| Logging | JSON logs → Logstash → Elasticsearch → Kibana |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
smart_locker/
├── config/                  # Django project configuration
│   ├── settings/
│   │   ├── base.py          # Shared settings (DB, Redis, JWT, logging)
│   │   ├── development.py   # Dev overrides
│   │   └── production.py    # Production security settings
│   └── urls.py              # Root URL config
├── apps/
│   ├── accounts/            # User auth (JWT register/login/refresh)
│   ├── lockers/             # Locker CRUD + Redis-cached available list
│   └── reservations/        # Reservation lifecycle management
├── core/
│   ├── permissions.py       # IsAdminRole, IsOwnerOrAdmin, etc.
│   ├── exceptions.py        # Global JSON error handler
│   └── logging.py           # JSON log formatter for Kibana
├── docker/
│   └── logstash/
│       └── logstash.conf    # Logstash pipeline
├── logs/                    # Log files (watched by Logstash)
├── docker-compose.yml       # Full stack orchestration
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start (Local — Without Docker)

### 1. Create virtual environment & install dependencies

```bash
cd smart_locker
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env
# Edit .env with your PostgreSQL and Redis credentials
```

### 3. Apply database migrations

```bash
python manage.py migrate
```

### 4. Create an admin user

```bash
python manage.py create_admin --email admin@example.com --name "Admin User" --password Admin@1234
```

### 5. Run the development server

```bash
python manage.py runserver
```

The API is now available at **http://localhost:8000**

---

## Quick Start (Docker Compose — Full Stack)

```bash
docker-compose up --build
```

This starts:
- Django app at `http://localhost:8000`
- PostgreSQL at `localhost:5432`
- Redis at `localhost:6379`
- Elasticsearch at `http://localhost:9200`
- Kibana at **`http://localhost:5601`**

---

## API Reference

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register new user | No |
| POST | `/api/auth/login/` | Login & get JWT tokens | No |
| POST | `/api/auth/refresh/` | Refresh access token | No |

**Register example:**
```json
POST /api/auth/register/
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "SecurePass@123",
  "confirm_password": "SecurePass@123"
}
```

**Login response:**
```json
{
  "success": true,
  "user": { "id": "...", "name": "Jane Doe", "email": "...", "role": "user" },
  "tokens": {
    "access": "<access_token>",
    "refresh": "<refresh_token>"
  }
}
```

---

### Locker Management

> All locker endpoints require `Authorization: Bearer <access_token>`

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/lockers/` | Create locker | Admin |
| GET | `/api/lockers/` | List all lockers | Any |
| GET | `/api/lockers/<id>/` | Locker details | Any |
| PUT | `/api/lockers/<id>/` | Update locker | Admin |
| DELETE | `/api/lockers/<id>/` | Deactivate locker | Admin |
| GET | `/api/lockers/available/` | Available lockers *(Redis cached, 60s TTL)* | Any |

**Available lockers response** (shows cache source):
```json
{
  "success": true,
  "source": "cache",       ← "cache" or "database"
  "count": 5,
  "lockers": [...]
}
```

---

### Reservation Management

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/reservations/` | Reserve a locker | Any authenticated |
| GET | `/api/reservations/` | List reservations (own / all) | User=own, Admin=all |
| GET | `/api/reservations/<id>/` | Reservation details | Owner or Admin |
| PUT | `/api/reservations/<id>/release/` | Release locker | Owner or Admin |

**Create reservation:**
```json
POST /api/reservations/
{
  "locker_id": "<locker-uuid>"
}
```

---

## Role-Based Access Control

| Action | User | Admin |
|--------|------|-------|
| Register/Login | ✅ | ✅ |
| View all lockers | ✅ | ✅ |
| Create/Update/Deactivate locker | ❌ | ✅ |
| Reserve a locker | ✅ | ✅ |
| View own reservations | ✅ | ✅ |
| View all reservations | ❌ | ✅ |
| Release own reservation | ✅ | ✅ |

---

## Redis Caching

`GET /api/lockers/available/` uses a **60-second TTL** cache.

- First request: queries DB → stores in Redis → `"source": "database"`
- Subsequent requests (within 60s): served from Redis → `"source": "cache"`
- On reservation/release: cache expires naturally (no manual invalidation needed)

---

## Logging & Kibana

All key actions are logged in **structured JSON** format to `logs/app.log`:

```json
{
  "timestamp": "2026-03-01T09:00:00.000Z",
  "level": "INFO",
  "logger": "apps.reservations",
  "message": "Reservation created",
  "user_id": "abc-123",
  "action": "create_reservation",
  "locker_id": "xyz-456",
  "reservation_id": "def-789"
}
```

Logstash ships these logs to Elasticsearch. View them at **http://localhost:5601** (Kibana).

**Kibana setup:**
1. Open Kibana at `http://localhost:5601`
2. Go to **Stack Management → Index Patterns**
3. Create index pattern: `smart-locker-logs-*`
4. Go to **Discover** to view live logs

---

## Concurrency Protection

Reservations use a **two-layer protection** against race conditions:

1. **`select_for_update()`** — pessimistic DB row lock inside a `transaction.atomic()` block
2. **DB `UniqueConstraint`** — `unique_active_reservation_per_locker` on `(locker, status='active')` as a database-level safety net

Concurrent requests get `HTTP 409 Conflict`.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | *(required)* |
| `DEBUG` | Debug mode | `False` |
| `DB_NAME` | PostgreSQL database name | `smart_locker_db` |
| `DB_USER` | PostgreSQL username | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Access token lifetime | `15` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token lifetime | `7` |
