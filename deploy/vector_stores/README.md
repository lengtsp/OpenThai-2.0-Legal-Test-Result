# Vector-store backends for OpenThai Legal RAG

The application keeps lexical retrieval in-process (Python BM25 and SQLite
FTS5 trigram) and uses one interchangeable dense-vector backend. Start only the
backend you want:

```bash
docker compose --profile qdrant up -d
docker compose --profile chroma up -d
docker compose --profile milvus up -d
```

Then configure port 8083:

```bash
# Qdrant server
export RAG_VECTOR_BACKEND=qdrant
export RAG_QDRANT_URL=http://127.0.0.1:6333

# Chroma server
export RAG_VECTOR_BACKEND=chroma
export RAG_CHROMA_HOST=127.0.0.1
export RAG_CHROMA_PORT=8004

# Milvus standalone
export RAG_VECTOR_BACKEND=milvus
export RAG_MILVUS_URI=http://127.0.0.1:19530
```

For a small local test, omit each server URL and use the embedded paths already
supported by `server.py`: Qdrant Local, Chroma PersistentClient, or Milvus
Lite. The web service currently uses Qdrant Local so no Docker daemon is
required.

The containers bind to loopback only. This is deliberate: the default
development configurations do not provide production authentication, TLS,
high availability, backup, or disaster recovery.
