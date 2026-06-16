from pydantic import BaseModel, EmailStr
from typing import List

# --- Auth ---
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    interests: List[str] = []

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- User ---
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    interests: List[str]

    class Config:
        from_attributes = True  # lets pydantic read SQLAlchemy models

class InterestsUpdate(BaseModel):
    interests: List[str]

# --- Chat / RAG ---
class EmbedRequest(BaseModel):
    article_url: str
    article_title: str

class EmbedResponse(BaseModel):
    session_id: int
    article_title: str
    chunks_stored: int
    message: str
    can_embed: bool = True

class AskRequest(BaseModel):
    article_url: str
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str
    source_chunks: int