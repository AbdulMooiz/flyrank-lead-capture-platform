import logging

from redis import Redis
from rq import Queue, Retry

from app.core.config import settings

logger = logging.getLogger(__name__)


def enqueue_notification(submission_id: str) -> None:
    try:
        queue = Queue("notifications", connection=Redis.from_url(settings.redis_url))
        queue.enqueue(
            "app.workers.worker.process_notification",
            submission_id,
            retry=Retry(max=3, interval=[1, 5, 15]),
        )
    except Exception as exc:
        logger.error("side_effect_enqueue_failed", extra={"submission_id": submission_id, "error": str(exc)})
