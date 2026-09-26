import logging
import time

from redis import Redis
from rq import Queue, Worker
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SideEffectJob, Submission
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def process_notification(submission_id: str) -> None:
    db: Session = SessionLocal()
    job = db.query(SideEffectJob).filter_by(submission_id=submission_id).one()
    try:
        job.attempts += 1
        submission = db.get(Submission, submission_id)
        if not submission:
            raise RuntimeError("submission missing")
        if submission.payload.get("force_side_effect_failure"):
            raise RuntimeError("configured side-effect failure")
        logger.info("notification_sent", extra={"submission_id": submission_id})
        job.status = "succeeded"
        db.commit()
    except Exception as exc:
        job.last_error = str(exc)
        job.status = "failed" if job.attempts >= 3 else "retrying"
        db.commit()
        logger.error("notification_failed", extra={"submission_id": submission_id, "attempt": job.attempts, "error": str(exc)})
        if job.attempts < 3:
            time.sleep(2 ** (job.attempts - 1))
            raise
    finally:
        db.close()


def main() -> None:
    redis = Redis.from_url(settings.redis_url)
    worker = Worker([Queue("notifications", connection=redis)], connection=redis)
    worker.work()


if __name__ == "__main__":
    main()
