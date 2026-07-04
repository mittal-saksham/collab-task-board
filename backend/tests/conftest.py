"""Shared fixtures for the DB-backed API tests.

Isolation note: our CRUD layer calls `db.commit()`, so wrapping a test in one
outer transaction and rolling back won't isolate it (the commit ends the
transaction). Instead we create the schema ONCE on a throwaway test database and
TRUNCATE every table (RESTART IDENTITY) after each test.

Heavy imports (settings, the app, models) live INSIDE the fixtures so the
pure-logic tests (e.g. test_ordering.py) can still run with no database or env.
"""

import pytest

TEST_DB_NAME = "taskapp_test"

# Wiped after each test. CASCADE handles FK order; RESTART IDENTITY resets the id
# sequences so every test sees predictable ids starting at 1.
_ALL_TABLES = (
    "activities, comments, card_labels, cards, labels, "
    "lists, memberships, boards, users"
)


@pytest.fixture(scope="session")
def _engine():
    """An engine bound to a freshly-created `taskapp_test` database."""
    import sqlalchemy as sa
    from sqlalchemy.engine import make_url

    import app.models  # noqa: F401 — importing registers every table on Base.metadata
    from app.core.config import settings
    from app.db.base import Base

    app_url = make_url(settings.database_url)
    test_url = app_url.set(database=TEST_DB_NAME)
    admin_url = app_url.set(database="postgres")  # the always-present maintenance db

    # CREATE DATABASE can't run in a transaction → use an autocommit connection.
    admin = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    # Pass the URL OBJECT, not str(test_url): SQLAlchemy masks the password as
    # "***" when a URL is stringified, which would break authentication.
    engine = sa.create_engine(test_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(_engine):
    """A FastAPI TestClient whose `get_db` yields sessions on the test database.
    Truncates all tables after each test for isolation."""
    import sqlalchemy as sa
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    import app.api.ws as ws_module
    from app.db.session import get_db
    from app.main import app

    TestingSessionLocal = sessionmaker(
        bind=_engine, autoflush=False, autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # The WS handshake (api/ws.py) deliberately opens its own short-lived
    # session via SessionLocal instead of the get_db dependency — which means
    # dependency_overrides does NOT redirect it. Without this patch the WS
    # authz check queries the app's real database (empty in CI → every connect
    # rejected; worse, locally it can pass by coincidence against leftover dev
    # rows). Point it at the test engine and restore afterwards.
    _real_session_local = ws_module.SessionLocal
    ws_module.SessionLocal = TestingSessionLocal
    # Not used as a context manager, so the app lifespan doesn't run → the WS
    # manager's loop stays unset and emit() is a harmless no-op during tests.
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        ws_module.SessionLocal = _real_session_local
        with _engine.begin() as conn:
            conn.execute(
                sa.text(f"TRUNCATE {_ALL_TABLES} RESTART IDENTITY CASCADE")
            )
        # Rate limiters are in-memory and keyed by client IP — and every test
        # request comes from the same "testclient" IP, so without a reset the
        # auth fixture's signups/logins would trip the limit across tests.
        from app.core import ratelimit

        ratelimit.reset_all()


@pytest.fixture
def auth(client):
    """Factory: register + log in a user, return the Authorization headers.

    Usage:  headers = auth("owner@example.com")
    """
    def _make(email: str, password: str = "supersecret123") -> dict[str, str]:
        client.post("/auth/signup", json={"email": email, "password": password})
        resp = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
