
import socket

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory store, enough for learning purposes
_items = []


def build_greeting(name=None):
    """Return a greeting, defaulting to 'user'."""
    cleaned = (name or "user").strip()
    if not cleaned:
        cleaned = "user"
    return f"hello {cleaned}"


@app.route("/")
def hello():
    return "hello user"


@app.route("/greet/<name>")
def greet(name):
    return build_greeting(name)


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/info")
def info():
    return jsonify(
        hostname=socket.gethostname(),
        version=os.getenv("APP_VERSION", "dev"),
    )


@app.route("/items", methods=["GET"])
def list_items():
    return jsonify(items=_items, count=len(_items))


@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json(silent=True)
    if not data or "name" not in data or not str(data["name"]).strip():
        return jsonify(error="'name' is required"), 400
    item = {"id": len(_items) + 1, "name": str(data["name"]).strip()}
    _items.append(item)
    return jsonify(item), 201


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    for item in _items:
        if item["id"] == item_id:
            return jsonify(item)
    return jsonify(error="item not found"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)