from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL


# =========================================
# LOAD EMBEDDING MODEL
# =========================================

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)


# =========================================
# GENERATE EMBEDDINGS
# =========================================

def generate_embeddings(chunks):
    """
    Convert text chunks into embeddings.
    """

    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True
    )

    return embeddings