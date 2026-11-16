
import pytest

import app as app_module
from app import app, build_greeting


class FakeItemStore:
    """In-memory replacement for DynamoDB + Redis during unit tests."""

    def __init__(self):
        self.items = {}
        self.next_id = 1

    def add(self, name, cost, quantity):
        item = {
            "id": str(self.next_id),
            "name": name,
            "cost": float(cost),
            "quantity": int(quantity),
        }
        self.items[item["id"]] = item
        self.next_id += 1
        return item

    def list_all(self):
        return list(self.items.values()), "miss"

    def get(self, item_id):
        return self.items.get(item_id), "miss"

    def update(self, item_id, name, cost, quantity):
        if item_id not in self.items:
            return None

        item = {
            "id": item_id,
            "name": name,
            "cost": float(cost),
            "quantity": int(quantity),
        }
        self.items[item_id] = item
        return item

    def delete(self, item_id):
        self.items.pop(item_id, None)

    def ping(self):
        return {"dynamodb": "ok", "redis": "ok"}


@pytest.fixture
def client():
    app.config["TESTING"] = True

    # Replace real DynamoDB/Redis storage with fake storage.
    app_module._store = FakeItemStore()

    with app.test_client() as test_client:
        yield test_client

    app_module._store = None


# ---------- build_greeting ----------

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


def test_health_deep(client):
    response = client.get("/health/deep")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "dynamodb": "ok",
        "redis": "ok",
    }


# ---------- items API ----------

def test_list_items_empty(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.get_json() == {"items": [], "count": 0}


def test_add_item_success(client):
    response = client.post(
        "/items",
        json={"name": "laptop", "cost": 50000, "quantity": 2},
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": "1",
        "name": "laptop",
        "cost": 50000.0,
        "quantity": 2,
    }


def test_add_item_trims_name(client):
    response = client.post(
        "/items",
        json={"name": "  mouse  ", "cost": 500, "quantity": 3},
    )

    assert response.status_code == 201
    assert response.get_json()["name"] == "mouse"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "laptop"},
        {"name": "", "cost": 100, "quantity": 1},
        {"name": "   ", "cost": 100, "quantity": 1},
        {"name": "laptop", "cost": -10, "quantity": 1},
        {"name": "laptop", "cost": 100, "quantity": -1},
        {"name": "laptop", "cost": "invalid", "quantity": 1},
        {"name": "laptop", "cost": 100, "quantity": 1.5},
    ],
)
def test_add_item_validation_errors(client, payload):
    response = client.post("/items", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_item_without_json_body(client):
    response = client.post("/items", data="not json")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_get_item_found(client):
    client.post(
        "/items",
        json={"name": "keyboard", "cost": 1000, "quantity": 1},
    )

    response = client.get("/items/1")

    assert response.status_code == 200
    assert response.get_json()["name"] == "keyboard"


def test_get_item_not_found(client):
    response = client.get("/items/99")
    assert response.status_code == 404


def test_list_items_after_adds(client):
    client.post(
        "/items",
        json={"name": "laptop", "cost": 50000, "quantity": 1},
    )
    client.post(
        "/items",
        json={"name": "mouse", "cost": 500, "quantity": 2},
    )

    body = client.get("/items").get_json()

    assert body["count"] == 2
    assert [item["name"] for item in body["items"]] == [
        "laptop",
        "mouse",
    ]


def test_update_item(client):
    client.post(
        "/items",
        json={"name": "mouse", "cost": 500, "quantity": 1},
    )

    response = client.put(
        "/items/1",
        json={"name": "wireless mouse", "cost": 800, "quantity": 2},
    )

    assert response.status_code == 200
    assert response.get_json()["name"] == "wireless mouse"


def test_delete_item(client):
    client.post(
        "/items",
        json={"name": "keyboard", "cost": 1000, "quantity": 1},
    )

    response = client.delete("/items/1")

    assert response.status_code == 204
    assert client.get("/items/1").status_code == 404
