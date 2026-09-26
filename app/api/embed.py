from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.models import User, Widget
from app.db.session import get_db

router = APIRouter(prefix="/api/widgets", tags=["embed"])


@router.get("/{widget_id}/embed")
def embed(widget_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.scalar(select(Widget).where(Widget.id == widget_id, Widget.tenant_id == user.tenant_id)):
        raise HTTPException(404, "Widget not found")
    return {"snippet": f'<div data-flyrank-widget="{widget_id}"></div>\n<script async src="{settings.api_base_url}/widget.v1.js"></script>'}
