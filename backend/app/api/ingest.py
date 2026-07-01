"""
Data ingestion endpoints — CSV, Excel, SQL dump upload
"""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Dataset
from app.models.schemas import DatasetResponse
from app.services.ingestion import IngestionService
from app.services.pipeline_orchestrator import run_full_pipeline

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".sql"}


@router.post("/upload", response_model=DatasetResponse, status_code=202)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV, Excel, or SQL dump file.
    Returns immediately; AI pipeline runs in background.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Persist uploaded file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4()
    dest_path = upload_dir / f"{upload_id}{suffix}"

    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Validate file size
    file_size_mb = dest_path.stat().st_size / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        dest_path.unlink()
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    # Determine source type
    source_map = {".csv": "csv", ".xlsx": "excel", ".xls": "excel", ".sql": "sql_dump"}
    source_type = source_map[suffix]

    # Create dataset record
    dataset = Dataset(
        user_id=current_user["user_id"],
        name=file.filename,
        source_type=source_type,
        source_reference=str(dest_path),
        status="pending",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # Kick off background pipeline: ingest → AI analysis → Superset
    background_tasks.add_task(
        run_full_pipeline,
        dataset_id=str(dataset.id),
        mode="upload",
        source_path=str(dest_path),
        source_type=source_type,
    )

    return dataset


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == current_user["user_id"])
        .order_by(Dataset.created_at.desc())
    )
    return result.scalars().all()


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user["user_id"],
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
