"""Build ChromaDB vector store from DDR text corpus."""

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from src.config import VECTORSTORE_DIR, OPENAI_API_KEY, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ddr_reports"
BATCH_SIZE = 100


def get_chroma_client(persist_dir: Optional[Path] = None) -> chromadb.ClientAPI:
    """Get a ChromaDB persistent client."""
    persist_dir = persist_dir or VECTORSTORE_DIR
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def _get_openai_embedding_fn():
    """Get OpenAI embedding function for ChromaDB."""
    import os
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
    api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not set. Set it in .env or as environment variable."
        )
    return OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL,
    )


def build_vectorstore(
    text_docs: list[dict],
    persist_dir: Optional[Path] = None,
) -> int:
    """Build ChromaDB collection from DDR text documents.

    Args:
        text_docs: List of dicts with keys: well, date, depth_m, doc_type, text,
                   and optionally activity_code
        persist_dir: ChromaDB persistence directory

    Returns:
        Number of documents indexed
    """
    if not text_docs:
        logger.warning("No text documents to index")
        return 0

    client = get_chroma_client(persist_dir)
    embedding_fn = _get_openai_embedding_fn()

    # Delete existing collection to rebuild
    try:
        client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Prepare documents in batches
    total = len(text_docs)
    logger.info("Indexing %d text documents into ChromaDB...", total)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = text_docs[batch_start : batch_start + BATCH_SIZE]

        ids = []
        documents = []
        metadatas = []

        for i, doc in enumerate(batch):
            doc_id = f"{doc['well']}_{doc['date']}_{doc['doc_type']}_{batch_start + i}"
            ids.append(doc_id)
            documents.append(doc["text"])
            metadatas.append({
                "well": doc["well"],
                "date": doc["date"],
                "depth_m": doc.get("depth_m") or 0.0,
                "doc_type": doc["doc_type"],
                "activity_code": doc.get("activity_code", ""),
            })

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

        if (batch_start + BATCH_SIZE) % 1000 == 0 or batch_start + BATCH_SIZE >= total:
            logger.info(
                "Indexed %d / %d documents",
                min(batch_start + BATCH_SIZE, total),
                total,
            )

    logger.info("Vector store built with %d documents", total)
    return total
