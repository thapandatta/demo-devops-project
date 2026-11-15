import pytest

import app as app_module
from app import app, build_greeting


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app_module._items.clear()  # reset state between tests
    with app.test_client() as test_client:
        yield test_client


# ---------- build_greeting (unit tests) ----------
def test_build_greeting_default():
    assert build_greeting() == "hello user"


def test_build_greeting_with_name():
    assert build_greeting("Alice") == "hello Alice"


def test_build_greeting_strips_whitespace():
    assert build_greeting("  Bob  ") == "hello Bob"


def test_build_greeting_blank_falls_back():
    assert build_greeting("   ") == "hello user"


# ---------- basic routes ----------
def test_root_returns_hello_user(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data == b"hello user"


def test_greet_route(client):
    response = client.get("/greet/Priya")
    assert response.status_code == 200
    assert response.data == b"hello Priya"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_info_uses_env_version(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    response = client.get("/info")
    body = response.get_json()
    assert response.status_code == 200
    assert body["version"] == "1.2.3"
    assert "hostname" in body


def test_info_default_version(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    response = client.get("/info")
    assert response.get_json()["version"] == "dev"


# ---------- items API ----------
def test_list_items_empty(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.get_json() == {"items": [], "count": 0}


def test_add_item_success(client):
    response = client.post("/items", json={"name": "laptop"})
    assert response.status_code == 201
    assert response.get_json() == {"id": 1, "name": "laptop"}


def test_add_item_trims_name(client):
    response = client.post("/items", json={"name": "  mouse  "})
    assert response.get_json()["name"] == "mouse"


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": ""}, {"name": "   "}, {"other": "x"}],
)
def test_add_item_validation_errors(client, payload):
    response = client.post("/items", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_item_without_json_body(client):
    response = client.post("/items", data="not json")
    assert response.status_code == 400


def test_get_item_found(client):
    client.post("/items", json={"name": "keyboard"})
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.get_json()["name"] == "keyboard"


def test_get_item_not_found(client):
    response = client.get("/items/99")
    assert response.status_code == 404


def test_list_items_after_adds(client):
    client.post("/items", json={"name": "a"})
    client.post("/items", json={"name": "b"})
    body = client.get("/items").get_json()
    assert body["count"] == 2
    assert [item["name"] for item in body["items"]] == ["a", "b"]