| Stage                           | Script            | What It Does                                                                    | Output                         |
| ------------------------------- | ----------------- | ------------------------------------------------------------------------------- | ------------------------------ |
| **1️⃣ Ingestion**               | `ingest.py`       | Reads `.txt` and `.pdf`, cleans & splits text into chunks                       | `data/chunks_preview.json`     |
| **2️⃣ Embedding**               | `embedding.py`    | Converts chunks → embeddings (SentenceTransformers) → stores in Chroma          | `chromadb_store/`              |
| **3️⃣ Retrieval**               | `vectorstore.py`  | Utility functions for `query()`, filtering by metadata                          | used by `rag_agent.py`         |
| **4️⃣ Generation (RAG)**        | `rag_agent.py`    | Takes a query → retrieves top-k docs → sends to LLM → generates grounded answer | printed/returned answer        |
| **5️⃣ Reflection/Verification** | `verifier.py`     | Optional evaluator agent that re-checks RAG output vs source docs               | confidence score or correction |
| **6️⃣ External Data Loader**    | `external_doc.py` | Fetches live PDFs or new company documents for re-indexing                      | updated `data/` folder         |



  D:/.venv/Scripts/Activate.ps1 
What is the due date on INV-2025-0815?