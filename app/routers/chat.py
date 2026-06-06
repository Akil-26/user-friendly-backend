from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, ArticleChunk, ChatSession
from ..schemas import EmbedRequest, EmbedResponse, AskRequest, AskResponse
from ..dependencies import get_current_user
from ..services.rag_service import (
    scrape_article, chunk_text,
    get_embedding, find_relevant_chunks, ask_ai
)

router = APIRouter(prefix="/chat", tags=["Chat AI"])


@router.post("/embed", response_model=EmbedResponse)
async def embed_article(
    data: EmbedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called when user taps YES on the popup.
    Scrapes article → chunks → embeds → stores in DB.
    """
    # check if already embedded for this user
    existing = db.query(ArticleChunk).filter(
        ArticleChunk.article_url == data.article_url,
        ArticleChunk.user_id == current_user.id
    ).first()

    if existing:
        # already done — just return session
        session = db.query(ChatSession).filter(
            ChatSession.article_url == data.article_url,
            ChatSession.user_id == current_user.id
        ).first()
        return EmbedResponse(
            session_id=session.id,
            article_title=data.article_title,
            chunks_stored=0,
            message="Already embedded, ready to chat!"
        )

    # 1. scrape
    try:
        title, full_text = scrape_article(data.article_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not full_text or len(full_text) < 100:
        raise HTTPException(status_code=400, detail="Could not extract enough text from this article.")

    # 2. chunk
    chunks = chunk_text(full_text)

    # 3. embed each chunk + store
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        db_chunk = ArticleChunk(
            article_url=data.article_url,
            user_id=current_user.id,
            chunk_index=i,
            chunk_text=chunk,
            embedding=embedding,
        )
        db.add(db_chunk)

    # 4. create chat session
    session = ChatSession(
        article_url=data.article_url,
        article_title=title,
        user_id=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return EmbedResponse(
        session_id=session.id,
        article_title=title,
        chunks_stored=len(chunks),
        message="Article ready! You can now ask questions."
    )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    data: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called when user sends a message in the chat page.
    Embeds question → finds relevant chunks → Claude answers.
    """
    # get all chunks for this article + user
    chunks = db.query(ArticleChunk).filter(
        ArticleChunk.article_url == data.article_url,
        ArticleChunk.user_id == current_user.id
    ).all()

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Article not embedded yet. Please tap 'Chat with AI' first."
        )

    # get session for title
    session = db.query(ChatSession).filter(
        ChatSession.article_url == data.article_url,
        ChatSession.user_id == current_user.id
    ).first()
    article_title = session.article_title if session else "News Article"

    # embed the question
    question_embedding = get_embedding(data.question)

    # find top 3 most relevant chunks
    relevant = find_relevant_chunks(question_embedding, chunks, top_k=3)
    context_texts = [c.chunk_text for c in relevant]

    # ask Claude
    answer = ask_ai(data.question, context_texts, article_title)

    return AskResponse(
        question=data.question,
        answer=answer,
        source_chunks=len(relevant)
    )


@router.get("/sessions")
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all articles the user has chatted with."""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()

    return {
        "sessions": [
            {
                "session_id": s.id,
                "article_title": s.article_title,
                "article_url": s.article_url,
                "created_at": s.created_at,
            }
            for s in sessions
        ]
    }