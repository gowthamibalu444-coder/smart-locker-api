# Smart Storage Locker Management System

This repository contains the backend service for a Smart Storage Locker system, completely designed and developed to allow users to reserve lockers, store/retrieve items, and track usage.

## 🚀 Live Demo
- **API Base URL**: `https://smart-locker-api-production.up.railway.app`
- **Interactive API Documentation (Swagger)**: `https://smart-locker-api-production.up.railway.app/api/docs/swagger/`

---

## 🏗 Stack Architecture
- **Framework**: Django & Django REST Framework (Python 3.11)
- **Database**: PostgreSQL (Hosted on Neon)
- **Caching Engine**: Redis (Configured via `REDIS_URL` in Django cache framework)
- **Authentication**: JSON Web Tokens (JWT via `rest_framework_simplejwt`)
- **Containerization**: Docker & Dockerfile
- **Deployment & Hosting**: Railway.app
- **Logging**: Structured JSON Logging (Ready for ELK/Kibana ingestion)

---

## ✨ Features & Requirements Met

### 👤 User Management
- **Registration & Login**: Secure user endpoints issuing JWT tokens for session management.
- **Role-based Access Control Policies**:
  - `IsAdminUser`: Superusers who can manage the entire application state.
  - `IsAuthenticated`: Regular registered users who can reserve and manage their own lockers.

### 🔒 Locker Management & Reservation Logic
- Admins possess exclusive rights to create, query, modify details of, and deactivate lockers.
- Users can query all *active* lockers and filter for currently available ones.
- **Race Condition Prevention Engine**: Strict transaction block mechanisms (`select_for_update`) ensure that the same locker cannot be accidentally reserved by two users simultaneously under high concurrency.
- **Automatic Status Mutation**: Making a reservation actively changes the locker state to occupied automatically. Releasing it marks it back to available.

### ⚡ Caching Mechanisms
- The `List Available Lockers` endpoint features an integrated checking routine fetching cache buffers dynamically. 
- Results are temporarily preserved mimicking low-TTL constraints (60 seconds by default configuration).
- Cache validity naturally exhausts post-action ensuring dynamic updates upon continuous locker reservations without triggering manual/harsh invalidations.

### 📊 Structured Logging
- The application processes detailed logging interceptors producing JSON arrays tracking key actions, trace logs, warnings, reservations attempts, and user login traces. 
- These standard JSON streams are structurally perfect and easily ship to Logstash or directly into Kibana environments for Real-Time monitoring pipelines.

---

## 📂 Project Structure Strategy
Implemented modern domain-driven app distribution:
```
smart_locker/
├── apps/
│   ├── accounts/     # User, Admin modes, and Auth management
│   └── lockers/      # Locker objects, Reservations, and availability logic
├── config/           # Django settings, separated by env (base, dev, prod)
├── core/             # Custom exceptions, standardized logging, permissions etc
└── manage.py
```
*This cleanly breaks project mechanics, increasing readability and allowing faster maintainability while utilizing proper coding standards across APIs and classes.*

---

## 🛠 Endpoints

### Authentication
- `POST /api/auth/register/` - Register novel user profiles
- `POST /api/auth/login/` - Login and acquire Access/Refresh JWT
- `POST /api/auth/refresh/` - Renew expired JWT

### Locker Administration
- `GET /api/lockers/` - View all valid lockers
- `GET /api/lockers/available/` - View free lockers (CACHED endpoint)
- `POST /api/lockers/` - (Admin only) Construct new locker unit
- `GET /api/lockers/{id}/` - Detailed locker trace
- `PUT /api/lockers/{id}/` - (Admin only) Alter state
- `DELETE /api/lockers/{id}/` - (Admin only) Safely detach/delete locker

### Reservation Cycle
- `POST /api/reservations/` - Book targeted valid locker
- `GET /api/reservations/` - Fetch historical and active queries (Users see theirs, Admins see global)
- `GET /api/reservations/{id}/` - Granular perspective
- `PUT /api/reservations/{id}/release/` - Finalize interaction and purge hold

---

## 💻 Local Developer Setup

1. **Clone Repo**
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. **Environment & Keys**
   Configure `.env` file using `.env.example` as standard. Provide `DATABASE_URL` and `REDIS_URL` natively.

3. **Docker Method (Recommended)**
   ```bash
   docker-compose up --build
   ```
   *This initializes the PostgreSQL and Redis containers, performs makemigrations automatically, and spins up the backend runtime over `http://localhost:8000`.*
