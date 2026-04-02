from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes_analytics import router as analytics_router
from app.api.routes_auth import router as auth_router
from app.database.database import Base, SessionLocal, engine
from app.database.models import User

app = FastAPI()
app.include_router(auth_router)
app.include_router(analytics_router)
client = TestClient(app)


def _cleanup_user(email: str) -> None:
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).delete()
        db.commit()
    finally:
        db.close()


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)


def test_signup_creates_user_and_returns_token() -> None:
    email = "auth.signup@example.com"
    password = "super-secure-password"
    _cleanup_user(email)

    res = client.post("/auth/signup", json={"email": email, "password": password})

    assert res.status_code == 200
    payload = res.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        stored_hash = getattr(user, "password_hash", None)
        assert stored_hash is not None
        assert stored_hash != password
    finally:
        db.close()


def test_login_success_and_invalid_credentials_fail() -> None:
    email = "auth.login@example.com"
    password = "super-secure-password"
    _cleanup_user(email)

    signup_res = client.post("/auth/signup", json={"email": email, "password": password})
    assert signup_res.status_code == 200

    good_login = client.post("/auth/login", json={"email": email, "password": password})
    assert good_login.status_code == 200
    assert "access_token" in good_login.json()

    bad_login = client.post("/auth/login", json={"email": email, "password": "wrong-pass"})
    assert bad_login.status_code == 401


def test_protected_analytics_requires_token() -> None:
    no_token = client.get("/analytics/summary")
    assert no_token.status_code in (401, 403)

    email = "auth.protected@example.com"
    password = "super-secure-password"
    _cleanup_user(email)
    signup_res = client.post("/auth/signup", json={"email": email, "password": password})
    assert signup_res.status_code == 200

    token = signup_res.json()["access_token"]
    with_token = client.get(
        "/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert with_token.status_code == 200
