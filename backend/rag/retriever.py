import json
import os
from processors.text_preprocessor import preprocess_text

from processors.document_chunker import chunk_document

from embeddings.embedding_generator import generate_embeddings

from vectorstore.faiss_store import store_embeddings


# =========================================
# GLOBAL CHUNK STORAGE
# =========================================

CHUNKS_PATH = "rag/document_chunks.json"


def _normalize_filepath(filepath):
    if not filepath:
        return ""

    normalized_path = filepath.replace("\\", "/")

    if normalized_path.startswith("uploads/"):
        return normalized_path

    if "/uploads/" in normalized_path:
        relative_path = normalized_path.split("/uploads/", 1)[1]
        return f"uploads/{relative_path}"

    file_name = os.path.basename(normalized_path)

    if file_name:
        return f"uploads/{file_name}"

    return normalized_path


def _save_document_chunks():
    os.makedirs(
        os.path.dirname(CHUNKS_PATH),
        exist_ok=True
    )

    with open(
        CHUNKS_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            document_chunks,
            file,
            indent=4
        )


# LOAD EXISTING CHUNKS

if os.path.exists(CHUNKS_PATH):

    with open(
        CHUNKS_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        document_chunks = json.load(
            file
        )

else:

    document_chunks = []


# NORMALIZE EXISTING CHUNKS TO MAINTAIN STABLE METADATA

for index, chunk in enumerate(document_chunks):

    chunk["filepath"] = _normalize_filepath(
        chunk.get("filepath")
    )

    chunk["page_number"] = chunk.get("page_number") or "N/A"

    chunk["chunk_id"] = index

    chunk["document_id"] = chunk.get(
        "document_id"
    ) or f"doc_{index}"


_save_document_chunks()


def sync_metadata_store():
    from vectorstore.faiss_store import metadata_store, METADATA_PATH

    metadata_store.clear()

    for chunk in document_chunks:
        metadata_store.append({
            "source": chunk["filename"],
            "filename": chunk["filename"],
            "text": chunk["chunk"],
            "chunk": chunk["chunk"],
            "page_number": chunk.get("page_number") or "N/A",
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "filepath": chunk["filepath"]
        })

    os.makedirs(
        os.path.dirname(METADATA_PATH),
        exist_ok=True
    )

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            metadata_store,
            file,
            indent=4
        )


sync_metadata_store()


# =========================================
# PROCESS + INDEX DOCUMENT
# =========================================

def process_and_index_document(
    text,
    filename,
    filepath,
    page_number=None
):
    """
    Full indexing pipeline with metadata.
    """

    # =====================================
    # PREPROCESS TEXT
    # =====================================

    cleaned_text = preprocess_text(text)

    # =====================================
    # CHUNKING
    # =====================================

    chunks = chunk_document(cleaned_text)

    if not chunks:

        return []

    # =====================================
    # GENERATE EMBEDDINGS
    # =====================================

    embeddings = generate_embeddings(chunks)

    normalized_filepath = _normalize_filepath(filepath)

    chunk_records = []

    for index, chunk in enumerate(chunks):

        chunk_id = len(document_chunks) + index

        chunk_record = {
            "chunk": chunk,
            "filename": filename,
            "filepath": normalized_filepath,
            "page_number": page_number if page_number is not None else "N/A",
            "chunk_id": chunk_id,
            "document_id": f"doc_{chunk_id}"
        }

        chunk_records.append(chunk_record)

        document_chunks.append(chunk_record)

    # =====================================
    # STORE IN FAISS
    # =====================================

    store_embeddings(
        embeddings,
        chunk_records,
        filename,
        metadata_entries=chunk_records
    )

    _save_document_chunks()

    return chunks