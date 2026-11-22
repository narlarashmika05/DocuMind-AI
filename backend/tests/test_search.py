import pytest

from app.models import Chunk
from app.services.retrieval.dense import ScoredChunk
from app.services.retrieval.retriever import reciprocal_rank_fusion
from tests import pdf_factory

DOCS_URL = "/api/v1/documents"
SEARCH_URL = "/api/v1/search"

TOPIC_PAGES = [
    "Photosynthesis converts light energy into chemical energy stored in glucose inside chloroplasts.",
    "The French Revolution began in 1789 and transformed politics in Europe.",
    "Transformers use self-attention so every token can attend to every other token.",
]


def upload(client, headers, pages=TOPIC_PAGES, name="notes.pdf") -> int:
    files = [("files", (name, pdf_factory.text_pdf(pages), "application/pdf"))]
    return client.post(DOCS_URL, headers=headers, files=files).json()["uploaded"][0]["id"]


def search(client, headers, query, **options):
    response = client.post(SEARCH_URL, headers=headers, json={"query": query, **options})
    assert response.status_code == 200, response.text
    return response.json()["hits"]


def test_processing_indexes_chunks(client, make_user):
    headers = make_user()

    document = client.get(f"{DOCS_URL}/{upload(client, headers)}", headers=headers).json()

    assert document["status"] == "ready"
    assert document["chunk_count"] == 3
    assert document["embedding_model"] == "fake-model"
    assert document["chunk_strategy"] == "recursive"


@pytest.mark.parametrize("mode", ["dense", "keyword", "hybrid"])
def test_search_finds_the_right_page(client, make_user, mode):
    headers = make_user()
    upload(client, headers)

    hits = search(client, headers, "How does self-attention work in transformers?", mode=mode, top_k=3)

    assert hits[0]["page_number"] == 3
    assert "self-attention" in hits[0]["text"]
    assert hits[0]["document_title"]


def test_search_is_limited_to_selected_documents(client, make_user):
    headers = make_user()
    first = upload(client, headers, ["Mitochondria are the powerhouse of the cell."], "bio.pdf")
    second = upload(client, headers, ["Mitochondria appear in this second file too."], "other.pdf")

    hits = search(client, headers, "mitochondria", document_ids=[second])

    assert {h["document_id"] for h in hits} == {second}
    assert first != second


def test_users_only_search_their_own_documents(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    upload(client, alice)

    assert search(client, bob, "photosynthesis") == []
    assert search(client, alice, "photosynthesis")


def test_deleted_documents_disappear_from_search(client, make_user):
    headers = make_user()
    document_id = upload(client, headers)
    assert search(client, headers, "French Revolution")

    client.delete(f"{DOCS_URL}/{document_id}", headers=headers)

    assert search(client, headers, "French Revolution") == []


def test_reprocessing_does_not_duplicate_chunks(client, make_user):
    headers = make_user()
    document_id = upload(client, headers)

    client.post(f"{DOCS_URL}/{document_id}/reprocess", headers=headers)

    hits = search(client, headers, "photosynthesis glucose chloroplasts", top_k=10, rerank=False)
    assert len({h["chunk_id"] for h in hits}) == len(hits) == 3
    assert client.get(f"{DOCS_URL}/{document_id}", headers=headers).json()["chunk_count"] == 3


def test_search_validates_input(client, make_user):
    headers = make_user()

    assert client.post(SEARCH_URL, headers=headers, json={"query": ""}).status_code == 422
    assert client.post(SEARCH_URL, headers=headers, json={"query": "x", "mode": "magic"}).status_code == 422
    assert client.post(SEARCH_URL, json={"query": "x"}).status_code == 401


def test_reciprocal_rank_fusion_rewards_agreement():
    a, b, c = (Chunk(id=i, text=str(i)) for i in (1, 2, 3))
    dense = [ScoredChunk(a, 0.9), ScoredChunk(b, 0.8)]
    keyword = [ScoredChunk(b, 12.0), ScoredChunk(c, 5.0)]

    fused = reciprocal_rank_fusion([dense, keyword])

    assert [item.chunk.id for item in fused] == [2, 1, 3]  # b is in both lists
