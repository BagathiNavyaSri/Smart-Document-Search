import numpy as np
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer

from vectorstore.faiss_store import search_embeddings
from rag.retriever import document_chunks

# =====================================
# LOAD EMBEDDING MODEL
# =====================================

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


keyword_index = {
    "version": None,
    "vectorizer": None,
    "matrix": None
}


def _build_keyword_index():
    current_version = len(document_chunks)

    if (
        keyword_index["version"] == current_version
        and keyword_index["vectorizer"] is not None
        and keyword_index["matrix"] is not None
    ):
        return keyword_index["vectorizer"], keyword_index["matrix"]

    corpus = [
        chunk["chunk"]
        for chunk in document_chunks
    ]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        lowercase=True,
        stop_words="english"
    )

    matrix = vectorizer.fit_transform(corpus)

    keyword_index["version"] = current_version
    keyword_index["vectorizer"] = vectorizer
    keyword_index["matrix"] = matrix

    return vectorizer, matrix


# =========================================
# HYBRID SEMANTIC SEARCH
# =========================================

def retrieve_relevant_chunks(
    query,
    top_k=10,
    allowed_filenames=None
):
    if not document_chunks:
        return []

    # If an explicit active file list is provided, and it's empty,
    # there are no eligible documents to search.
    if allowed_filenames is not None and len(allowed_filenames) == 0:
        return []

    query_embedding = embedding_model.encode(
        query,
        convert_to_numpy=True
    )

    query_embedding = np.array(
        [query_embedding]
    ).astype("float32")

    semantic_results_k = max(top_k * 2, 10)

    distances, indices = search_embeddings(
        query_embedding,
        semantic_results_k
    )

    query_text = (query or "").strip().lower()
    query_tokens = re.findall(
        r"[A-Za-z0-9_-]+",
        query_text
    )

    vectorizer, tfidf_matrix = _build_keyword_index()
    keyword_query = vectorizer.transform([query_text])
    keyword_scores = tfidf_matrix.dot(keyword_query.T).toarray().ravel()

    combined_results = {}

    for rank, chunk_index in enumerate(indices[0]):

        chunk_index = int(chunk_index)

        if (
            chunk_index < 0
            or chunk_index >= len(document_chunks)
        ):
            continue

        chunk_data = document_chunks[chunk_index]

        # Active-file filtering: if allowed_filenames is provided,
        # skip any chunk that does not belong to an active file.
        if allowed_filenames is not None:
            if chunk_data.get("filename") not in allowed_filenames:
                continue
        chunk_text = chunk_data["chunk"]

        semantic_similarity = float(
            max(0.0, 1.0 / (1.0 + float(distances[0][rank])))
        )

        semantic_confidence = min(
            100.0,
            max(0.0, semantic_similarity * 100.0)
        )

        keyword_score = float(
            keyword_scores[chunk_index]
            if chunk_index < len(keyword_scores)
            else 0.0
        )

        keyword_confidence = min(
            100.0,
            max(0.0, keyword_score * 100.0)
        )

        phrase_boost = 15.0 if query_text and query_text in chunk_text.lower() else 0.0

        exact_matches = sum(
            1 for token in query_tokens if token in chunk_text.lower()
        )

        identifier_boost = min(
            10.0,
            exact_matches * 2.0
        )

        technical_boost = min(
            10.0,
            sum(1 for token in query_tokens if token.isdigit() or len(token) >= 6) * 2.0
        )

        final_confidence = (
            semantic_confidence * 0.60
            + keyword_confidence * 0.40
            + phrase_boost
            + identifier_boost
            + technical_boost
        )

        final_confidence = min(
            100.0,
            max(0.0, round(final_confidence, 2))
        )

        chunk_key = (
            chunk_data.get("filename"),
            chunk_data.get("page_number"),
            chunk_text
        )

        combined_results[chunk_key] = {
            "source": chunk_data["filename"],
            "filename": chunk_data["filename"],
            "filepath": chunk_data.get("filepath"),
            "page_number": chunk_data.get("page_number") or "N/A",
            "chunk": chunk_text,
            "chunk_id": chunk_data.get("chunk_id"),
            "document_id": chunk_data.get("document_id"),
            "semantic_score": semantic_confidence,
            "keyword_score": keyword_confidence,
            "confidence": final_confidence
        }

    keyword_top_k = max(top_k * 3, 10)

    keyword_candidates = sorted(
        enumerate(keyword_scores),
        key=lambda item: item[1],
        reverse=True
    )[:keyword_top_k]

    for chunk_index, keyword_score in keyword_candidates:

        chunk_data = document_chunks[chunk_index]

        if allowed_filenames is not None:
            if chunk_data.get("filename") not in allowed_filenames:
                continue
        chunk_text = chunk_data["chunk"]

        keyword_confidence = min(
            100.0,
            max(0.0, float(keyword_score) * 100.0)
        )

        if keyword_confidence <= 0:
            continue

        phrase_boost = 15.0 if query_text and query_text in chunk_text.lower() else 0.0

        exact_matches = sum(
            1 for token in query_tokens if token in chunk_text.lower()
        )

        identifier_boost = min(
            10.0,
            exact_matches * 2.0
        )

        technical_boost = min(
            10.0,
            sum(1 for token in query_tokens if token.isdigit() or len(token) >= 6) * 2.0
        )

        chunk_key = (
            chunk_data.get("filename"),
            chunk_data.get("page_number"),
            chunk_text
        )

        if chunk_key not in combined_results:
            combined_results[chunk_key] = {
                "source": chunk_data["filename"],
                "filename": chunk_data["filename"],
                "filepath": chunk_data.get("filepath"),
                "page_number": chunk_data.get("page_number") or "N/A",
                "chunk": chunk_text,
                "chunk_id": chunk_data.get("chunk_id"),
                "document_id": chunk_data.get("document_id"),
                "semantic_score": 0.0,
                "keyword_score": keyword_confidence,
                "confidence": round(
                    min(
                        100.0,
                        max(0.0, keyword_confidence + phrase_boost + identifier_boost + technical_boost)
                    ),
                    2
                )
            }
        else:
            existing_item = combined_results[chunk_key]
            updated_confidence = (
                existing_item["semantic_score"] * 0.6
                + keyword_confidence * 0.4
                + phrase_boost
                + identifier_boost
                + technical_boost
            )
            existing_item["keyword_score"] = keyword_confidence
            existing_item["confidence"] = round(
                min(100.0, max(0.0, updated_confidence)),
                2
            )

    retrieved_results = list(combined_results.values())
    retrieved_results.sort(
        key=lambda item: item["confidence"],
        reverse=True
    )

    return retrieved_results[:top_k]