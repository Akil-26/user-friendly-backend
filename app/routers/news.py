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
from ..news_sources import INTEREST_FEEDS, DEFAULT_INTERESTS, SOURCE_NAMES, get_feed_url_for_topic

router = APIRouter(prefix="/news", tags=["News"])


# ── helpers ──────────────────────────────────────────────

def parse_date(entry) -> datetime:
    """Parse publish date from RSS entry — handles multiple date formats."""
    try:
        if hasattr(entry, "published"):
            return parsedate_to_datetime(entry.published)
        if hasattr(entry, "updated"):
            return parsedate_to_datetime(entry.updated)
    except Exception:
        pass
    return datetime.min  # if no date, push to bottom


def get_source_name(link: str) -> str:
    """Extract clean source name from article URL."""
    for key, name in SOURCE_NAMES.items():
        if key in link:
            return name
    return "News"


def clean_summary(summary: str) -> str:
    """Remove HTML tags from summary text."""
    import re
    clean = re.sub(r"<[^>]+>", "", summary)  # remove HTML tags
    return clean.strip()[:300]               # limit to 300 chars


async def fetch_feed(
    client: httpx.AsyncClient,
    interest: str,
    url: str,
    limit: int
) -> List[dict]:
    """Fetch and parse a single RSS feed from a trusted source."""
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
                "_sort_date": pub_date,  # used for sorting, removed before response
            })

        return articles

    except Exception:
        return []


async def fetch_all_feeds(interests: List[str], limit_per_feed: int) -> List[dict]:
    """
    Fetch ALL trusted sources for ALL user interests simultaneously.
    Uses asyncio.gather — all requests fire at the same time.
    """
    tasks = []

    for interest in interests:
        urls = INTEREST_FEEDS.get(interest, [])
        for url in urls:
            tasks.append((interest, url))

    if not tasks:
        # fallback to default interests
        for interest in DEFAULT_INTERESTS:
            for url in INTEREST_FEEDS.get(interest, []):
                tasks.append((interest, url))

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},  # some RSS feeds need this
        follow_redirects=True
    ) as client:
        fetch_tasks = [
            fetch_feed(client, interest, url, limit_per_feed)
            for interest, url in tasks
        ]
        results = await asyncio.gather(*fetch_tasks)

    # flatten all articles into one list
    all_articles = [article for feed in results for article in feed]

    # ── Sort by newest first ──
    all_articles.sort(key=lambda x: x["_sort_date"], reverse=True)

    # remove internal sort key before sending response
    for article in all_articles:
        del article["_sort_date"]

    # remove articles with empty titles or links
    all_articles = [a for a in all_articles if a["title"] and a["link"]]

    return all_articles


# ── routes ───────────────────────────────────────────────

@router.get("/feed")
async def get_feed(
    limit: int = Query(default=10, ge=1, le=30, description="Articles per source"),
    current_user: User = Depends(get_current_user),
):
    """
    Returns personalized news feed based on user interests.
    - Fetches from trusted sources only (BBC, Reuters, Hindu, TOI, etc.)
    - Sorted by newest article first
    - Covers all historical articles available in the RSS feed
    """
    interests = current_user.interests
    if not interests:
        interests = DEFAULT_INTERESTS

    articles = await fetch_all_feeds(interests, limit_per_feed=limit)

    if not articles:
        raise HTTPException(status_code=503, detail="Could not fetch news right now, try again")

    return {
        "user": current_user.name,
        "interests": interests,
        "total": len(articles),
        "articles": articles,
    }


@router.get("/topics")
def get_available_topics():
    """Returns all available interest topics — no auth needed."""
    return {
        "total": len(INTEREST_FEEDS),
        "topics": list(INTEREST_FEEDS.keys()),
    }


@router.get("/feed")
async def get_feed(
    limit: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    interests = current_user.interests or DEFAULT_INTERESTS

    # fetch ALL user interests simultaneously — known + custom tags
    all_articles = []
    
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True
    ) as client:
        tasks = []
        for interest in interests:
            urls = get_feed_url_for_topic(interest)  # works for any tag
            for url in urls:
                tasks.append(fetch_feed(client, interest, url, limit))
        
        results = await asyncio.gather(*tasks)

    all_articles = [a for feed in results for a in feed]
    all_articles.sort(key=lambda x: x["_sort_date"], reverse=True)
    for a in all_articles:
        del a["_sort_date"]
    all_articles = [a for a in all_articles if a["title"] and a["link"]]

    return {
        "user": current_user.name,
        "interests": interests,
        "total": len(all_articles),
        "articles": all_articles,
    }