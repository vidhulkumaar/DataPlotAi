"""
Pydantic schemas for all API request / response bodies
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ── Dataset ───────────────────────────────────────────────────────────────────

class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    status: str
    row_count: int
    column_count: int
    warehouse_table: Optional[str]
    ai_schema: Optional[Dict[str, Any]]
    superset_dashboard_id: Optional[int]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# ── DB Connection ─────────────────────────────────────────────────────────────

class DBConnectRequest(BaseModel):
    db_type: str          # postgresql | mysql | snowflake | firebase
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    # Snowflake extras
    account: Optional[str] = None
    warehouse: Optional[str] = None
    schema: Optional[str] = None
    # Firebase
    service_account_json: Optional[str] = None
    project_id: Optional[str] = None
    # Alias shown in UI
    alias: str = "My Database"


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineStatusResponse(BaseModel):
    dataset_id: uuid.UUID
    status: str
    steps: List[Dict[str, Any]]
    ai_schema: Optional[Dict[str, Any]]
    superset_dashboard_id: Optional[int]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    superset_dashboard_id: Optional[int]
    superset_url: Optional[str]
    embed_token: Optional[str]
    charts: List[Dict[str, Any]]


# ── Native Chart Data ─────────────────────────────────────────────────────

class ChartDataItem(BaseModel):
    chart_id: str
    title: str
    chart_type: str              # bar, line, pie, scatter, table, big_number
    labels: List[Any] = []
    datasets: List[Dict[str, Any]] = []   # [{label, data, backgroundColor, ...}]
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    ai_reasoning: Optional[str] = None
    raw_rows: Optional[List[Dict[str, Any]]] = None  # for table type


class ChartDataResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    total_charts: int
    charts: List[ChartDataItem]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    dataset_id: uuid.UUID
    message: str
    history: List[Dict[str, str]] = []    # [{role: user|assistant, content: ...}]


class ChatResponse(BaseModel):
    answer: str
    sql_generated: Optional[str] = None
    new_chart_id: Optional[int] = None   # If a new Superset chart was created
    modified_chart_id: Optional[int] = None
    sources: List[str] = []
    chart_data: Optional[ChartDataItem] = None  # Native chart data for in-page rendering
    chart_modification: Optional[Dict[str, Any]] = None  # {target_title, new_type}


# ── Chart modification ────────────────────────────────────────────────────────

class ChartModifyRequest(BaseModel):
    dataset_id: uuid.UUID
    chart_id: int            # Superset chart ID
    instruction: str         # e.g. "change to bar chart"

