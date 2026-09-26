from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def new_id() -> str:
    return str(uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    widgets: Mapped[list["Widget"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Widget(Base):
    __tablename__ = "widgets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSON_TYPE, nullable=False)
    button_text: Mapped[str] = mapped_column(String(80), nullable=False)
    display_options: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant: Mapped[Tenant] = relationship(back_populates="widgets")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="widget", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_id: Mapped[str] = mapped_column(ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    country_code: Mapped[str | None] = mapped_column(String(8))
    city: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    geo_provider: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    widget: Mapped[Widget] = relationship(back_populates="submissions")
    job: Mapped["SideEffectJob | None"] = relationship(back_populates="submission", uselist=False, cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_widget_idempotency"), Index("ix_submission_tenant_created", "tenant_id", "created_at"))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))


class SideEffectJob(Base):
    __tablename__ = "side_effect_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submission: Mapped[Submission] = relationship(back_populates="job")
