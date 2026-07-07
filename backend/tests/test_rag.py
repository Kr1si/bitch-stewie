"""Integration test: requires dockerized Qdrant + host Ollama with bge-m3."""

from assistant.rag.ingest import ingest_text
from assistant.rag.store import collection_name, get_client, hybrid_search


def test_ingest_and_hybrid_search() -> None:
    project = "rag-selftest"
    n = ingest_text(
        "The payment service uses PostgreSQL for ledger storage. "
        "The notification service uses RabbitMQ for message delivery.",
        source="test:doc", project=project,
    )
    assert n >= 1
    hits = hybrid_search("which database stores the ledger", project=project)
    assert hits and "PostgreSQL" in hits[0]["text"]
    get_client().delete_collection(collection_name(project))
