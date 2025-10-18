# # src/vectorstore.py
# from pathlib import Path
# import chromadb

# ROOT = Path(__file__).resolve().parents[1]
# PERSIST_DIR = ROOT / "chromadb_store"
# COLLECTION_NAME = "werize_docs"

# def get_client_and_collection():
#     """
#     Return a PersistentClient connected to the local chroma store and the collection.
#     """
#     # Use PersistentClient so we always operate on the same on-disk store
#     client = chromadb.PersistentClient(path=str(PERSIST_DIR))
#     collection = client.get_or_create_collection(name=COLLECTION_NAME)
#     return client, collection

# def retrieve(query, n_results=4):
#     """
#     Returns a list of dicts: {id, text, metadata, score}
#     """
#     _, collection = get_client_and_collection()
#     resp = collection.query(query_texts=[query], n_results=n_results)
#     ids = resp.get("ids", [[]])[0]
#     documents = resp.get("documents", [[]])[0]
#     metadatas = resp.get("metadatas", [[]])[0]
#     distances = resp.get("distances", [[]])[0] if "distances" in resp else [None] * len(ids)
#     results = []
#     for i in range(len(ids)):
#         results.append({
#             "id": ids[i],
#             "text": documents[i],
#             "metadata": metadatas[i],
#             "score": distances[i]
#         })
#     return results




# src/vectorstore.py
from pathlib import Path
import chromadb

# ---- Config ----
ROOT = Path(__file__).resolve().parents[1]
# we can keep separate vector DB directories if desired
PUBLIC_DIR = ROOT / "chromadb_store"           # public collection
INTERNAL_DIR = ROOT / "chromadb_internal"      # internal-only docs
PUBLIC_COLLECTION = "werize_docs"
INTERNAL_COLLECTION = "werize_internal_docs"

# ---- Helper: dynamic client + collection ----
def get_client_and_collection(collection_name=PUBLIC_COLLECTION, internal=False):
    """
    Returns a PersistentClient and the specified collection.
    If internal=True, it uses INTERNAL_DIR and INTERNAL_COLLECTION.
    Otherwise, it uses PUBLIC_DIR and PUBLIC_COLLECTION.
    """
    persist_path = INTERNAL_DIR if internal else PUBLIC_DIR
    persist_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(name=collection_name)
    return client, collection


# ---- Core retrieval ----
def retrieve(query, n_results=4, internal=False):
    """
    Query the chosen Chroma collection.
    If internal=True, searches in the internal collection only.
    Returns a list of dicts: {id, text, metadata, score}.
    """
    collection_name = INTERNAL_COLLECTION if internal else PUBLIC_COLLECTION
    _, collection = get_client_and_collection(collection_name=collection_name, internal=internal)
    resp = collection.query(query_texts=[query], n_results=n_results)

    ids = resp.get("ids", [[]])[0]
    documents = resp.get("documents", [[]])[0]
    metadatas = resp.get("metadatas", [[]])[0]
    distances = resp.get("distances", [[]])[0] if "distances" in resp else [None] * len(ids)

    results = []
    for i in range(len(ids)):
        results.append({
            "id": ids[i],
            "text": documents[i],
            "metadata": metadatas[i],
            "score": distances[i]
        })
    return results


# ---- Optional quick test ----
if __name__ == "__main__":
    q = input("Enter query: ")
    print("\n[Public results]")
    res_public = retrieve(q, n_results=3)
    for r in res_public:
        print("-", r["id"], "|", r["score"])

    print("\n[Internal results]")
    res_internal = retrieve(q, n_results=3, internal=True)
    for r in res_internal:
        print("-", r["id"], "|", r["score"])
