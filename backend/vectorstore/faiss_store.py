import faiss
import numpy as np
import os
import json

# =====================================
# PATHS
# =====================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FAISS_INDEX_PATH = os.path.join(
    BASE_DIR,
    "vectorstore",
    "faiss.index"
)

METADATA_DIR = os.path.join(
    BASE_DIR,
    "storage",
    "metadata"
)

METADATA_PATH = os.path.join(
    METADATA_DIR,
    "metadata.json"
)

os.makedirs(
    os.path.dirname(FAISS_INDEX_PATH),
    exist_ok=True
)

os.makedirs(
    METADATA_DIR,
    exist_ok=True
)

# =====================================
# LOAD OR CREATE INDEX
# =====================================

dimension = 384

if os.path.exists(FAISS_INDEX_PATH):

    faiss_index = faiss.read_index(
        FAISS_INDEX_PATH
    )

else:

    faiss_index = faiss.IndexFlatL2(
        dimension
    )

# =====================================
# LOAD METADATA
# =====================================

if os.path.exists(METADATA_PATH):

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        metadata_store = json.load(f)

else:

    metadata_store = []

# =====================================
# STORE EMBEDDINGS + METADATA
# =====================================

def store_embeddings(
    embeddings,
    chunks,
    filename,
    metadata_entries=None
):

    embeddings = np.array(
        embeddings
    ).astype("float32")

    if embeddings.ndim == 1:

        embeddings = np.expand_dims(
            embeddings,
            axis=0
        )

    if embeddings.shape[0] == 0:

        return

    faiss_index.add(
        embeddings
    )

    if metadata_entries is None:

        metadata_entries = []

        for chunk in chunks:

            metadata_entries.append({
                "source": filename,
                "filename": filename,
                "text": chunk,
                "chunk": chunk,
                "page_number": None,
                "chunk_id": None,
                "document_id": None,
                "filepath": ""
            })

    normalized_metadata = []

    for entry in metadata_entries:

        normalized_entry = dict(entry)

        normalized_entry["filename"] = normalized_entry.get(
            "filename",
            filename
        )

        normalized_entry["source"] = normalized_entry.get(
            "source",
            normalized_entry["filename"]
        )

        normalized_entry["chunk"] = normalized_entry.get(
            "chunk",
            ""
        )

        normalized_entry["text"] = normalized_entry.get(
            "text",
            normalized_entry["chunk"]
        )

        normalized_entry["page_number"] = normalized_entry.get(
            "page_number"
        )

        normalized_entry["chunk_id"] = normalized_entry.get(
            "chunk_id"
        )

        normalized_entry["document_id"] = normalized_entry.get(
            "document_id"
        )

        normalized_entry["filepath"] = normalized_entry.get(
            "filepath",
            ""
        )

        normalized_metadata.append(
            normalized_entry
        )

    metadata_store.extend(
        normalized_metadata
    )

    # SAVE FAISS INDEX

    faiss.write_index(
        faiss_index,
        FAISS_INDEX_PATH
    )

    # SAVE METADATA

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata_store,
            f,
            indent=2
        )

# =====================================
# SEARCH EMBEDDINGS
# =====================================

def search_embeddings(
    query_embedding,
    top_k=5
):

    query_embedding = np.array(
        query_embedding
    ).astype("float32")

    if query_embedding.ndim == 1:

        query_embedding = np.expand_dims(
            query_embedding,
            axis=0
        )

    actual_top_k = min(
        top_k,
        faiss_index.ntotal
    )

    if actual_top_k <= 0:

        return np.array([]), np.array([])

    distances, indices = faiss_index.search(

        query_embedding,

        actual_top_k
    )

    return distances, indices