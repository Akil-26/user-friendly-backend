from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import httpx
import feedparser
import asyncio
from typing import List, Optional
from datetime import datetime
from email.utils import parsedate_to_datetime

from ..database import get_db
from ..models import User
from ..dependencies import get_current_user
from ..news_sources import (
    INTEREST_FEEDS, BUILTIN_TOPICS,
    DEFAULT_INTERESTS, SOURCE_NAMES,
    get_feed_url_for_topic
)

router = APIRouter(prefix="/news", tags=["News"])


# ── helpers ──────────────────────────────────────────────

def parse_date(entry) -> datetime:
    try:
        if hasattr(entry, "published"):
            return parsedate_to_datetime(entry.published)
        if hasattr(entry, "updated"):
            return parsedate_to_datetime(entry.updated)
    except Exception:
        pass
    return datetime.min


def get_source_name(link: str) -> str:
    for key, name in SOURCE_NAMES.items():
        if key in link:
            return name
    return "News"


def clean_summary(summary: str) -> str:
    import re
    clean = re.sub(r"<[^>]+>", "", summary)
    return clean.strip()[:300]


async def fetch_feed(
    client: httpx.AsyncClient,
    interest: str,
    url: str,
    limit: int
) -> List[dict]:
    try:
        response = await client.get(url, timeout=10.0)
        if response.status_code != 200:
            return []
        feed = feedparser.parse(response.text)
        articles = []
        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            pub_date = parse_date(entry)
            articles.append({
                "title": entry.get("title", "").strip(),
                "link": link,
                "source": get_source_name(link),
                "summary": clean_summary(entry.get("summary", "")),
                "interest": interest,
                "published_raw": pub_date.isoformat() if pub_date != datetime.min else None,
                "published_display": pub_date.strftime("%d %b %Y, %I:%M %p") if pub_date != datetime.min else "Date unavailable",
                "_sort_date": pub_date,
            })
        return articles
    except Exception:
        return []


async def fetch_topics(topics: List[str], limit: int) -> List[dict]:
    """Fetch all topics simultaneously and return sorted articles."""
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True
    ) as client:
        tasks = []
        for topic in topics:
            urls = get_feed_url_for_topic(topic)
            for url in urls:
                tasks.append(fetch_feed(client, topic, url, limit))
        results = await asyncio.gather(*tasks)

    all_articles = [a for feed in results for a in feed]
    # sort newest first
    all_articles.sort(key=lambda x: x["_sort_date"], reverse=True)
    for a in all_articles:
        del a["_sort_date"]
    all_articles = [a for a in all_articles if a["title"] and a["link"]]
    return all_articles


# ── routes ───────────────────────────────────────────────

@router.get("/feed")
async def get_home_feed(
    limit: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """
    HOME PAGE feed.
    Returns news ONLY for user's selected interests.
    Both built-in and custom interests supported.
    Sorted newest first.
    """
    interests = current_user.interests
    if not interests:
        interests = DEFAULT_INTERESTS

    # normalize
    interests = [i.strip().lower() for i in interests]

    articles = await fetch_topics(interests, limit)

    if not articles:
        raise HTTPException(
            status_code=503,
            detail="Could not fetch news right now"
        )

    return {
        "user": current_user.name,
        "interests": interests,
        "total": len(articles),
        "articles": articles,
    }


@router.get("/explore")
async def get_explore_feed(
    limit: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """
    FEED/EXPLORE PAGE.
    Returns news for ALL built-in topics + user's custom interests.
    Sorted newest first.
    """
    # all built-in topics
    all_topics = list(BUILTIN_TOPICS)

    # add user custom interests not already in built-in
    user_interests = [i.strip().lower() for i in (current_user.interests or [])]
    for interest in user_interests:
        if interest not in all_topics:
            all_topics.append(interest)

    articles = await fetch_topics(all_topics, limit)

    return {
        "total": len(articles),
        "topics": all_topics,
        "articles": articles,
    }


@router.get("/feed/{interest}")
async def get_feed_by_interest(
    interest: str,
    limit: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """
    Single topic feed — used when user taps a chip.
    Works for both built-in and custom topics.
    """
    from thefuzz import process

    normalized = interest.strip().lower()
    available = list(INTEREST_FEEDS.keys())

    # exact match
    if normalized in available:
        matched = normalized
    else:
        # fuzzy match for known topics
        best = process.extractOne(normalized, available, score_cutoff=60)
        matched = best[0] if best else normalized
        # if no fuzzy match, use as-is (custom topic → Google News)

    articles = await fetch_topics([matched], limit)

    return {
        "searched": interest,
        "matched_topic": matched,
        "total": len(articles),
        "articles": articles,
    }


@router.get("/topics")
def get_available_topics(
    current_user: User = Depends(get_current_user),
):
    """
    Returns built-in topics + user's custom interests.
    Used by Feed/Explore page to build tab list.
    """
    user_custom = [
        i.strip().lower() for i in (current_user.interests or [])
        if i.strip().lower() not in BUILTIN_TOPICS
    ]
    return {
        "builtin": BUILTIN_TOPICS,
        "custom": user_custom,
        "all":  user_custom + BUILTIN_TOPICS ,
    }