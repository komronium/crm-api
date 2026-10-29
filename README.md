# FastAPI Template

Production-ready FastAPI template with clean architecture and JWT authentication.

## Features

- ✅ JWT Authentication
- ✅ SQLAlchemy + PostgreSQL
- ✅ Clean Architecture
- ✅ Pydantic Validation
- ✅ Docker Support
- ✅ Unit Tests
- ✅ API Documentation

## Project Structure

```bash
📦 app/
├── 📂 api/                # API endpoints
│   └── 📂 v1/
├── 📂 core/              # Core configurations
├── 📂 db/                # Database setup
├── 📂 models/            # SQLAlchemy models
├── 📂 schemas/           # Pydantic schemas
├── 📂 services/          # Business logic
└── 📂 tests/             # Unit tests
```

## Quick Start

### Using Docker

```bash
# Clone repository
git clone https://github.com/yourusername/fastapi-template.git

# Setup environment
copy .env.example .env

# Run with Docker
docker-compose up -d
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload
```

## Tests

```bash
pip install -r requirements.txt
python -m pytest -q tests
```

The tests run on SQLite (the Postgres `JSONB` column is mapped to `JSON` for them), so they need no database.

## Notes for operators

- Every `/api/v1/leads/*` route requires a signed-in user (Bearer token).
- Login is locked for 15 minutes after 5 wrong passwords (per username and client address, in memory).
- Dashboard days and statistics use the business timezone (`TIMEZONE`, default `Asia/Tashkent`), not UTC.
- Facebook import: `FACEBOOK_LEADGEN_FORM_ID` is used when set, otherwise the value of `FACEBOOK_PAGE_ID` is used as the
  form id. If the access token expires the log says so once every 30 minutes; create a new token (a system-user token
  does not expire) and restart the service.
