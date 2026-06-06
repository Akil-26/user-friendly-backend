from sqlalchemy import Column, Float, Integer, String, DateTime, ARRAY, Boolean, Text
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    email       = Column(String, unique=True, index=True, nullable=False)
    password    = Column(String, nullable=False)          # hashed, never plain
    interests   = Column(ARRAY(String), default=[])       # ["tech", "sports"]
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=func.now())

class ArticleChunk(Base):
    __tablename__ = "article_chunks"

    id         = Column(Integer, primary_key=True, index=True)
    article_url = Column(String, nullable=False)
    user_id    = Column(Integer, nullable=False)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)
    embedding  = Column(ARRAY(Float))
    created_at = Column(DateTime, default=func.now())

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id            = Column(Integer, primary_key=True, index=True)
    article_url   = Column(String, nullable=False)
    article_title = Column(String)
    user_id       = Column(Integer, nullable=False)
    created_at    = Column(DateTime, default=func.now())