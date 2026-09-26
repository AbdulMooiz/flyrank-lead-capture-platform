from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WidgetCreate(BaseModel):
    type: str = Field(pattern="^(signup|contact|cta|popover)$")
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    fields: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    button_text: str = Field(min_length=1, max_length=80)
    display_options: dict[str, Any] = Field(default_factory=dict)


class WidgetResponse(WidgetCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class SubmissionCreate(BaseModel):
    widget_id: str
    data: dict[str, Any]
    honeypot: str = ""


class SubmissionResponse(BaseModel):
    id: str
    status: str
    created_at: Any


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
