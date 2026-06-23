from dotenv import load_dotenv
load_dotenv()
import os
import pytesseract

# =========================================
# BASE PATHS
# =========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

STORAGE_FOLDER = os.path.join(BASE_DIR, "storage")

FAISS_INDEX_PATH = os.path.join(STORAGE_FOLDER, "faiss_index")

METADATA_PATH = os.path.join(STORAGE_FOLDER, "metadata")

TEMP_IMAGE_FOLDER = os.path.join(STORAGE_FOLDER, "temp_images")


# =========================================
# TESSERACT OCR CONFIG
# =========================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# =========================================
# EMBEDDING MODEL
# =========================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# =========================================
# OLLAMA MODEL
# =========================================

OLLAMA_MODEL = "phi3:mini"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"

# =========================================
# CHUNKING CONFIG
# =========================================

CHUNK_SIZE = 200

CHUNK_OVERLAP = 40


# =========================================
# RETRIEVAL CONFIG
# =========================================

TOP_K_RESULTS = 5