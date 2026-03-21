"""Tool: Search DDR daily reports — semantic (ChromaDB) or SQL fallback."""

import logging
import os
from typing import Optional

from src.config import VECTORSTORE_DIR, OPENAI_API_KEY, EMBEDDING_MODEL, DB_PATH

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ddr_reports"


def _get_collection():
    """Get the ChromaDB collection with embedding function."""
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No API key for embeddings")

    client = chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    embedding_fn = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL,
    )
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def _sql_fallback_search(
    query: str,
    well: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    n_results: int = 10,
) -> str:
    """Fallback: keyword search over DDR text using SQL LIKE/contains."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)

    # Search in both summaries and activity comments
    keywords = [k.strip() for k in query.lower().split() if len(k.strip()) > 2]

    results_lines = []

    # Search 24hr summaries
    summary_q = "SELECT well, date, md_m, 'summary_24hr' as type, summary_24hr as text FROM ddr_status WHERE 1=1"
    params = []
    if well:
        summary_q += " AND well LIKE ?"
        params.append(well.replace("*", "%"))
    if date_from:
        summary_q += " AND date >= ?"
        params.append(date_from)
    if date_to:
        summary_q += " AND date <= ?"
        params.append(date_to)
    if keywords:
        kw_conditions = " OR ".join(["LOWER(summary_24hr) LIKE ?" for _ in keywords])
        summary_q += f" AND ({kw_conditions})"
        params.extend([f"%{kw}%" for kw in keywords])
    summary_q += f" LIMIT {n_results}"

    rows = con.execute(summary_q, params).fetchall()

    # Search activity comments
    act_q = "SELECT well, date, depth_m, activity_code || ' ' || 'activity' as type, comments as text FROM ddr_activities WHERE comments IS NOT NULL AND comments != ''"
    params2 = []
    if well:
        act_q += " AND well LIKE ?"
        params2.append(well.replace("*", "%"))
    if date_from:
        act_q += " AND date >= ?"
        params2.append(date_from)
    if date_to:
        act_q += " AND date <= ?"
        params2.append(date_to)
    if keywords:
        kw_conditions = " OR ".join(["LOWER(comments) LIKE ?" for _ in keywords])
        act_q += f" AND ({kw_conditions})"
        params2.extend([f"%{kw}%" for kw in keywords])
    act_q += f" LIMIT {n_results}"

    rows2 = con.execute(act_q, params2).fetchall()
    con.close()

    all_rows = rows + rows2

    if not all_rows:
        return "No matching reports found."

    for i, row in enumerate(all_rows[:n_results]):
        results_lines.append(
            f"--- Result {i + 1} (keyword match) ---\n"
            f"Well: {row[0]} | Date: {row[1]} | Depth: {row[2]}m | Type: {row[3]}\n"
            f"Text: {row[4]}\n"
        )

    return "\n".join(results_lines)


def search_daily_reports(
    query: str,
    well: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    n_results: int = 10,
) -> str:
    """Search daily drilling reports for passages matching a query.

    Uses semantic search (ChromaDB) when available, falls back to SQL keyword search.

    Args:
        query: Natural language search query
        well: Filter by well name (underscore format, e.g. '15_9_F_11_T2')
        date_from: Filter results from this date (YYYY-MM-DD)
        date_to: Filter results up to this date (YYYY-MM-DD)
        n_results: Number of results to return (default 10)

    Returns:
        Formatted search results with well, date, depth, and text passages
    """
    # Try semantic search first
    try:
        collection = _get_collection()

        where_filters = []
        if well:
            where_filters.append({"well": well})
        if date_from:
            where_filters.append({"date": {"$gte": date_from}})
        if date_to:
            where_filters.append({"date": {"$lte": date_to}})

        where = None
        if len(where_filters) == 1:
            where = where_filters[0]
        elif len(where_filters) > 1:
            where = {"$and": where_filters}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return "No matching reports found."

        output_lines = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            relevance = max(0, 1 - dist)
            output_lines.append(
                f"--- Result {i + 1} (relevance: {relevance:.2f}) ---\n"
                f"Well: {meta.get('well', 'N/A')} | "
                f"Date: {meta.get('date', 'N/A')} | "
                f"Depth: {meta.get('depth_m', 'N/A')}m | "
                f"Type: {meta.get('doc_type', 'N/A')}\n"
                f"Activity: {meta.get('activity_code', 'N/A')}\n"
                f"Text: {doc}\n"
            )
        return "\n".join(output_lines)

    except Exception as e:
        logger.info("Vector search unavailable (%s), using SQL fallback", e)
        return _sql_fallback_search(query, well, date_from, date_to, n_results)
