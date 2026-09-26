import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import SideEffectJob, Submission, Widget
from app.db.session import get_db
from app.integrations.geo import GeoEnricher
from app.schemas.common import SubmissionCreate, SubmissionResponse
from app.services.jobs import enqueue_notification
from app.services.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/submissions", tags=["public submissions"])


@router.post("", response_model=SubmissionResponse, status_code=201)
async def create_submission(payload: SubmissionCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    widget = db.scalar(select(Widget).where(Widget.id == payload.widget_id, Widget.active.is_(True)))
    if not widget:
        raise HTTPException(404, "Widget not found")
    check_rate_limit(f"{client_ip}:{widget.id}")
    if payload.honeypot:
        raise HTTPException(400, "Spam submission rejected")
    allowed = {field.get("name") for field in widget.fields if isinstance(field, dict) and field.get("name")}
    unknown = set(payload.data) - allowed
    if unknown:
        raise HTTPException(422, {"unknown_fields": sorted(unknown)})
    for field in widget.fields:
        if field.get("required") and not payload.data.get(field.get("name")):
            raise HTTPException(422, f"Field '{field.get('name')}' is required")
    idem = request.headers.get("Idempotency-Key")
    if idem:
        existing = db.scalar(select(Submission).where(Submission.widget_id == widget.id, Submission.idempotency_key == idem))
        if existing:
            return SubmissionResponse(id=existing.id, status="already_received", created_at=existing.created_at)
    geo = await GeoEnricher().enrich(client_ip)
    submission = Submission(tenant_id=widget.tenant_id, widget_id=widget.id, payload=payload.data, ip_address=client_ip, idempotency_key=idem, **geo)
    db.add(submission)
    try:
        db.flush()
        job = SideEffectJob(submission_id=submission.id, status="queued", attempts=0)
        db.add(job)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Submission).where(Submission.widget_id == widget.id, Submission.idempotency_key == idem)) if idem else None
        if existing:
            return SubmissionResponse(id=existing.id, status="already_received", created_at=existing.created_at)
        raise HTTPException(409, "Submission could not be stored")
    enqueue_notification(submission.id)
    return SubmissionResponse(id=submission.id, status="received", created_at=submission.created_at or datetime.now(timezone.utc))
