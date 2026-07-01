"""
Pipeline orchestrator — the core AI-driven pipeline:
  1. Ingest data (file or DB)
  2. Extract schema
  3. Gemini AI schema analysis
  4. AI data selection (only meaningful columns/rows)
  5. Push to Apache Superset (create dataset + charts + dashboard)
  6. Build RAG embeddings for chatbot

This runs as a background task — dataset.status is updated at each step.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models import Dataset, Chart, ChunkEmbedding, PipelineRun

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def run_full_pipeline(
    dataset_id: str,
    mode: str,  # "upload" | "connect"
    source_path: Optional[str] = None,
    source_type: Optional[str] = None,
    connection_config: Optional[Dict[str, Any]] = None,
):
    """Entry point called from background_tasks."""
    current_step = "unknown"
    async with _Session() as db:
        try:
            # We override _start_step to track current_step
            original_start = _start_step
            async def track_start(db, ds_id, step):
                nonlocal current_step
                current_step = step
                await original_start(db, ds_id, step)
            
            # This is a bit hacky but works for the existing structure
            import app.services.pipeline_orchestrator as po
            po._start_step = track_start

            await _run(db, dataset_id, mode, source_path, source_type, connection_config)
            
            # Restore
            po._start_step = original_start
        except Exception as exc:
            logger.exception("Pipeline failed for dataset %s at step %s: %s", dataset_id, current_step, exc)
            await _finish_step(db, uuid.UUID(dataset_id), current_step, detail=str(exc), status="error")
            await _set_status(db, dataset_id, "error", error_message=str(exc))


async def _run(
    db: AsyncSession,
    dataset_id: str,
    mode: str,
    source_path,
    source_type,
    connection_config,
):
    ds_id = uuid.UUID(dataset_id)

    # ── Step 1 — Ingest ───────────────────────────────────────────────────────
    await _start_step(db, ds_id, "ingest")
    warehouse_table = None
    raw_schema = None

    if mode == "upload":
        from app.services.ingestion import IngestionService
        svc = IngestionService()
        warehouse_table, row_count, col_count, raw_schema = await svc.ingest_file(
            source_path, source_type, dataset_id
        )
        await _update_dataset(db, ds_id, {
            "warehouse_table": warehouse_table,
            "row_count": row_count,
            "column_count": col_count,
            "raw_schema": raw_schema,
            "status": "ingested",
        })
    else:  # connect
        from app.services.db_connector import ExternalDBConnector
        from app.models.schemas import DBConnectRequest
        cfg = DBConnectRequest(**connection_config)
        connector = ExternalDBConnector(cfg)
        raw_schema = await connector.extract_schema()
        # Count tables/columns
        tables = raw_schema.get("tables", [])
        col_count = sum(len(t.get("columns", [])) for t in tables)
        await _update_dataset(db, ds_id, {
            "raw_schema": raw_schema,
            "column_count": col_count,
            "status": "ingested",
        })

    await _finish_step(db, ds_id, "ingest", f"Schema extracted — {col_count} columns")

    # ── Step 2 — Schema extraction ────────────────────────────────────────────
    await _start_step(db, ds_id, "schema_extract")
    await _finish_step(db, ds_id, "schema_extract", "Schema mapped successfully")

    # ── Step 3 — Gemini AI schema analysis ───────────────────────────────────
    await _start_step(db, ds_id, "ai_schema_analysis")
    await _set_status(db, ds_id, "ai_analyzing")

    dataset = await _get_dataset(db, ds_id)
    if dataset.ai_schema:
        logger.info(f"Reusing existing AI schema analysis for dataset {ds_id}")
        ai_schema = dataset.ai_schema
    else:
        from app.services.gemini_service import GeminiService
        gemini = GeminiService()
        ai_schema = await gemini.analyze_schema(raw_schema)
        await _update_dataset(db, ds_id, {"ai_schema": ai_schema})

    await _set_status(db, ds_id, "ai_analyzing")
    await _finish_step(db, ds_id, "ai_schema_analysis",
                       f"AI selected {len(ai_schema.get('selected_columns', []))} columns, "
                       f"suggesting {len(ai_schema.get('suggested_charts', []))} charts")

    # ── Step 4 — AI data selection ────────────────────────────────────────────
    await _start_step(db, ds_id, "ai_data_selection")
    await _set_status(db, ds_id, "ai_done")

    selected_cols = [
        c["name"] for c in ai_schema.get("selected_columns", []) if c["role"] != "skip"
    ]
    suggested_charts = ai_schema.get("suggested_charts", [])

    if not selected_cols or not suggested_charts:
        await _finish_step(db, ds_id, "ai_data_selection", "No meaningful columns/charts selected", status="error")
        await _set_status(db, ds_id, "error", error_message="AI: No meaningful data found for visualization")
        return

    await _finish_step(db, ds_id, "ai_data_selection",
                       f"{len(selected_cols)} columns selected, {len(suggested_charts)} charts queued")

    # ── Step 5 — Superset push ────────────────────────────────────────────────
    await _start_step(db, ds_id, "superset_push")

    from app.services.superset_client import SupersetClient
    superset = SupersetClient()

    sync_db_uri = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    db_id = await superset.get_or_create_database(sync_db_uri)

    # For file uploads: use the warehouse table; for DB connects: create a virtual view
    if mode == "upload" and warehouse_table:
        ss_dataset_id = await superset.create_dataset(db_id, warehouse_table)
        table_ref = warehouse_table
    else:
        # For external DB: create a Superset DB connection for the external DB, use first table
        tables = raw_schema.get("tables", [])
        if not tables:
            raise ValueError("No tables found in connected database")
        table_ref = tables[0]["name"]
        ss_dataset_id = await superset.create_dataset(db_id, table_ref)

    chart_ids = []
    # Quote table name for SQL
    quoted_table = f'"{table_ref}"'
    
    for chart_spec in suggested_charts:
        # Resolve {{table}} placeholder in SQL
        sql = chart_spec.get("sql", "").replace("{{table}}", quoted_table).replace("{table}", quoted_table)
        
        y_col = chart_spec.get("y_column")
        quoted_y = f'"{y_col}"' if y_col else None
        
        sanitized_label = "".join(c if c.isalnum() or c == " " else "_" for c in (y_col or "Value")).strip()
        option_name = f"metric_{uuid.uuid4().hex[:8]}"
        metric_obj = {
            "expressionType": "SQL",
            "sqlExpression": f"SUM({quoted_y})",
            "label": sanitized_label,
            "hasCustomLabel": True,
            "optionName": option_name,
        } if quoted_y else None
        
        chart_params = {
            "viz_type": chart_spec.get("chart_type", "table"),
            "groupby": [chart_spec.get("x_column")] if chart_spec.get("x_column") else [],
            "metrics": [metric_obj] if metric_obj else [],
            "metric": metric_obj,
            "adhoc_filters": [],
            "row_limit": 1000,
            "show_legend": True,
            "rich_tooltip": True,
            "bottom_margin": "auto",
        }

        ss_chart_id = await superset.create_chart(
            datasource_id=ss_dataset_id,
            title=chart_spec["title"],
            chart_type=chart_spec["chart_type"],
            params=chart_params,
        )
        chart_ids.append(ss_chart_id)

        # Save chart record
        chart = Chart(
            dataset_id=ds_id,
            user_id=(await _get_dataset(db, ds_id)).user_id,
            superset_chart_id=ss_chart_id,
            title=chart_spec["title"],
            chart_type=chart_spec["chart_type"],
            sql_query=sql,
            ai_reasoning=chart_spec.get("reasoning", ""),
        )
        db.add(chart)

    # Create dashboard
    ds_name = (await _get_dataset(db, ds_id)).name
    ss_dashboard_id = await superset.create_dashboard(
        title=f"AI Dashboard — {ds_name}",
        chart_ids=chart_ids,
    )

    await db.commit()

    await _update_dataset(db, ds_id, {
        "superset_dataset_id": ss_dataset_id,
        "superset_dashboard_id": ss_dashboard_id,
        "status": "superset_ready",
    })
    await _finish_step(db, ds_id, "superset_push",
                       f"{len(chart_ids)} charts created, dashboard ID {ss_dashboard_id}")

    # ── Step 6 — RAG embedding ────────────────────────────────────────────────
    await _start_step(db, ds_id, "rag_embed")
    await _build_rag_embeddings(db, ds_id, ai_schema, table_ref if mode == "upload" else table_ref)
    await _finish_step(db, ds_id, "rag_embed", "RAG embeddings built successfully")


# ── RAG embedding builder ─────────────────────────────────────────────────────

async def _build_rag_embeddings(
    db: AsyncSession, dataset_id: uuid.UUID, ai_schema: Dict, table_name: str
):
    """
    Sample data rows and schema info, chunk them, embed with Gemini, store.
    """
    from app.services.gemini_service import GeminiService
    import sqlalchemy as sa

    gemini = GeminiService()

    # Build text chunks from schema info
    chunks = []

    # Chunk 1: data summary
    summary = ai_schema.get("data_summary", "")
    if summary:
        chunks.append(f"Data summary: {summary}")

    # Chunk 2: column descriptions
    for col in ai_schema.get("selected_columns", []):
        if col["role"] != "skip":
            chunks.append(
                f"Column '{col['name']}' ({col['sql_type']}) — role: {col['role']}. {col.get('reason', '')}"
            )

    # Chunk 3-N: sample data rows from warehouse
    if table_name:
        try:
            sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
            import sqlalchemy as sa_sync
            sync_engine = sa_sync.create_engine(sync_url)
            with sync_engine.connect() as conn:
                rows = conn.execute(sa_sync.text(f'SELECT * FROM "{table_name}" LIMIT 200')).fetchall()
                keys = conn.execute(sa_sync.text(f'SELECT * FROM "{table_name}" LIMIT 1')).keys()
                col_names = list(keys)
                for row in rows:
                    chunk = " | ".join(f"{col_names[i]}: {v}" for i, v in enumerate(row))
                    chunks.append(chunk)
            sync_engine.dispose()
        except Exception as e:
            logger.warning("Could not sample rows for RAG: %s", e)

    # Embed and store (batch)
    for i, chunk in enumerate(chunks):
        try:
            embedding = await gemini.embed_text(chunk[:2000])  # truncate long chunks
            emb = ChunkEmbedding(
                dataset_id=dataset_id,
                chunk_text=chunk[:4000],
                embedding=embedding,
                chunk_index=i,
            )
            db.add(emb)
        except Exception as e:
            logger.warning("Embedding failed for chunk %d: %s", i, e)

    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_dataset(db: AsyncSession, ds_id: uuid.UUID) -> Dataset:
    result = await db.execute(select(Dataset).where(Dataset.id == ds_id))
    return result.scalar_one()


async def _update_dataset(db: AsyncSession, ds_id: uuid.UUID, fields: Dict):
    ds = await _get_dataset(db, ds_id)
    for k, v in fields.items():
        setattr(ds, k, v)
    await db.commit()


async def _set_status(db, ds_id, status, error_message=None):
    ds = await _get_dataset(db, ds_id)
    ds.status = status
    if error_message:
        ds.error_message = error_message
    await db.commit()


async def _start_step(db: AsyncSession, ds_id: uuid.UUID, step: str):
    run = PipelineRun(dataset_id=ds_id, step=step, status="running")
    db.add(run)
    await db.commit()


async def _finish_step(
    db: AsyncSession, ds_id: uuid.UUID, step: str, detail: str = "", status: str = "done"
):
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.dataset_id == ds_id,
            PipelineRun.step == step,
        ).order_by(PipelineRun.started_at.desc())
    )
    run = result.scalars().first()
    if run:
        run.status = status
        run.detail = detail
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
