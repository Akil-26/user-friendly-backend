# Only trusted, real news channels — no blogs or spam
INTEREST_FEEDS = {
    "tech": [
        "https://feeds.feedburner.com/ndtvtech",           # NDTV Tech
        "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",  # The Hindu Tech
        "https://feeds.bbci.co.uk/news/technology/rss.xml",  # BBC Technology
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",  # NYT Tech
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",          # BBC Sport
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",  # ESPNCricinfo
        "https://timesofindia.indiatimes.com/rss/4719148.cms",  # TOI Sports
        "https://www.thehindu.com/sport/feeder/default.rss",   # The Hindu Sports
    ],
    "finance": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # ET Markets
        "https://www.moneycontrol.com/rss/latestnews.xml",    # Moneycontrol
        "https://feeds.bbci.co.uk/news/business/rss.xml",     # BBC Business
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",  # NYT Business
    ],
    "science": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",  # BBC Science
        "https://www.thehindu.com/sci-tech/science/feeder/default.rss",   # The Hindu Science
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",       # NYT Science
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",                  # NASA
    ],
    "health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",       # BBC Health
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",  # NYT Health
        "https://www.thehindu.com/sci-tech/health/feeder/default.rss",  # The Hindu Health
    ],
    "politics": [
        "https://feeds.bbci.co.uk/news/politics/rss.xml",     # BBC Politics
        "https://www.thehindu.com/news/national/feeder/default.rss",  # The Hindu India
        "https://timesofindia.indiatimes.com/rss/4719148.cms",  # TOI India
        "https://indianexpress.com/feed/",                     # Indian Express
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",        # BBC World
        "https://feeds.reuters.com/reuters/worldNews",         # Reuters World
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
        "https://www.thehindu.com/news/international/feeder/default.rss",  # The Hindu World
    ],
    "business": [
        "https://economictimes.indiatimes.com/rss/3442a468.cms",  # ET Business
        "https://feeds.reuters.com/reuters/businessNews",          # Reuters Business
        "https://feeds.bbci.co.uk/news/business/rss.xml",         # BBC Business
    ],
    "entertainment": [
        "https://timesofindia.indiatimes.com/rss/4719148.cms",    # TOI Entertainment
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",  # BBC Entertainment
        "https://indianexpress.com/section/entertainment/feed/",   # Indian Express Entertainment
    ],
    "gaming": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",   # BBC Tech (covers gaming)
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ],
    "india": [
        "https://www.thehindu.com/news/national/feeder/default.rss",  # The Hindu
        "https://indianexpress.com/feed/",                             # Indian Express
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", # TOI Top Stories
        "https://www.ndtv.com/rss/2012",                              # NDTV India
    ],
}

# All built-in topic keys — used for Feed/Explore page
BUILTIN_TOPICS = list(INTEREST_FEEDS.keys())

DEFAULT_INTERESTS = ["world", "india"]

# Trusted source display names
SOURCE_NAMES = {
    "ndtv": "NDTV",
    "thehindu": "The Hindu",
    "bbc": "BBC News",
    "nytimes": "New York Times",
    "reuters": "Reuters",
    "espncricinfo": "ESPNCricinfo",
    "timesofindia": "Times of India",
    "economictimes": "Economic Times",
    "moneycontrol": "Moneycontrol",
    "nasa": "NASA",
    "indianexpress": "Indian Express",
}


def get_feed_url_for_topic(topic: str) -> list:
    """
    Returns RSS URLs for any topic.
    Known topics → trusted multi-source RSS.
    Custom topics → Google News RSS search.
    """
    normalized = topic.strip().lower()
    if normalized in INTEREST_FEEDS:
        return INTEREST_FEEDS[normalized]
    # custom tag → Google News search RSS
    encoded = normalized.replace(" ", "+")
    return [
        f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    ]