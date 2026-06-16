import os
import httpx
import numpy as np
import hashlib
from bs4 import BeautifulSoup
from typing import List
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()


# ── AI Client factory ─────────────────────────────────────

def get_ai_response(system_prompt: str, user_message: str) -> str:
    """
    Single function to call any AI provider.
    Just change AI_PROVIDER in .env to switch.
    """
    if AI_PROVIDER == "ollama":
        return _call_ollama(system_prompt, user_message)
    elif AI_PROVIDER == "groq":
        return _call_groq(system_prompt, user_message)
    elif AI_PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_message)
    elif AI_PROVIDER == "openai":
        return _call_openai(system_prompt, user_message)
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {AI_PROVIDER}. Choose: ollama, groq, gemini, openai")


def _call_ollama(system_prompt: str, user_message: str) -> str:
    """Free — runs fully on your machine. No internet needed."""
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=60.0,
    )
    return response.json()["message"]["content"]


def _call_groq(system_prompt: str, user_message: str) -> str:
    """Free tier — very fast, great for production."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # free model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content


def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Free tier available — Google's model."""
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",  # free tier model
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_message)
    return response.text


def _call_openai(system_prompt: str, user_message: str) -> str:
    """Paid — most powerful option."""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # cheapest good model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content


# ── Article scraping ──────────────────────────────────────

def scrape_article(url: str) -> tuple[str, str]:
    """Fetch and extract clean text. Raises exception if paywall detected."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        
        # paywall detection — login redirect or very short content
        if response.status_code in [401, 403, 429]:
            raise Exception("paywall_detected")
        
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else "News Article"

        # detect login walls — common patterns
        page_text = soup.get_text().lower()
        paywall_signals = [
            "subscribe to read",
            "sign in to read",
            "login to continue",
            "subscribe now to",
            "create a free account",
            "you've used all your free articles",
            "please log in",
        ]
        if any(signal in page_text for signal in paywall_signals):
            raise Exception("paywall_detected")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)

        return title.strip(), text.strip()

    except Exception as e:
        raise Exception(f"scrape_failed: {str(e)}")


def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into overlapping ~500 word chunks."""
    words = text.split()
    chunks = []
    overlap = 50

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


# ── Embeddings (free, local, no API needed) ───────────────

def get_embedding(text: str) -> List[float]:
    """
    Hash-based embedding — free, no API cost, works offline.
    Each word maps to a position in a 512-dimension vector.
    """
    words = text.lower().split()
    vector = [0.0] * 512

    for word in words:
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % 512
        vector[idx] += 1.0

    # normalize to unit vector
    magnitude = sum(x**2 for x in vector) ** 0.5
    if magnitude > 0:
        vector = [x / magnitude for x in vector]

    return vector


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """1.0 = identical meaning, 0.0 = completely unrelated."""
    a = np.array(vec1)
    b = np.array(vec2)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def find_relevant_chunks(
    question_embedding: List[float],
    all_chunks: list,
    top_k: int = 3
) -> list:
    """Find top_k most relevant chunks by cosine similarity."""
    scored = [(cosine_similarity(question_embedding, c.embedding), c) for c in all_chunks]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


# ── Main answer function ──────────────────────────────────

def ask_ai(question: str, context_chunks: List[str], article_title: str) -> str:
    """Build prompt with context and get answer from chosen AI provider."""
    context = "\n\n".join(context_chunks)

    system_prompt = f"""You are a helpful news assistant.
The user is reading a news article titled: "{article_title}".
Answer ONLY based on the article context provided.
If the answer is not in the context, say "I couldn't find that in this article."
Be concise and clear."""

    user_message = f"""Article context:
{context}

Question: {question}"""

    return get_ai_response(system_prompt, user_message)