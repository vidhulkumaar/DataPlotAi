"""
Gemini AI service — all calls to Gemini API.
Handles: schema analysis, column selection, chart recommendations, SQL generation, embeddings.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.api_core import exceptions
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:

    def __init__(self):
        self.use_groq = settings.USE_GROQ and settings.GROQ_API_KEY
        self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        
        if self.use_groq:
            logger.info(f"AI Service initialized with Groq ({settings.GROQ_MODEL}) via HTTP")
        else:
            logger.info(f"AI Service initialized with Gemini ({settings.GEMINI_MODEL})")

    async def _generate_with_retry(self, prompt: str, max_retries: int = 5) -> Any:
        """Helper to generate content with exponential backoff or use Groq."""
        if self.use_groq:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.GROQ_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                        },
                        timeout=60.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Mock a Gemini-like response object for compatibility
                    class MockResponse:
                        def __init__(self, text): self.text = text
                    return MockResponse(content)
            except Exception as e:
                logger.error(f"Groq generation error via HTTP: {e}")
                raise e

        # Original Gemini logic
        for i in range(max_retries):
            try:
                return await asyncio.to_thread(self.gemini_model.generate_content, prompt)
            except exceptions.ResourceExhausted as e:
                if i == max_retries - 1:
                    raise e
                wait_time = (2 ** i) + 1
                logger.warning(f"Gemini quota exceeded (429). Retrying in {wait_time}s... (Attempt {i+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Gemini generation error: {e}")
                raise e

    # ── Schema Analysis ──────────────────────────────────────────────────────

    async def analyze_schema(self, raw_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send the full schema to Gemini and receive:
        - selected columns with role (metric/dimension/skip)
        - suggested charts (up to 8)
        - key insights about the data
        """
        prompt = f"""
You are an expert data analyst. Analyze the following database schema and return a JSON object.

SCHEMA:
{json.dumps(raw_schema, indent=2)}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "selected_columns": [
    {{
      "name": "column_name",
      "role": "metric|dimension|skip",
      "reason": "brief reason",
      "sql_type": "numeric|categorical|date|boolean|id"
    }}
  ],
  "suggested_charts": [
    {{
      "title": "Chart Title",
      "chart_type": "bar|line|pie|area|scatter|table|big_number",
      "x_column": "column_name or null",
      "y_column": "column_name or null",
      "group_by": "column_name or null",
      "aggregation": "SUM|COUNT|AVG|MAX|MIN|COUNT_DISTINCT",
      "sql": "SELECT ... FROM {{table}} ...",
      "reasoning": "why this chart is meaningful"
    }}
  ],
  "key_metrics": ["list", "of", "important", "column", "names"],
  "time_column": "date/time column name or null",
  "primary_dimension": "main categorical column for segmentation or null",
  "data_summary": "2-3 sentence summary of what this data represents",
  "is_valid_for_analytics": true
}}

Rules:
- Skip columns that are: primary keys (UUIDs/IDs with high cardinality), internal codes, passwords, tokens
- Mark numeric columns measuring quantities as "metric"
- Mark categorical/date columns used for grouping as "dimension"
- Suggest 4-8 charts maximum — only suggest charts that would be MEANINGFUL and INSIGHTFUL
- If there are 0 rows, 0 columns, or no meaningful data, set is_valid_for_analytics: false and return empty arrays
- SQL queries should use {{table}} as a placeholder for the actual table name
"""

        response = await self._generate_with_retry(prompt)
        text = response.text.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Gemini returned invalid JSON: %s\n%s", e, text[:500])
            raise ValueError(f"Gemini returned invalid JSON: {e}")

        if not result.get("is_valid_for_analytics", True):
            raise ValueError("AI determined dataset has insufficient meaningful data for analytics")

        return result

    # ── SQL Generation ────────────────────────────────────────────────────────

    async def generate_sql(
        self,
        question: str,
        schema: Dict[str, Any],
        table_name: str,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate SQL + chart type for a natural language question.
        Returns: {sql, chart_type, title, explanation, x_col, y_col}
        """
        history_str = ""
        if history:
            history_str = "\nConversation history:\n" + "\n".join(
                [f"{m['role']}: {m['content']}" for m in history[-6:]]
            )

        prompt = f"""
You are a SQL expert and data analyst working with a table named `{table_name}`.

SCHEMA:
{json.dumps(schema.get("selected_columns", []), indent=2)}
{history_str}

USER QUESTION: {question}

Return ONLY valid JSON with this structure:
{{
  "sql": "SELECT ... FROM {table_name} ...",
  "chart_type": "bar|line|pie|area|scatter|table|big_number",
  "title": "Descriptive chart title",
  "x_col": "x-axis column name or null",
  "y_col": "y-axis / value column name",
  "group_by": "grouping column or null",
  "explanation": "Plain English explanation of the result",
  "is_chart_request": true/false
}}

Rules:
- Use ONLY columns that exist in the schema above
- Always use LIMIT 1000 unless the user asked for all data
- Use appropriate aggregations (SUM, COUNT, AVG etc)
- If the question doesn't require a chart (e.g. "what is the total?"), set is_chart_request: false
- Never generate DROP, DELETE, UPDATE, INSERT or DDL statements
"""

        response = await self._generate_with_retry(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text.strip())

    # ── Chart Modification ────────────────────────────────────────────────────

    async def plan_chart_modification(
        self, current_chart: Dict[str, Any], instruction: str
    ) -> Dict[str, Any]:
        """
        Decide how to modify an existing chart based on the instruction.
        Returns updated chart params.
        """
        prompt = f"""
You are modifying an Apache Superset chart.

CURRENT CHART:
{json.dumps(current_chart, indent=2)}

USER INSTRUCTION: {instruction}

Return ONLY valid JSON:
{{
  "viz_type": "new superset viz_type (e.g. bar, line, pie, echarts_timeseries_bar, etc.)",
  "params_override": {{ any Superset params_override dict }},
  "new_title": "new chart title or null to keep existing",
  "explanation": "what changed and why"
}}
"""
        response = await self._generate_with_retry(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    # ── RAG Answer Generation ─────────────────────────────────────────────────

    async def generate_rag_answer(
        self,
        question: str,
        context_chunks: List[str],
        data_summary: str,
        history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate a grounded natural-language answer using retrieved data chunks.
        """
        context = "\n\n".join(context_chunks[:8])
        history_str = ""
        if history:
            history_str = "\nPrevious conversation:\n" + "\n".join(
                [f"{m['role']}: {m['content']}" for m in history[-4:]]
            )

        prompt = f"""
You are a data analytics assistant. Answer the user's question using ONLY the data provided below.
Do NOT make up numbers. If the data doesn't contain the answer, say so clearly.

DATA SUMMARY: {data_summary}

RETRIEVED DATA CONTEXT:
{context}
{history_str}

USER QUESTION: {question}

Provide a clear, concise answer. If numbers are involved, be precise. 
If the user asked for a chart or visualization, acknowledge that you're generating it.
"""
        response = await self._generate_with_retry(prompt)
        return response.text.strip()

    # ── Embeddings ────────────────────────────────────────────────────────────

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a text chunk."""
        result = await asyncio.to_thread(
            genai.embed_content,
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a search query."""
        result = await asyncio.to_thread(
            genai.embed_content,
            model=self.embedding_model,
            content=query,
            task_type="retrieval_query",
        )
        return result["embedding"]
