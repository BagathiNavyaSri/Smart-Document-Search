from pydantic import BaseModel


# =========================================
# USER CREATE SCHEMA
# =========================================

class UserCreate(BaseModel):

    username: str

    email: str

    password: str


# =========================================
# USER LOGIN SCHEMA
# =========================================

class UserLogin(BaseModel):

    email: str

    password: str


# =========================================
# CHAT REQUEST SCHEMA
# =========================================

class ChatRequest(BaseModel):

    question: str

    email: str