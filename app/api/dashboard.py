from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import Submission, User, Widget
from app.db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/submissions")
def submissions(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)):
    base = select(Submission).where(Submission.tenant_id == user.tenant_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(Submission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{"id": row.id, "widget_id": row.widget_id, "data": row.payload, "country": row.country, "created_at": row.created_at} for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/analytics")
def analytics(user: User = Depends(current_user), db: Session = Depends(get_db)):
    start = datetime.now(timezone.utc) - timedelta(days=7)
    total = db.scalar(select(func.count(Submission.id)).where(Submission.tenant_id == user.tenant_id)) or 0
    today = db.scalar(select(func.count(Submission.id)).where(Submission.tenant_id == user.tenant_id, Submission.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))) or 0
    widgets = db.execute(select(Submission.widget_id, func.count(Submission.id)).where(Submission.tenant_id == user.tenant_id).group_by(Submission.widget_id)).all()
    countries = db.execute(select(Submission.country, func.count(Submission.id)).where(Submission.tenant_id == user.tenant_id).group_by(Submission.country)).all()
    recent = db.execute(select(func.date(Submission.created_at), func.count(Submission.id)).where(Submission.tenant_id == user.tenant_id, Submission.created_at >= start).group_by(func.date(Submission.created_at)).order_by(func.date(Submission.created_at))).all()
    return {"total": total, "today": today, "by_widget": {widget_id: count for widget_id, count in widgets}, "by_country": {country or "unknown": count for country, count in countries}, "recent_days": {str(day): count for day, count in recent}}
