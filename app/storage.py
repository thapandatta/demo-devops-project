import json
import os
import uuid
from datetime import datetime, timezone

import boto3
import redis

CACHE_TTL_SECONDS = 60
LIST_CACHE_KEY = "videos:all"


def to_jsonable(value):
    """Convert DynamoDB Decimals into int/float so JSON can serialize them."""
    from decimal import Decimal

    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


class VideoStore:
    """DynamoDB-backed storage with a Redis cache in front (cache-aside)."""

    def __init__(self, table=None, cache=None):
        if table is None:
            dynamodb = boto3.resource(
                "dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        if cache is None:
            cache = redis.Redis.from_url(
                os.getenv("REDIS_URL", "redis://redis:6379/0"),
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        self.table = table
        self.cache = cache

    # ---- cache helpers: a cache failure must never break the app ----
    def _cache_get(self, key):
        try:
            value = self.cache.get(key)
            return json.loads(value) if value else None
        except redis.RedisError:
            return None

    def _cache_set(self, key, value):
        try:
            self.cache.setex(key, CACHE_TTL_SECONDS, json.dumps(value))
        except redis.RedisError:
            pass

    def _cache_delete(self, *keys):
        try:
            self.cache.delete(*keys)
        except redis.RedisError:
            pass

    # ---- public API ----
    def add(self, ytvideoname, ytlink, description, length):
        video = {
            "id": str(uuid.uuid4()),
            "ytvideoname": ytvideoname,
            "ytlink": ytlink,
            "description": description,
            "length": int(length),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.table.put_item(Item=video)
        self._cache_delete(LIST_CACHE_KEY)
        return to_jsonable(video)

    def get(self, video_id):
        cache_key = f"video:{video_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached, "hit"

        video = self.table.get_item(Key={"id": video_id}).get("Item")
        if video:
            video = to_jsonable(video)
            self._cache_set(cache_key, video)
        return video, "miss"

    def list_all(self):
        cached = self._cache_get(LIST_CACHE_KEY)
        if cached is not None:
            return cached, "hit"

        rows = to_jsonable(self.table.scan().get("Items", []))
        # Skip leftover rows from the old schema (no ytvideoname)
        videos = [row for row in rows if "ytvideoname" in row]
        self._cache_set(LIST_CACHE_KEY, videos)
        return videos, "miss"

    def update(self, video_id, ytvideoname, ytlink, description, length):
        """Replace an existing video. Returns None if it doesn't exist."""
        existing = self.table.get_item(Key={"id": video_id}).get("Item")
        if not existing:
            return None
        video = {
            "id": video_id,
            "ytvideoname": ytvideoname,
            "ytlink": ytlink,
            "description": description,
            "length": int(length),
            "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        }
        self.table.put_item(Item=video)
        self._cache_delete(f"video:{video_id}", LIST_CACHE_KEY)
        return to_jsonable(video)

    def delete(self, video_id):
        self.table.delete_item(Key={"id": video_id})
        self._cache_delete(f"video:{video_id}", LIST_CACHE_KEY)

    def ping(self):
        """Report dependency health for /health/deep."""
        status = {"dynamodb": "ok", "redis": "ok"}
        try:
            self.table.load()
        except Exception:
            status["dynamodb"] = "down"
        try:
            self.cache.ping()
        except redis.RedisError:
            status["redis"] = "down"
        return status