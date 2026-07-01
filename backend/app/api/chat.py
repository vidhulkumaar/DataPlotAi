"""
RAG chatbot endpoints — query, chart creation via natural language
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Dataset
from app.models.schemas import ChatRequest, ChatResponse, ChartModifyRequest
from app.services.rag_engine import RAGEngine

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    RAG chatbot — retrieves context from dataset embeddings,
    answers using Gemini, optionally creates/modifies Superset charts.
    """
    # Verify dataset ownership
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == body.dataset_id,
            Dataset.user_id == current_user["user_id"],
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status not in ("superset_ready", "ai_done"):
        raise HTTPException(status_code=400, detail="Dataset is still being processed")

    engine = RAGEngine(db=db)
    response = await engine.query(
        dataset=dataset,
        user_message=body.message,
        history=body.history,
        user_id=str(current_user["user_id"]),
    )
    return response


@router.post("/modify-chart", response_model=ChatResponse)
async def modify_chart(
    body: ChartModifyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Modify an existing Superset chart via natural language instruction."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == body.dataset_id,
            Dataset.user_id == current_user["user_id"],
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    engine = RAGEngine(db=db)
    response = await engine.modify_chart(
        dataset=dataset,
        chart_id=body.chart_id,
        instruction=body.instruction,
        user_id=str(current_user["user_id"]),
    )
    return response
