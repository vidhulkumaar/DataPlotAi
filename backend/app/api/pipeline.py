"""
Pipeline status endpoints — check AI processing progress
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Dataset, PipelineRun
from app.models.schemas import PipelineStatusResponse

router = APIRouter()

STEP_ORDER = [
    "ingest",
    "schema_extract",
    "ai_schema_analysis",
    "ai_data_selection",
    "superset_push",
    "rag_embed",
]


@router.get("/{dataset_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    dataset_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    ds_result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user["user_id"],
        )
    )
    dataset = ds_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get pipeline run steps
    runs_result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.dataset_id == dataset_id)
        .order_by(PipelineRun.started_at)
    )
    runs = runs_result.scalars().all()
    run_map = {r.step: r for r in runs}

    steps = []
    for step_name in STEP_ORDER:
        run = run_map.get(step_name)
        steps.append({
            "step": step_name,
            "label": _step_label(step_name),
            "status": run.status if run else "pending",
            "detail": run.detail if run else None,
            "started_at": run.started_at.isoformat() if run and run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run and run.finished_at else None,
        })

    return PipelineStatusResponse(
        dataset_id=dataset_id,
        status=dataset.status,
        steps=steps,
        ai_schema=dataset.ai_schema,
        superset_dashboard_id=dataset.superset_dashboard_id,
    )


def _step_label(step: str) -> str:
    labels = {
        "ingest": "Data ingestion",
        "schema_extract": "Schema extraction",
        "ai_schema_analysis": "Gemini AI schema analysis",
        "ai_data_selection": "AI data selection",
        "superset_push": "Superset chart generation",
        "rag_embed": "RAG embedding",
    }
    return labels.get(step, step)
