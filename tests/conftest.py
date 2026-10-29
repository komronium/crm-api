import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "verify-me")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core import throttle
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.user import User


@compiles(JSONB, "sqlite")
def _jsonb_as_json(type_, compiler, **kw):  # the models use Postgres JSONB; the tests run on SQLite
    return "JSON"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    throttle.clear_all()
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, username="admin", password="admin-pass-1", **over):
    user = User(username=username, password=hash_password(password), name=username, **over)
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def admin(db):
    return make_user(db, "admin", "admin-pass-1", is_admin=True)


@pytest.fixture()
def auth(client, admin):
    token = client.post("/api/v1/login", json={"username": "admin", "password": "admin-pass-1"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
