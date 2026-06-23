from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from database.db import Base


# =========================================
# USER TABLE
# =========================================

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)

    email = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    uploaded_files = relationship("UploadedFile", back_populates="owner")

    chat_history = relationship("ChatHistory", back_populates="user")


# =========================================
# UPLOADED FILES TABLE
# =========================================

class UploadedFile(Base):

    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)

    filesize = Column(String)

    filename = Column(String, nullable=False)

    filepath = Column(String, nullable=False)

    filetype = Column(String, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="uploaded_files")


# =========================================
# CHAT HISTORY TABLE
# =========================================

class ChatHistory(Base):

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(Text, nullable=False)

    answer = Column(Text, nullable=False)

    confidence_score = Column(String)

    source_filename = Column(String, nullable=True)

    source_page_number = Column(String, nullable=True)

    sources_json = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=True
    )

    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="chat_history")

# =========================================
# SEARCH HISTORY
# =========================================

class SearchHistory(Base):

    __tablename__ = "search_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    email = Column(String)

    question = Column(String)