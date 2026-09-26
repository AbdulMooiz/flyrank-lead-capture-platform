from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.models import User, Widget
from app.db.session import get_db
from app.schemas.common import WidgetCreate, WidgetResponse

router = APIRouter(prefix="/api/widgets", tags=["widgets"])


def owned(widget_id: str, user: User, db: Session) -> Widget:
    widget = db.scalar(select(Widget).where(Widget.id == widget_id, Widget.tenant_id == user.tenant_id))
    if not widget:
        raise HTTPException(404, "Widget not found")
    return widget


@router.post("", response_model=WidgetResponse, status_code=201)
def create_widget(payload: WidgetCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    widget = Widget(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.get("", response_model=list[WidgetResponse])
def list_widgets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Widget).where(Widget.tenant_id == user.tenant_id).order_by(Widget.created_at.desc())))


@router.get("/{widget_id}", response_model=WidgetResponse)
def get_widget(widget_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned(widget_id, user, db)


@router.put("/{widget_id}", response_model=WidgetResponse)
def update_widget(widget_id: str, payload: WidgetCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    widget = owned(widget_id, user, db)
    for key, value in payload.model_dump().items():
        setattr(widget, key, value)
    db.commit()
    db.refresh(widget)
    return widget


@router.delete("/{widget_id}", status_code=204)
def delete_widget(widget_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    widget = owned(widget_id, user, db)
    db.delete(widget)
    db.commit()
    return Response(status_code=204)


@router.get("/{widget_id}/config")
def public_config(widget_id: str, response: Response, db: Session = Depends(get_db)):
    widget = db.scalar(select(Widget).where(Widget.id == widget_id, Widget.active.is_(True)))
    if not widget:
        raise HTTPException(404, "Widget not found")
    response.headers["Cache-Control"] = "public, max-age=60"
    return {"id": widget.id, "type": widget.type, "title": widget.title, "description": widget.description, "fields": widget.fields, "button_text": widget.button_text, "display_options": widget.display_options, "submit_url": f"{settings.api_base_url}/api/submissions"}
