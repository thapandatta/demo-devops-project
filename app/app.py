import os
import socket
from urllib.parse import parse_qs, urlparse

from flask import Flask, jsonify, request, send_from_directory

from storage import VideoStore

app = Flask(__name__)

_store = None

MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 1000
MAX_LINK_LENGTH = 500
MAX_VIDEO_MINUTES = 100000  # sanity cap, about 69 days

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def get_store():
    """Create the store lazily so tests can replace it."""
    global _store
    if _store is None:
        _store = VideoStore()
    return _store


def build_greeting(name=None):
    cleaned = (name or "user").strip()
    if not cleaned:
        cleaned = "user"
    return f"hello {cleaned}"


def is_valid_youtube_link(link):
    """True only for https links on a YouTube host that point at a video."""
    try:
        parsed = urlparse(link)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return False

    if host.endswith("youtu.be"):
        return len(parsed.path.strip("/")) > 0       # youtu.be/<id>
    if parsed.path == "/watch":
        return "v" in parse_qs(parsed.query)         # youtube.com/watch?v=<id>
    return parsed.path.startswith(("/shorts/", "/embed/", "/live/"))


def validate_video(data):
    """Return (clean_values, None) if valid, or (None, error_message)."""
    if not isinstance(data, dict):
        return None, "request body must be a JSON object"

    name = data.get("ytvideoname")
    if not isinstance(name, str) or not name.strip():
        return None, "'ytvideoname' is required"
    name = name.strip()
    if len(name) > MAX_NAME_LENGTH:
        return None, f"'ytvideoname' must be at most {MAX_NAME_LENGTH} characters"

    link = data.get("ytlink")
    if not isinstance(link, str) or not link.strip():
        return None, "'ytlink' is required"
    link = link.strip()
    if len(link) > MAX_LINK_LENGTH:
        return None, f"'ytlink' must be at most {MAX_LINK_LENGTH} characters"
    if not is_valid_youtube_link(link):
        return None, "'ytlink' must be a valid YouTube video link"

    description = data.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        return None, "'description' must be text"
    description = description.strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return None, f"'description' must be at most {MAX_DESCRIPTION_LENGTH} characters"

    if "length" not in data:
        return None, "'length' is required"
    length = data["length"]
    if isinstance(length, bool) or not isinstance(length, int):
        return None, "'length' must be a whole number of minutes"
    if length < 1:
        return None, "'length' must be at least 1 minute"
    if length > MAX_VIDEO_MINUTES:
        return None, f"'length' must be at most {MAX_VIDEO_MINUTES} minutes"

    return {
        "ytvideoname": name,
        "ytlink": link,
        "description": description,
        "length": length,
    }, None


@app.route("/")
def hello():
    return "hello user"


@app.route("/greet/<name>")
def greet(name):
    return build_greeting(name)


@app.route("/ui")
def ui():
    return send_from_directory("static", "index.html")


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


@app.route("/videos", methods=["GET"])
def list_videos():
    videos, cache_status = get_store().list_all()
    response = jsonify(videos=videos, count=len(videos))
    response.headers["X-Cache"] = cache_status.upper()
    return response


@app.route("/videos", methods=["POST"])
def add_video():
    values, error = validate_video(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    video = get_store().add(**values)
    return jsonify(video), 201


@app.route("/videos/<video_id>", methods=["GET"])
def get_video(video_id):
    video, cache_status = get_store().get(video_id)
    if video is None:
        return jsonify(error="video not found"), 404
    response = jsonify(video)
    response.headers["X-Cache"] = cache_status.upper()
    return response


@app.route("/videos/<video_id>", methods=["PUT"])
def update_video(video_id):
    values, error = validate_video(request.get_json(silent=True))
    if error:
        return jsonify(error=error), 400
    video = get_store().update(video_id, **values)
    if video is None:
        return jsonify(error="video not found"), 404
    return jsonify(video)


@app.route("/videos/<video_id>", methods=["DELETE"])
def delete_video(video_id):
    get_store().delete(video_id)
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)