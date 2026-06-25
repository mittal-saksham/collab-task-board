"""DB-backed tests for the auth routes (signup / login / me)."""


def test_signup_returns_user_without_password(client):
    r = client.post(
        "/auth/signup", json={"email": "a@x.com", "password": "supersecret123"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@x.com"
    assert "id" in body
    # The hash must never cross the wire.
    assert "hashed_password" not in body
    assert "password" not in body


def test_duplicate_signup_conflicts(client):
    payload = {"email": "a@x.com", "password": "supersecret123"}
    assert client.post("/auth/signup", json=payload).status_code == 201
    assert client.post("/auth/signup", json=payload).status_code == 409


def test_signup_rejects_short_password(client):
    # min_length=8 on the schema → 422 before our handler runs.
    r = client.post("/auth/signup", json={"email": "a@x.com", "password": "short"})
    assert r.status_code == 422


def test_signup_rejects_malformed_email(client):
    r = client.post(
        "/auth/signup", json={"email": "not-an-email", "password": "supersecret123"}
    )
    assert r.status_code == 422


def test_login_returns_a_token(client):
    client.post(
        "/auth/signup", json={"email": "a@x.com", "password": "supersecret123"}
    )
    r = client.post(
        "/auth/login", data={"username": "a@x.com", "password": "supersecret123"}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password_401(client):
    client.post(
        "/auth/signup", json={"email": "a@x.com", "password": "supersecret123"}
    )
    r = client.post(
        "/auth/login", data={"username": "a@x.com", "password": "wrongpass1"}
    )
    assert r.status_code == 401


def test_login_unknown_email_401(client):
    r = client.post(
        "/auth/login", data={"username": "nobody@x.com", "password": "supersecret123"}
    )
    assert r.status_code == 401


def test_me_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_returns_the_current_user(client, auth):
    headers = auth("a@x.com")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "a@x.com"
