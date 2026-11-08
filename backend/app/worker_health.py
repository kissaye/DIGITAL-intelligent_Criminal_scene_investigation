"""Check this container's registered RQ worker and recent heartbeat."""
from datetime import UTC, datetime

from redis import Redis
from rq import Worker

from app.core.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    connection.ping()
    worker = Worker.find_by_key("rq:worker:pointcloud-worker", connection=connection)
    if worker is None or worker.last_heartbeat is None:
        raise SystemExit("RQ worker is not registered")
    heartbeat = worker.last_heartbeat.replace(tzinfo=UTC)
    if (datetime.now(UTC) - heartbeat).total_seconds() > worker.worker_ttl + 30:
        raise SystemExit("RQ worker heartbeat is stale")
