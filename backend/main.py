from typing import List

from fastapi import FastAPI, Form
from fastapi import Depends
from fastapi import UploadFile, File
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from database.db import engine
from database.db import SessionLocal

from database.models import (
    Base,
    User,
    UploadedFile,
    ChatHistory
)

from database.schemas import (
    UserCreate,
    UserLogin,
    ChatRequest
)

from auth.auth_handler import (
    hash_password,
    verify_password,
    create_access_token
)

from utils.file_utils import save_uploaded_file
from utils.document_manager import process_document

from rag.retriever import (
    process_and_index_document
)

from rag.query_engine import (
    retrieve_relevant_chunks
)

from rag.gemini_engine import (
    generate_ai_response
)

import os
import re
import json
from fastapi.staticfiles import StaticFiles

from database.db import ensure_chat_history_schema


# =========================================
# CREATE DATABASE TABLES
# =========================================

Base.metadata.create_all(bind=engine)
ensure_chat_history_schema()


# =========================================
# FASTAPI APP
# =========================================

app = FastAPI(
    title="Smart AI Document Search System"
)
# =========================================
# SERVE UPLOADED FILES
# =========================================

app.mount(

    "/uploads",

    StaticFiles(directory="uploads"),

    name="uploads"
)


# =========================================
# CORS
# =========================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# =========================================
# DATABASE SESSION
# =========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


def _normalize_source_entry(source):
    if not isinstance(source, dict):
        return {
            "filename": "Unknown File",
            "page_number": "N/A",
            "chunk": "",
            "confidence": 0,
            "filepath": "",
            "source_url": ""
        }

    filename = source.get("filename") or "Unknown File"

    page_number = source.get("page_number")
    if page_number in (None, ""):
        page_number = "N/A"

    filepath = source.get("filepath") or ""
    normalized_filepath = filepath.replace("\\", "/") if isinstance(filepath, str) else ""

    if normalized_filepath.startswith("uploads/"):
        source_url = f"/{normalized_filepath}"
    elif "/uploads/" in normalized_filepath:
        relative_path = normalized_filepath.split("/uploads/", 1)[1]
        source_url = f"/uploads/{relative_path}"
    elif normalized_filepath:
        source_url = f"/uploads/{os.path.basename(normalized_filepath)}"
    else:
        source_url = ""

    try:
        confidence = round(float(source.get("confidence", 0)), 2)
    except (TypeError, ValueError):
        confidence = 0

    confidence = max(0, min(100, confidence))

    return {
        "filename": filename,
        "page_number": page_number,
        "chunk": (source.get("chunk") or "").strip(),
        "confidence": confidence,
        "filepath": normalized_filepath,
        "source_url": source_url,
        "chunk_id": source.get("chunk_id"),
        "document_id": source.get("document_id")
    }


def _deduplicate_sources(raw_sources):
    normalized_sources = []
    seen_keys = set()

    for source in raw_sources:
        normalized = _normalize_source_entry(source)
        preview = normalized["chunk"]
        if preview:
            preview = preview[:200]
        page_number = normalized["page_number"]
        key = (
            normalized["filename"],
            str(page_number),
            preview
        )

        if key in seen_keys:
            continue

        seen_keys.add(key)
        normalized_sources.append(normalized)

    return normalized_sources


def _serialize_chat_entry(chat):
    raw_sources = []
    try:
        raw_sources = json.loads(chat.sources_json or "[]")
    except json.JSONDecodeError:
        raw_sources = []

    normalized_sources = _deduplicate_sources(raw_sources)

    filenames = []
    page_numbers = []

    for source in normalized_sources:
        if source["filename"] not in filenames:
            filenames.append(source["filename"])
        page_number = source["page_number"]
        if page_number not in page_numbers:
            page_numbers.append(page_number)

    return {
        "id": chat.id,
        "question": chat.question,
        "answer": chat.answer,
        "confidence_score": float(chat.confidence_score or 0),
        "source_filename": chat.source_filename or ", ".join(filenames),
        "source_page_number": chat.source_page_number or ", ".join([str(item) for item in page_numbers]),
        "sources": normalized_sources,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "timestamp": chat.created_at.isoformat() if chat.created_at else None
    }


# =========================================
# TEST ROUTE
# =========================================

@app.get("/")
def home():

    return {

        "message":
        "Smart AI Document Search Backend Running"
    }


# =========================================
# USER SIGNUP
# =========================================

@app.post("/signup")
def signup(

    user: UserCreate,

    db: Session = Depends(get_db)
):

    # =====================================
    # EMPTY FIELD VALIDATION
    # =====================================

    if (

        not user.username or
        not user.email or
        not user.password
    ):

        raise HTTPException(

            status_code=400,

            detail="All fields are required"
        )

    # =====================================
    # REMOVE EXTRA SPACES
    # =====================================

    username = user.username.strip()

    email = user.email.strip()

    password = user.password.strip()

    # =====================================
    # USERNAME VALIDATION
    # =====================================

    if len(username) < 3:

        raise HTTPException(

            status_code=400,

            detail=
            "Username must contain at least 3 characters"
        )

    # =====================================
    # EMAIL VALIDATION
    # =====================================

    email_regex = r"^[^@]+@[^@]+\.[^@]+$"

    if not re.match(email_regex, email):

        raise HTTPException(

            status_code=400,

            detail="Invalid email format"
        )

    # =====================================
    # PASSWORD VALIDATION
    # =====================================

    if len(password) < 6:

        raise HTTPException(

            status_code=400,

            detail=
            "Password must contain at least 6 characters"
        )

    # =====================================
    # PASSWORD MUST CONTAIN LETTERS
    # =====================================

    if not any(char.isalpha() for char in password):

        raise HTTPException(

            status_code=400,

            detail=
            "Password must contain letters"
        )

    # =====================================
    # CHECK DUPLICATE EMAIL
    # =====================================

    existing_user = db.query(User).filter(

        User.email == email

    ).first()

    if existing_user:

        raise HTTPException(

            status_code=400,

            detail="Email already registered"
        )

    # =====================================
    # HASH PASSWORD
    # =====================================

    hashed_password = hash_password(password)

    # =====================================
    # CREATE USER
    # =====================================

    new_user = User(

        username=username,

        email=email,

        password=hashed_password
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)

    return {

        "message":
        "User created successfully"
    }


# =========================================
# USER LOGIN
# =========================================

@app.post("/login")
def login(

    user: UserLogin,

    db: Session = Depends(get_db)
):

    # =====================================
    # EMPTY FIELD VALIDATION
    # =====================================

    if (

        not user.email or
        not user.password
    ):

        raise HTTPException(

            status_code=400,

            detail="All fields are required"
        )

    # =====================================
    # CHECK USER
    # =====================================

    existing_user = db.query(User).filter(

        User.email == user.email

    ).first()

    if not existing_user:

        raise HTTPException(

            status_code=401,

            detail="Invalid email or password"
        )

    # =====================================
    # VERIFY PASSWORD
    # =====================================

    valid_password = verify_password(

        user.password,

        existing_user.password
    )

    if not valid_password:

        raise HTTPException(

            status_code=401,

            detail="Invalid email or password"
        )

    # =====================================
    # CREATE TOKEN
    # =====================================

    access_token = create_access_token({

        "sub": existing_user.email
    })

    return {

        "access_token": access_token,

        "token_type": "bearer",

        "username": existing_user.username,

        "email": existing_user.email
    }


# =========================================
# FILE UPLOAD API
# =========================================

@app.post("/upload")
async def upload_file(

    email: str = Form(...),

    file: List[UploadFile] = File(...),

    db: Session = Depends(get_db)
):

    user = db.query(User).filter(

        User.email == email

    ).first()

    if not user:

        raise HTTPException(

            status_code=404,

            detail="User not found"
        )

    upload_results = []

    for upload_file in file:

        try:

            file_size = str(upload_file.size)

            saved_file_path = save_uploaded_file(upload_file)

            relative_file_path = saved_file_path.replace(
                "\\",
                "/"
            ).split("uploads/")[-1]

            relative_file_path = f"uploads/{relative_file_path}"

            file_extension = os.path.splitext(
                upload_file.filename
            )[1]

            # =====================================
            # CHECK DUPLICATE FILE
            # =====================================

            existing_file = db.query(UploadedFile).filter(

                UploadedFile.filename == upload_file.filename,

                UploadedFile.filesize == file_size,

                UploadedFile.owner_id == user.id

            ).first()

            if existing_file:

                upload_results.append({

                    "filename": upload_file.filename,

                    "success": False,

                    "error": "File already uploaded"
                })

                continue

            # =====================================
            # SAVE FILE INFO
            # =====================================

            new_file = UploadedFile(
                owner_id=user.id,

                filename=upload_file.filename,

                filepath=relative_file_path,

                filetype=file_extension,

                filesize=file_size
            )

            db.add(new_file)

            db.commit()

            db.refresh(new_file)

            # =====================================
            # PROCESS DOCUMENT
            # =====================================

            processed_content = process_document(
                saved_file_path
            )

            # =====================================
            # INDEX DOCUMENT
            # =====================================

            all_chunks = []

            if isinstance(processed_content, list):

                for page_data in processed_content:

                    page_text = page_data["text"]

                    page_number = page_data["page_number"]

                    chunks = process_and_index_document(

                        text=page_text,

                        filename=upload_file.filename,

                        filepath=saved_file_path,

                        page_number=page_number
                    )

                    all_chunks.extend(chunks)

            else:

                chunks = process_and_index_document(

                    text=processed_content,

                    filename=upload_file.filename,

                    filepath=saved_file_path
                )

                all_chunks.extend(chunks)

            upload_results.append({

                "filename": upload_file.filename,

                "success": True,

                "total_chunks": len(all_chunks)
            })

        except Exception as exc:

            upload_results.append({

                "filename": getattr(upload_file, "filename", "Unknown File"),

                "success": False,

                "error": str(exc)
            })

    return {

        "uploads": upload_results
    }


# =========================================
# AI QUESTION ANSWERING
# =========================================

@app.post("/ask")
def ask_question(

    request: ChatRequest,

    db: Session = Depends(get_db)
):

    # Determine the current active files for this user (files visible in the UI)
    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user_files = db.query(UploadedFile).filter(
        UploadedFile.owner_id == existing_user.id
    ).all()

    allowed_filenames = [f.filename for f in user_files]

    retrieved_chunks = retrieve_relevant_chunks(
        request.question,
        top_k=5,
        allowed_filenames=allowed_filenames
    )

    normalized_chunks = _deduplicate_sources(retrieved_chunks)

    ai_response = generate_ai_response(
        request.question,
        normalized_chunks
    )

    average_confidence = round(
        sum(
            item["confidence"]
            for item in normalized_chunks
        ) / len(normalized_chunks),
        2
    ) if normalized_chunks else 0

    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    source_filenames = []
    source_pages = []

    for chunk in normalized_chunks:
        if chunk["filename"] not in source_filenames:
            source_filenames.append(chunk["filename"])
        if str(chunk["page_number"]) not in source_pages:
            source_pages.append(str(chunk["page_number"]))

    chat_entry = ChatHistory(
        user_id=existing_user.id,
        question=request.question,
        answer=ai_response,
        confidence_score=str(average_confidence),
        source_filename=", ".join(source_filenames) if source_filenames else "Unknown",
        source_page_number=", ".join(source_pages) if source_pages else "N/A",
        sources_json=json.dumps(normalized_chunks)
    )

    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)

    return {
        "question": request.question,
        "answer": ai_response,
        "sources": normalized_chunks,
        "confidence_score": round(
            max(
                [
                    chunk["confidence"]
                    for chunk in normalized_chunks
                ]
            ) if normalized_chunks else 0,
            2
        ),
        "created_at": chat_entry.created_at.isoformat() if chat_entry.created_at else None
    }


# =========================================
# UPDATE PROFILE
# =========================================

@app.put("/update-profile")
def update_profile(

    user_data: dict,

    db: Session = Depends(get_db)
):

    email = user_data.get("email")

    username = user_data.get("username")

    password = user_data.get("password")

    # =====================================
    # FIND USER
    # =====================================

    existing_user = db.query(User).filter(

        User.email == email

    ).first()

    if not existing_user:

        raise HTTPException(

            status_code=404,

            detail="User not found"
        )

    # =====================================
    # USERNAME VALIDATION
    # =====================================

    if len(username.strip()) < 3:

        raise HTTPException(

            status_code=400,

            detail=
            "Username must contain at least 3 characters"
        )

    # =====================================
    # PASSWORD VALIDATION
    # =====================================

    if password:

        if len(password.strip()) < 6:

            raise HTTPException(

                status_code=400,

                detail=
                "Password must contain at least 6 characters"
            )

        if not any(char.isalpha() for char in password):

            raise HTTPException(

                status_code=400,

                detail=
                "Password must contain letters"
            )

        existing_user.password = hash_password(
            password
        )

    # =====================================
    # UPDATE USERNAME
    # =====================================

    existing_user.username = username

    db.commit()

    return {

        "message":
        "Profile updated successfully"
    }

# =========================================
# GET USER CHAT HISTORY
# =========================================

# =========================================
# GET USER CHAT HISTORY
# =========================================

@app.get("/history/{email}")
def get_history(

    email: str,

    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(

        User.email == email

    ).first()

    if not existing_user:

        return []

    history = db.query(ChatHistory).filter(

        ChatHistory.user_id == existing_user.id

    ).order_by(
        ChatHistory.id.desc()
    ).all()

    return [
        _serialize_chat_entry(chat)
        for chat in history
    ]


# =========================================
# GET SINGLE CHAT
# =========================================

@app.get("/chat/{chat_id}")
def get_chat(

    chat_id: int,

    db: Session = Depends(get_db)
):

    chat = db.query(ChatHistory).filter(

        ChatHistory.id == chat_id

    ).first()

    if not chat:

        raise HTTPException(

            status_code=404,

            detail="Chat not found"
        )

    return _serialize_chat_entry(chat)

# =========================================
# DELETE CHAT HISTORY
# =========================================

@app.delete("/delete-chat/{chat_id}")
def delete_chat(

    chat_id: int,

    db: Session = Depends(get_db)
):

    chat = db.query(ChatHistory).filter(

        ChatHistory.id == chat_id

    ).first()

    if not chat:

        raise HTTPException(

            status_code=404,

            detail="Chat not found"
        )

    db.delete(chat)

    db.commit()

    return {

        "message":
        "Chat deleted successfully"
    }

# =========================================
# GET UPLOADED FILES
# =========================================

@app.get("/uploaded-files/{email}")

def get_uploaded_files(

    email: str,

    db: Session = Depends(get_db)
):

    user = db.query(User).filter(

        User.email == email

    ).first()

    if not user:

        raise HTTPException(

            status_code=404,

            detail="User not found"
        )

    files = db.query(UploadedFile).filter(

        UploadedFile.owner_id == user.id

    ).all()

    return files

# =========================================
# DELETE FILE
# =========================================

@app.delete("/delete-file/{file_id}")
def delete_file(

    file_id: int,

    db: Session = Depends(get_db)
):

    file = db.query(UploadedFile).filter(

        UploadedFile.id == file_id

    ).first()

    if not file:

        raise HTTPException(

            status_code=404,

            detail="File not found"
        )

    db.delete(file)

    db.commit()

    return {

        "message":
        "File deleted successfully"
    }

# =========================================
# DELETE ALL FILES
# =========================================

@app.delete("/delete-all-files")
def delete_all_files(

    db: Session = Depends(get_db)
):

    db.query(UploadedFile).delete()

    db.commit()

    return {

        "message":
        "All files deleted successfully"
    }