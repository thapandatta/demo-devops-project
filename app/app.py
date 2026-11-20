import os
import socket
from decimal import Decimal, InvalidOperation
from flask import send_from_directory

from flask import Flask, jsonify, request

from storage import ItemStore

app = Flask(__name__)

_store = None


def get_store():
    """Create the store lazily so tests can replace it."""
    global _store
    if _store is None:
        _store = ItemStore()
    return _store


def build_greeting(name=None):
    cleaned = (name or "user").strip()
    if not cleaned:
        cleaned = "user"
    return f"hello {cleaned}"


def validate_item(data):
    """Return (clean_values, None) if valid, or (None, error_message)."""
    if not isinstance(data, dict):
        return None, "request body must be a JSON object"

    name = str(data.get("name", "")).strip()
    if not name:
        return None, "'name' is required"

    if "cost" not in data:
        return None, "'cost' is required"
    if isinstance(data["cost"], bool):
        return None, "'cost' must be a number"
    try:
        cost = Decimal(str(data["cost"]))
    except InvalidOperation:
        return None, "'cost' must be a number"
    if not cost.is_finite() or cost < 0:
        return None, "'cost' must be zero or greater"

    if "quantity" not in data:
        return None, "'quantity' is required"
    quantity = data["quantity"]
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return None, "'quantity' must be a whole number"
    if quantity < 0:
        return None, "'quantity' must be zero or greater"

    return {"name": name, "cost": cost, "quantity": quantity}, None


@app.route("/")
def hello():
    return "hello user"


@app.route("/greet/<name>")
def greet(name):
    return build_greeting(name)


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/health/deep")
def health_deep():
    deps = get_store().ping()
    healthy = all(value == "ok" for value in deps.values())
    return jsonify(status="ok" if healthy else "degraded", **deps), (
        200 if healthy else 503
    )


@app.route("/info")
def info():
    return jsonify(
        hostname=socket.gethostname(),
        version=os.getenv("APP_VERSION", "dev"),
    )


@app.route("/items", methods=["GET"])
def list_items():
    items, cache_status = get_store().list_all()
    response = jsonify(items=items, count=len(items))
    response.headers["X-Cache"] = cache_status.upper()
    return response


@app.route("/items", methods=["POST"])
def add_item():
    values, error = validate_item(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    item = get_store().add(**values)
    return jsonify(item), 201

@app.route("/ui")
def ui():
    return send_from_directory("static", "index.html")


@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    item, cache_status = get_store().get(item_id)
    if item is None:
        return jsonify(error="item not found"), 404
    response = jsonify(item)
    response.headers["X-Cache"] = cache_status.upper()
    return response


@app.route("/items/<item_id>", methods=["PUT"])
def update_item(item_id):
    values, error = validate_item(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    item = get_store().update(item_id, **values)
    if item is None:
        return jsonify(error="item not found"), 404
    return jsonify(item)


@app.route("/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    get_store().delete(item_id)
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)