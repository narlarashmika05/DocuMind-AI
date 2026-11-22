# Module 4 – Text Chunking, Embeddings and Vector Search

## Objective
Split every processed document into retrievable passages ("chunks"), turn each chunk into a vector with a multilingual embedding model, store the vectors in ChromaDB, and search them — by meaning (dense), by keywords (BM25), or both (hybrid), with optional cross-encoder reranking.

## Concepts

### Tokens
Models do not read words; they read **tokens** (sub-word pieces). "unbelievable" → `un`, `believ`, `able`. Telugu words usually split into more tokens than English words. All chunk sizes in this project are measured in the **embedding model's own tokens**, so a chunk never exceeds what the model can read.

### Chunking, chunk size and overlap
- **Why chunk?** Embedding models read at most 256–512 tokens; anything longer is silently cut off. A focused passage also matches a specific question better than a whole page.
- **Chunk size (300 tokens):** too small → a chunk lacks context ("it increased by 5%" — what did?). Too large → one vector mixes several topics and matches nothing well, and the LLM prompt gets long.
- **Overlap (50 tokens):** consecutive chunks share their boundary sentences, so an idea that straddles a boundary appears complete in at least one chunk.
- **Chunks never cross pages** → every citation points to one exact page.
- **References sections are dropped** — bibliographies are full of keywords and pollute search.

| Strategy | How | Pros / cons |
|---|---|---|
| `fixed` | Windows of N tokens over words | Simple baseline; cuts sentences in half |
| `recursive` (default) | Paragraphs → sentences → words, packed up to N tokens | Keeps sentences whole |
| `sentence` | LlamaIndex `SentenceSplitter` | Mature implementation; comparable to recursive |

### Embeddings
An embedding model (a Transformer encoder) maps text to a vector of e.g. 768 numbers so that **similar meaning → similar direction**. We **normalise** vectors to length 1, so cosine similarity = dot product.

| Key | Model | Dim | Max tokens | Languages | Size |
|---|---|---|---|---|---|
| `minilm-en` | all-MiniLM-L6-v2 | 384 | 256 | English only | 90 MB |
| `multilingual-e5-base` (default) | intfloat/multilingual-e5-base | 768 | 512 | ~100 incl. Telugu | 1.1 GB |
| `bge-m3` | BAAI/bge-m3 | 1024 | 8192 | 100+ | 2.2 GB |

E5 models need the prefixes `query: ` and `passage: ` — they were trained that way (asymmetric search: short questions vs long passages).

### Vector database (ChromaDB)
Stores vectors with metadata and finds nearest neighbours quickly using an **HNSW** graph (approximate nearest-neighbour search: logarithmic instead of linear time). One **collection per embedding model**, because vectors from different models are not comparable. Every query filters `user_id` → access isolation.

**MySQL stays the source of truth** for chunk text; Chroma stores only `id → vector + metadata`. The index can be rebuilt any time.

### Dense vs keyword vs hybrid search
- **Dense:** understands paraphrases ("car" ≈ "automobile") and works across languages, but can miss exact terms (model names, numbers).
- **Keyword (BM25):** scores word overlap, weighting rare words higher (IDF) and normalising for length. Great for exact terms; useless across languages.
- **Hybrid:** run both, merge with **Reciprocal Rank Fusion**: `score = Σ 1/(60 + rank)`. Uses ranks, not raw scores, because the two score scales are incomparable.

### Reranking
A **bi-encoder** (embedding model) encodes question and passage separately → fast but approximate. A **cross-encoder** reads them *together* → much more accurate but slow. So: fetch 20 candidates cheaply, rerank only those, keep the top 5. The reranker outputs a 0–1 relevance probability, which Module 5 uses to refuse answering from irrelevant context.

## Workflow
```
pipeline (after Module 3 extraction):
  pages + tables (+ figure descriptions from Module 7)
    → chunk_document(strategy, size, overlap)        → chunks table (MySQL)
    → embedder.embed_documents("title\n" + chunk)     → batches of vectors
    → ChromaDB collection "chunks_<model>"  (id = chunk id, metadata = user/doc/page)
query:
  question → dense (Chroma, user filter) ┐
           → BM25 (user's chunks)        ┴→ RRF → top 20 → cross-encoder → top k
```

## Files
| File | Purpose |
|---|---|
| `app/services/embeddings/registry.py` | Supported embedding models and their properties |
| `app/services/embeddings/encoder.py` | Loads a model once per process; prefixes; token counting |
| `app/services/chunking/chunker.py` | The three chunking strategies, references removal, table splitting |
| `app/services/vectorstore/chroma_store.py` | ChromaDB wrapper with per-user filtering |
| `app/services/indexing.py` | Chunk → embed → store, called by the pipeline |
| `app/services/retrieval/{dense,bm25,reranker,retriever}.py` | Search modes, RRF, reranking |
| `app/api/v1/routes/search.py` | `POST /api/v1/search` |
| `frontend/src/pages/SearchPage.jsx` | Search UI with mode and rerank switches |
| `tests/fakes.py` | Tiny fake embedder/reranker so tests run offline in seconds |

## Configuration (`backend/.env`)
```
EMBEDDING_MODEL=multilingual-e5-base   # minilm-en | multilingual-e5-base | bge-m3
CHUNK_STRATEGY=recursive               # fixed | recursive | sentence
CHUNK_SIZE_TOKENS=300
CHUNK_OVERLAP_TOKENS=50
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
PRELOAD_MODELS=true
```
After changing the model or strategy, **reprocess** documents (the UI shows which model each document was indexed with).

## Run and test
```powershell
cd backend; .\.venv\Scripts\Activate.ps1
alembic upgrade head
pytest -v                     # chunking, search, isolation tests (fake models, offline)
uvicorn app.main:app --reload # first start downloads ~1.2 GB of models in the background
```
Upload a paper → wait for **Ready** → open **Search** → ask a question in English, then the same in Telugu → switch between Hybrid / Semantic / Keyword and toggle reranking to see the difference.

**Sample request**
```http
POST /api/v1/search
Authorization: Bearer <token>
Content-Type: application/json

{"query": "What optimizer was used for training?", "mode": "hybrid", "rerank": true, "top_k": 3}
```
```json
{"query": "What optimizer was used for training?", "mode": "hybrid", "latency_ms": 184.2,
 "hits": [{"chunk_id": 41, "document_id": 3, "document_title": "Attention Is All You Need",
           "page_number": 7, "element_type": "text", "text": "We used the Adam optimizer with β1 = 0.9 ...",
           "score": 0.9731}]}
```

## Common errors
| Problem | Fix |
|---|---|
| First upload/search very slow | Models are downloading/loading (one-time). Watch the uvicorn log for "Models loaded". |
| `OSError: ... couldn't connect to huggingface.co` | No internet on first run. Models are cached in `%USERPROFILE%\.cache\huggingface` after one successful download. |
| Search returns nothing | Documents not **Ready**, or indexed with a different `EMBEDDING_MODEL` → reprocess. |
| High RAM use | e5-base (~1.1 GB) + reranker + later NLI model. Use `minilm-en` for English-only experiments. |
| Telugu search works in Semantic but not Keyword mode | Expected: BM25 matches words, and Telugu words don't occur in English documents. Module 6 translates the query for BM25. |

## Interview questions
1. What is an embedding? Why do similar sentences get similar vectors?
2. Why chunk documents? How do you choose chunk size and overlap?
3. Cosine similarity vs dot product vs Euclidean distance — when are they equivalent?
4. What is HNSW and why is it approximate?
5. Why keep chunk text in MySQL instead of only in the vector DB?
6. Dense vs sparse (BM25) retrieval — strengths and weaknesses of each?
7. Explain Reciprocal Rank Fusion. Why not just add the scores?
8. Bi-encoder vs cross-encoder — why use both?
9. Why do E5 models need "query:" / "passage:" prefixes?
10. How do you enforce that users only retrieve their own documents in a shared vector index?
