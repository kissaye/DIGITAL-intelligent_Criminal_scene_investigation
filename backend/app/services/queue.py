from redis import Redis
from rq import Queue

from app.core.config import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    return Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))
