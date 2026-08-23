def test_register_login_and_me(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "correct-horse-1"},
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "correct-horse-1"},
    )
    assert logged_in.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_duplicate_email_is_rejected(client):
    payload = {"name": "Ada", "email": "ada@example.com", "password": "correct-horse-1"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409

