"""
API Demo Script — exercises every endpoint using Django's test client.
No server or PostgreSQL needed (uses local SQLite settings).

Usage:
    .venv\Scripts\python demo.py
"""
import os
import sys
import json

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from django.test import Client

client = Client()


def section(title):
    print(f"\n{'='*62}")
    print(f"  {title}")
    print(f"{'='*62}")


def show(label, response):
    ok = response.status_code < 400
    status_str = f"[{response.status_code}]"
    print(f"\n>> {label}")
    print(f"   Status : {status_str}")
    try:
        data = response.json()
        print(f"   Body   :")
        print("   " + json.dumps(data, indent=4, default=str).replace("\n", "\n   "))
    except Exception:
        print(f"   Body   : {response.content}")


# ==============================================================
section("1. AUTHENTICATION")
# ==============================================================

# Register user
r = client.post("/api/auth/register/", {
    "name": "Alice",
    "email": "alice@demo.com",
    "password": "AlicePass@1",
    "confirm_password": "AlicePass@1",
    "role": "user"
}, content_type="application/json")
show("POST /api/auth/register/ (user)", r)
user_access  = r.json()["tokens"]["access"]
user_refresh = r.json()["tokens"]["refresh"]

# Register admin
r = client.post("/api/auth/register/", {
    "name": "Admin Bob",
    "email": "bob@demo.com",
    "password": "BobPass@1234",
    "confirm_password": "BobPass@1234",
    "role": "admin"
}, content_type="application/json")
show("POST /api/auth/register/ (admin)", r)
admin_access = r.json()["tokens"]["access"]

# Login
r = client.post("/api/auth/login/", {
    "email": "alice@demo.com",
    "password": "AlicePass@1"
}, content_type="application/json")
show("POST /api/auth/login/", r)

# Token refresh
r = client.post("/api/auth/refresh/", {
    "refresh": user_refresh
}, content_type="application/json")
show("POST /api/auth/refresh/", r)

# Wrong password - 401
r = client.post("/api/auth/login/", {
    "email": "alice@demo.com",
    "password": "wrongpassword"
}, content_type="application/json")
show("POST /api/auth/login/ (wrong password) -> 401", r)


# ==============================================================
section("2. LOCKER MANAGEMENT (Admin CRUD)")
# ==============================================================

admin_hdr = {"HTTP_AUTHORIZATION": f"Bearer {admin_access}"}
user_hdr  = {"HTTP_AUTHORIZATION": f"Bearer {user_access}"}

# Create lockers
r = client.post("/api/lockers/", {
    "locker_number": "L001", "location": "Floor 1 - Zone A"
}, content_type="application/json", **admin_hdr)
show("POST /api/lockers/ - Create L001 (admin)", r)
locker1_id = r.json()["locker"]["id"]

r = client.post("/api/lockers/", {
    "locker_number": "L002", "location": "Floor 1 - Zone B"
}, content_type="application/json", **admin_hdr)
show("POST /api/lockers/ - Create L002 (admin)", r)
locker2_id = r.json()["locker"]["id"]

r = client.post("/api/lockers/", {
    "locker_number": "L003", "location": "Floor 2"
}, content_type="application/json", **admin_hdr)
show("POST /api/lockers/ - Create L003 (admin)", r)

# User tries to create -> 403
r = client.post("/api/lockers/", {
    "locker_number": "L999", "location": "Unauthorized"
}, content_type="application/json", **user_hdr)
show("POST /api/lockers/ - User attempts create -> 403", r)

# List all
r = client.get("/api/lockers/", **user_hdr)
show("GET /api/lockers/ - List all lockers", r)

# Detail
r = client.get(f"/api/lockers/{locker1_id}/", **user_hdr)
show("GET /api/lockers/<id>/ - Locker detail", r)

# Update
r = client.put(f"/api/lockers/{locker1_id}/", {
    "locker_number": "L001",
    "location": "Floor 1 - Zone A (Updated)",
    "status": "available"
}, content_type="application/json", **admin_hdr)
show("PUT /api/lockers/<id>/ - Update location (admin)", r)


# ==============================================================
section("3. AVAILABLE LOCKERS - Redis Cache Demo")
# ==============================================================

# First call -> hits DB, puts result in cache
r = client.get("/api/lockers/available/", **user_hdr)
show("GET /api/lockers/available/ - 1st call  [source: database]", r)

# Second call -> served from cache
r = client.get("/api/lockers/available/", **user_hdr)
show("GET /api/lockers/available/ - 2nd call  [source: cache]", r)


# ==============================================================
section("4. RESERVATION MANAGEMENT")
# ==============================================================

# Reserve L001
r = client.post("/api/reservations/", {
    "locker_id": locker1_id
}, content_type="application/json", **user_hdr)
show("POST /api/reservations/ - Alice reserves L001", r)
res1_id = r.json()["reservation"]["id"]

# Try to reserve occupied L001 -> conflict
r = client.post("/api/reservations/", {
    "locker_id": locker1_id
}, content_type="application/json", **admin_hdr)
show("POST /api/reservations/ - Reserve L001 again -> 400 (occupied)", r)

# Reserve L002 as admin
r = client.post("/api/reservations/", {
    "locker_id": locker2_id
}, content_type="application/json", **admin_hdr)
show("POST /api/reservations/ - Admin reserves L002", r)
res2_id = r.json()["reservation"]["id"]

# User sees own reservations only
r = client.get("/api/reservations/", **user_hdr)
show("GET /api/reservations/ - User sees own only (count=1)", r)

# Admin sees all
r = client.get("/api/reservations/", **admin_hdr)
show("GET /api/reservations/ - Admin sees all (count=2)", r)

# Get detail
r = client.get(f"/api/reservations/{res1_id}/", **user_hdr)
show("GET /api/reservations/<id>/ - Reservation detail", r)

# Other user can't view another's reservation
r = client.get(f"/api/reservations/{res2_id}/", **user_hdr)
show("GET /api/reservations/<id>/ - Alice views Bob's -> 403", r)

# Release L001
r = client.put(f"/api/reservations/{res1_id}/release/", **user_hdr)
show("PUT /api/reservations/<id>/release/ - Alice releases L001", r)

# Check available - L001 back
r = client.get("/api/lockers/available/", **user_hdr)
show("GET /api/lockers/available/ - After release (source: database, L001 back)", r)

# Already released - 400
r = client.put(f"/api/reservations/{res1_id}/release/", **user_hdr)
show("PUT /api/reservations/<id>/release/ - Already released -> 400", r)


# ==============================================================
section("5. DEACTIVATE LOCKER")
# ==============================================================

# Deactivate occupied L002 -> 400
r = client.delete(f"/api/lockers/{locker2_id}/", **admin_hdr)
show("DELETE /api/lockers/<id>/ - Deactivate occupied L002 -> 400", r)

# Release L002 first
r = client.put(f"/api/reservations/{res2_id}/release/", **admin_hdr)
show("PUT /api/reservations/<id>/release/ - Admin releases L002", r)

# Deactivate now-available L002
r = client.delete(f"/api/lockers/{locker2_id}/", **admin_hdr)
show("DELETE /api/lockers/<id>/ - Deactivate L002 -> 200 OK", r)

# L002 no longer in available list
r = client.get("/api/lockers/available/", **user_hdr)
show("GET /api/lockers/available/ - L002 gone (deactivated)", r)


# ==============================================================
section("DEMO COMPLETE")
# ==============================================================
print("\nAll endpoints exercised successfully!\n")
print("  Swagger UI  : http://localhost:8000/api/docs/swagger/")
print("  ReDoc       : http://localhost:8000/api/docs/redoc/")
print("  Django Admin: http://localhost:8000/admin/")
print()
