"""
FastAPI Microservice for Indian Stock Market News Aggregation

Security Features:
- HTML sanitization to prevent XSS attacks
- User-Agent spoofing to prevent IP bans
- CORS configured (can be locked down to specific domains)
- Per-feed error handling for resilience

Performance Optimizations:
- Async I/O with parallel feed fetching
- Memory-efficient deque with O(1) operations
- O(1) duplicate detection using hash set
"""

import asyncio
import hashlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional
from dateutil import parser as date_parser

import feedparser
import requests
import re
from app.core.scheduler_v2 import scheduler_instance
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

# Indian Standard Time offset
IST = timezone(timedelta(hours=5, minutes=30))

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# API Key for authentication
API_KEY = "NEWSFORTFU2026"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Depends(api_key_header)):

    if api_key is None or api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="WAIT A MINUTEEEE... WHO AREE YOU??"
        )
    return api_key


# ============================================================================
# CONFIGURATION
# ============================================================================

RSS_FEEDS = {
# Stock Market & Trading focused feeds
    "Business Today Markets": "https://www.businesstoday.in/rssfeeds?id=markets",
    "Hindu BusinessLine Markets": "https://www.thehindubusinessline.com/markets/feeder/default.rss",
    "Hindu BusinessLine Stock Markets": "https://www.thehindubusinessline.com/markets/stock-markets/feeder/default.rss",
    "Live Mint Markets": "https://www.livemint.com/rss/markets",
    "Live Mint Money": "https://www.livemint.com/rss/money",
    
    # Finance & Investment focused feeds
    "Rediff Money": "https://www.rediff.com/rss/moneyrss.xml",
    "Business Standard Finance": "https://www.business-standard.com/rss/finance-103.rss",
    "Business Standard Markets": "https://www.business-standard.com/rss/markets-106.rss",
    
    # IPO & Investment opportunities
    "GoodReturns IPO": "https://www.goodreturns.in/rss/feeds/ipo-fb.xml",
    "GoodReturns Money": "https://www.goodreturns.in/rss/feeds/money-news-fb.xml",

    # Moneycontrol Feeds (Using Google News RSS Workaround since official feeds are stale since April 2024)
    "Moneycontrol Latest News": "https://news.google.com/rss/search?q=site:moneycontrol.com+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Top News": "https://news.google.com/rss/search?q=site:moneycontrol.com+top+news+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Buzzing Stocks": "https://news.google.com/rss/search?q=site:moneycontrol.com+buzzing+stocks+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Market Reports": "https://news.google.com/rss/search?q=site:moneycontrol.com+market+reports+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Business": "https://news.google.com/rss/search?q=site:moneycontrol.com+business+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Technology": "https://news.google.com/rss/search?q=site:moneycontrol.com+technology+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Mutual Funds": "https://news.google.com/rss/search?q=site:moneycontrol.com+mutual+funds+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Special Picks": "https://news.google.com/rss/search?q=site:moneycontrol.com+special+picks+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "Moneycontrol Commodities": "https://news.google.com/rss/search?q=site:moneycontrol.com+commodities+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    
    # NDTV Profit & Business
    "NDTV Profit": "https://feeds.feedburner.com/ndtvprofit-latest",
    
    # Economic Times
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Economic Times Industry": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
    "Economic Times Mutual Funds": "https://economictimes.indiatimes.com/mf/rssfeeds/8972232.cms",
    "Economic Times Wealth": "https://economictimes.indiatimes.com/wealth/rssfeeds/8371186.cms",
    
    # Financial Express
    "Financial Express Markets": "https://www.financialexpress.com/market/feed/",
    "Financial Express Industry": "https://www.financialexpress.com/industry/feed/",
    "Financial Express Economy": "https://www.financialexpress.com/economy/feed/",
    
    # CNBC TV18
    "CNBC Market News": "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/market.xml",
    "CNBC Business News": "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/business.xml",
    "CNBC Personal Finance": "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/personal-finance.xml",
    
    # Business Line (Additional)
    "Hindu BusinessLine Companies": "https://www.thehindubusinessline.com/companies/feeder/default.rss",
    "Hindu BusinessLine Economy": "https://www.thehindubusinessline.com/economy/feeder/default.rss",

}



MAX_NEWS_ITEMS = 200  # Increased for deeper history
UPDATE_INTERVAL_SECONDS = 60

# Connection pooling for better performance
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# DATA STORAGE (Memory-Efficient with Source Tracking)
# ============================================================================

# Using deque with maxlen for automatic O(1) removal of oldest items
news_storage: deque = deque(maxlen=MAX_NEWS_ITEMS)

# Set of URL hashes for O(1) duplicate detection
seen_urls: Set[str] = set()

# Using global scheduler_instance for background jobs

async def update_news_cache():
    """
    Background worker that fetches ALL RSS feeds in parallel and populates memory.
    Ensures zero-latency for user requests.
    """
    all_items = []
    print(f"[{datetime.now(IST)}] Neural Hub: Refreshing news cache...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(fetch_single_feed, name, url) 
            for name, url in RSS_FEEDS.items()
        ]
        for future in futures:
            try:
                all_items.extend(future.result())
            except Exception as e:
                print(f"Background Fetch Exception: {e}")

    # Deduplicate and update global storage
    count = 0
    for item in all_items:
        url_hash = hash_url(item["link"])
        if url_hash not in seen_urls:
            seen_urls.add(url_hash)
            news_storage.appendleft(item)
            count += 1
            
    # Sort storage by date
    temp_list = list(news_storage)
    temp_list.sort(key=lambda x: x.get("published_datetime", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    news_storage.clear()
    news_storage.extend(temp_list)
    
    print(f"✓ Neural Hub: Cache updated. {count} new articles added. Total: {len(news_storage)}")

# ============================================================================
# PRODUCTION FIX: Per-source article tracking
# Preserves articles when individual RSS feeds fail
source_articles: Dict[str, List[Dict[str, Any]]] = {
    source: [] for source in RSS_FEEDS.keys()
}

# PRODUCTION FIX: Source health monitoring
# Tracks success/failure rate of each RSS source
source_status: Dict[str, Dict[str, Any]] = {
    source: {
        "last_success": None,
        "last_attempt": None,
        "consecutive_failures": 0,
        "total_fetches": 0,
        "successful_fetches": 0
    } for source in RSS_FEEDS.keys()
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_html(html_content: str) -> str:
    """
    Strip all HTML tags to prevent XSS attacks.
    
    Args:
        html_content: Raw HTML string from RSS feed
        
    Returns:
        Plain text with all HTML removed
    """
    if not html_content:
        return ""
    
    try:
        # Parse and strip all HTML tags
        soup = BeautifulSoup(html_content, "html.parser")
    
        # Remove script, style, and iframe tags completely
        for tag in soup(["script", "style", "iframe", "object", "embed"]):
            tag.decompose()
        
        # Get plain text
        clean_text = soup.get_text(separator=" ", strip=True)
        # Return full summary - user wants complete content
        return clean_text
    except Exception as e:
        # If HTML parsing fails, return empty string (safer than raw content)
        print(f"Warning: HTML sanitization failed: {e}")
        return ""


def hash_url(url: str) -> str:
    """Generate SHA256 hash of URL for duplicate detection."""
    return hashlib.sha256(url.encode()).hexdigest()


def convert_to_ist(dt: datetime) -> str:
    """
    Convert datetime to IST and format as readable string in 12-hour format.
    
    Args:
        dt: datetime object (timezone-aware)
        
    Returns:
        Formatted datetime string in IST (YYYY-MM-DD HH:MM:SS AM/PM IST)
    """
    # Convert to IST
    ist_dt = dt.astimezone(IST)
    # Format: 2026-02-15 06:30:45 PM IST (12-hour format)
    return ist_dt.strftime("%Y-%m-%d %I:%M:%S %p IST")


def parse_date_from_entry(entry) -> datetime:
    """
    Parse date from RSS entry with multiple fallbacks.
    
    Tries in order:
    1. published_parsed
    2. updated_parsed  
    3. published string with dateutil
    4. updated string with dateutil
    5. Current time (fallback)
    
    Args:
        entry: feedparser entry object
        
    Returns:
        datetime object (timezone-aware)
    """
    # Try published_parsed first
    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed:
        try:
            dt = datetime(*published_parsed[:6])
            # Make timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError, IndexError) as e:
            print(f"Warning: published_parsed parsing failed: {e}")
            pass
    
    # Try updated_parsed as fallback
    updated_parsed = getattr(entry, "updated_parsed", None)
    if updated_parsed:
        try:
            dt = datetime(*updated_parsed[:6])
            # Make timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError, IndexError) as e:
            print(f"Warning: updated_parsed parsing failed: {e}")
            pass
    
    # Try parsing published/updated strings with dateutil
    for field in ['published', 'updated']:
        date_str = getattr(entry, field, None)
        if date_str:
            try:
                dt = date_parser.parse(date_str)
                # Make timezone aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError, OverflowError) as e:
                print(f"Warning: dateutil parsing failed for {field}: {e}")
                continue
    
    # Final fallback: current time
    return datetime.now(IST)


def fetch_single_feed(source_name: str, feed_url: str) -> List[Dict[str, Any]]:
    """
    Fetch and parse a single RSS feed with error handling.
    
    This function runs in a thread pool to avoid blocking the async event loop.
    
    Args:
        source_name: Human-readable name of the news source
        feed_url: URL of the RSS feed
        
    Returns:
        List of normalized news items
    """
    news_items = []
    
    try:
        # Use session for connection pooling (performance optimization)
        response = SESSION.get(feed_url, timeout=10)
        response.raise_for_status()
        
        # Parse RSS feed
        feed = feedparser.parse(response.content)
        
        for entry in feed.entries:
            # Extract and sanitize data
            title = sanitize_html(getattr(entry, "title", ""))
            
            # Get summary/description (different feeds use different field names)
            summary = sanitize_html(
                getattr(entry, "summary", "") or 
                getattr(entry, "description", "")
            )
            
            link = getattr(entry, "link", "")
            
            # Parse published date with robust fallback
            published_dt = parse_date_from_entry(entry)
            timestamp = published_dt.isoformat()
            date = published_dt.strftime("%Y-%m-%d")
        items = []
        for entry in feed.entries[:15]:  # Process top 15 from each feed
            pub_dt = parse_date_from_entry(entry)
            
            items.append({
                "source": source_name,
                "title": entry.get("title", "No Title"),
                "summary": sanitize_html(entry.get("summary", entry.get("description", ""))),
                "link": entry.get("link", ""),
                "date": convert_to_ist(pub_dt),
                "published_datetime": pub_dt
            })
            
        print(f"✓ Fetched {len(items)} items from {source_name}")
        return items
        
    except requests.exceptions.Timeout:
        print(f"✗ Timeout fetching {source_name}")
        return []
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection error fetching {source_name}")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP error fetching {source_name}: {e.response.status_code}")
    except Exception as e:
        print(f"✗ Unexpected error fetching {source_name}: {type(e).__name__}: {str(e)}")
    
    return news_items


async def fetch_all_feeds() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch all RSS feeds in parallel using ThreadPoolExecutor.
    
    PRODUCTION FIX: Returns source-mapped results instead of flat list.
    Individual source failures don't crash entire update.
    
    Returns:
        Dict mapping source_name to list of articles (empty list if source failed)
    """
    loop = asyncio.get_event_loop()
    results_by_source = {}
    
    # Create tasks for parallel execution
    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = {
            source: loop.run_in_executor(executor, fetch_single_feed, source, url)
            for source, url in RSS_FEEDS.items()
        }
        
        # Wait for all feeds to complete
        for source, task in tasks.items():
            try:
                feed_items = await task
                results_by_source[source] = feed_items
                # Update source status on success
                source_status[source]["last_success"] = datetime.now(IST)
                source_status[source]["last_attempt"] = datetime.now(IST)
                source_status[source]["total_fetches"] += 1
                source_status[source]["successful_fetches"] += 1
                source_status[source]["consecutive_failures"] = 0
            except Exception as e:
                # CRITICAL: Don't crash on single source failure
                print(f"✗ Fatal error for {source}: {type(e).__name__}: {str(e)}")
                results_by_source[source] = []  # Empty = preserve old articles
                # Update source status on failure
                source_status[source]["last_attempt"] = datetime.now(IST)
                source_status[source]["total_fetches"] += 1
                source_status[source]["consecutive_failures"] += 1
    
    return results_by_source


def update_news_storage(new_items_by_source: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Update the in-memory news storage with source-aware resilience.
    
    PRODUCTION FIX: Preserves articles from failed sources instead of discarding them.
    Only updates sources that successfully fetched new data.
    
    Algorithm:
    1. Update source_articles for successful sources
    2. Keep existing articles for failed sources (empty list)
    3. Merge all sources into single pool
    4. Deduplicate across sources
    5. Sort by datetime (newest first)
    6. Keep top MAX_NEWS_ITEMS
    7. Atomic replacement of news_storage
    
    Args:
        new_items_by_source: Dict mapping source_name to list of articles
                            Empty list indicates source failure (preserve old)
    """
    updated_sources = []
    preserved_sources = []
    
    # Step 1: Update successful sources, preserve failed ones
    for source, new_articles in new_items_by_source.items():
        if new_articles:
            # Source succeeded - update its articles
            source_articles[source] = new_articles
            updated_sources.append(source)
        else:
            # Source failed - keep existing articles
            preserved_sources.append(source)
    
    # Step 2: Merge all source articles into single pool
    all_articles = []
    for source, articles in source_articles.items():
        all_articles.extend(articles)
    
    # Step 3: Deduplicate across sources using URL hashing
    seen_in_merge = set()
    deduplicated = []
    
    for item in all_articles:
        url_hash = hash_url(item["link"])
        if url_hash not in seen_in_merge:
            seen_in_merge.add(url_hash)
            deduplicated.append(item)
    
    # Step 4: Sort by published datetime (newest first)
    sorted_items = sorted(
        deduplicated,
        key=lambda x: x.get('published_datetime', datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )
    
    # Step 5: Keep only top MAX_NEWS_ITEMS
    sorted_items = sorted_items[:MAX_NEWS_ITEMS]
    
    # Step 6: Atomic replacement (prevents race conditions)
    new_storage = deque(maxlen=MAX_NEWS_ITEMS)
    new_seen_urls = set()
    
    for item in sorted_items:
        new_storage.append(item)
        new_seen_urls.add(hash_url(item["link"]))
    
    # Atomic swap
    news_storage.clear()
    news_storage.extend(new_storage)
    seen_urls.clear()
    seen_urls.update(new_seen_urls)
    
    # Step 7: Logging
    print(f"✓ Updated {len(updated_sources)} sources, preserved {len(preserved_sources)} failed sources")
    print(f"✓ Total: {len(news_storage)} articles from {len([s for s, items in source_articles.items() if items])} active sources")
    if preserved_sources:
        print(f"⚠ Preserved sources (feeds failed): {', '.join(preserved_sources)}")


async def scheduled_update():
    """Background task to update news feeds periodically."""
    print(f"[{datetime.now(IST)}] Starting scheduled news update...")
    
    try:
        # Returns Dict[source_name, List[articles]]
        new_items_by_source = await fetch_all_feeds()
        update_news_storage(new_items_by_source)
        print(f"[{datetime.now(IST)}] Update complete. Total items: {len(news_storage)}")
    except asyncio.CancelledError:
        print(f"[{datetime.now(IST)}] Scheduled update cancelled")
        raise
    except Exception as e:
        print(f"[{datetime.now(IST)}] Error during scheduled update: {type(e).__name__}: {str(e)}")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Indian Stock Market News API",
    description="High-performance news aggregation microservice with rate limiting",
    version="2.0.0"
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
# Currently allows all origins (*) since it's a public news feed
# TO LOCK DOWN: Replace ["*"] with specific domains like ["https://yourapp.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔒 Change to specific domains in production
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/news", response_model=List[Dict[str, Any]])
@limiter.limit("60/minute")  # Max 60 requests per minute per IP
async def get_news(
    request: Request,
    limit: int = Query(50, ge=1, le=300, description="Number of articles to return (1-300)"),
    query: str = Query(None, description="Search term to filter articles (title/summary/source)"),
    api_key: str = Depends(get_api_key),  # Security applied
    # Field selection parameters
    title: bool = Query(True, description="Include article title"),
    description: bool = Query(True, description="Include article description/summary"),
    source_name: bool = Query(True, description="Include source name"),
    source_link: bool = Query(True, description="Include source RSS feed link"),
    article_link: bool = Query(True, description="Include link to original article"),
    published_datetime: bool = Query(True, description="Include published date and time in IST"),
):
    """
    Get news items from the in-memory storage with configurable fields.
    
    Security: Requires X-API-Key header with valid API key
    Rate limit: 60 requests/minute
    
    Query Parameters:
        - limit: Number of articles to return (default: 50, min: 1, max: 300)
        - title: Include article title (default: True)
        - description: Include article summary (default: True)
        - source_name: Include news source name (default: True)
        - source_link: Include RSS feed URL (default: True)
        - article_link: Include original article URL (default: True)
        - published_datetime: Include publication datetime in IST (default: True)
    
    Returns:
        List of news objects with selected fields (limited to 'limit' items)
    
    Example:
        /news?limit=25 - Returns 25 latest articles with all fields
        /news?limit=100&source_name=false&source_link=false - 100 articles without source info
    """
    # Reverse lookup for source links
    source_to_link = {name: url for name, url in RSS_FEEDS.items()}
    
    # Filter items first
    filtered_items = list(news_storage)
    
    if query:
        query_lower = query.lower()
        filtered_items = [
            item for item in filtered_items 
            if query_lower in item["title"].lower() or 
               query_lower in item["summary"].lower() or 
               query_lower in item["source"].lower()
        ]

    # Build response with only requested fields, limited to 'limit' items
    response_items = []
    
    for item in filtered_items[:limit]:  # Apply limit after filtering
        article = {}
        
        if title:
            article["title"] = item["title"]
        
        if description:
            article["description"] = item["summary"]
        
        if source_name:
            article["source_name"] = item["source"]
        
        if source_link:
            article["source_link"] = source_to_link.get(item["source"], "")
        
        if article_link:
            article["article_link"] = item["link"]
        
        if published_datetime:
            # Convert to IST and format
            article["published_datetime"] = convert_to_ist(item["published_datetime"])
        
        response_items.append(article)
    
    return response_items


@app.get("/stats", response_model=Dict[str, int])
@limiter.limit("30/minute")  # Max 30 requests per minute per IP  
async def get_stats(
    request: Request,
    api_key: str = Depends(get_api_key)  # Security dependency
):
    """
    Get statistics about news sources.
    
    Security: Requires X-API-Key header with valid API key
    Rate limit: 30 requests/minute
    
    Returns:
        Dictionary mapping source names to article counts
    """
    # Initialize all sources with 0 to show even empty ones
    stats = {source: 0 for source in RSS_FEEDS.keys()}
    
    for item in news_storage:
        source = item.get("source", "Unknown")
        if source in stats:
            stats[source] += 1
        else:
            stats[source] = stats.get(source, 0) + 1
    
    return stats


@app.get("/health")
@limiter.limit("120/minute")  # Max 120 requests per minute per IP
async def health_check(request: Request):
    """
    Simple health check endpoint.
    
    Rate limit: 120 requests/minute
    
    Returns:
        Status information about the service
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(IST).isoformat(),
        "total_news_items": len(news_storage),
        "sources_count": len(RSS_FEEDS),
        "version": "2.0.0"
    }


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize the application on startup.
    
    - Performs initial news fetch
    - Starts the background scheduler
    """
    print("🚀 Starting FastAPI News Aggregation Service...")
    
    # Initial fetch with source-aware logic
    print("📰 Performing initial news fetch...")
    initial_news_by_source = await fetch_all_feeds()
    update_news_storage(initial_news_by_source)
    
    # Start global scheduler
    scheduler_instance.scheduler.add_job(
        scheduled_update,
        "interval",
        seconds=UPDATE_INTERVAL_SECONDS,
        id="news_update_job",
        replace_existing=True
    )
    scheduler_instance.start()
    print(f"⏰ Global Scheduler started (updates every {UPDATE_INTERVAL_SECONDS}s)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 Shutting down FastAPI News Aggregation Service...")


# ============================================================================
# NEWS TOOL CLASS (for use by AnalystAgent)
# ============================================================================

class NewsTool:
    """
    Lightweight wrapper around the RSS feed fetching logic.
    Used by the AnalystAgent to get news data without running the full FastAPI app.
    """

    def __init__(self):
        self.rss_feeds = RSS_FEEDS
        self.session = SESSION

    def _parse_target_date(self, query: str) -> Optional[datetime]:
        """
        Detect if the query contains a specific date or relative time.
        Returns a naive datetime object representing the target day.
        """
        if not query:
            return None
            
        q = query.lower()
        now = datetime.now(IST)
        
        # 1. Relative dates
        if "yesterday" in q:
            return now - timedelta(days=1)
        if "today" in q:
            return now
            
        # 2. Explicit Month/Day patterns (e.g., "8 April", "April 8")
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
            "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
        ]
        
        # Pattern: [digit] [month] or [month] [digit]
        for month in months:
            if month in q:
                # Try to find a digit near the month
                match = re.search(r'(\d{1,2})', q)
                if match:
                    try:
                        day = int(match.group(1))
                        month_idx = (months.index(month) % 12) + 1
                        # Assume current year if not specified
                        year = now.year
                        # If the user mentioned a year (e.g. 2026)
                        year_match = re.search(r'(\d{4})', q)
                        if year_match:
                            year = int(year_match.group(1))
                            
                        return datetime(year, month_idx, day)
                    except ValueError:
                        continue
        return None

    def fetch_latest_news(self, query: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        ZERO-LATENCY News Retrieval from in-memory cache.
        """
        # 1. Start with the full in-memory cache
        deduplicated = list(news_storage)

        # 2. Target Date Detection
        target_date = self._parse_target_date(query) if query else None
        
        # 3. Filter by Date if detected
        if target_date:
            filtered_by_date = []
            for item in deduplicated:
                pub_dt = item.get("published_datetime")
                if pub_dt:
                    pub_ist = pub_dt.astimezone(IST)
                    if (pub_ist.year == target_date.year and 
                        pub_ist.month == target_date.month and 
                        pub_ist.day == target_date.day):
                        filtered_by_date.append(item)
            
            if filtered_by_date:
                deduplicated = filtered_by_date

        # 4. Keyword Filtering (only if query isn't just a date)
        if query:
            q_lower = query.lower()
            stop_words = ["yesterday", "today", "news", "important", "market", "india", "indian"]
            keywords = [w for w in q_lower.split() if len(w) > 2 and w not in stop_words]
            
            if keywords:
                keyword_results = []
                for item in deduplicated:
                    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
                    if any(kw in text for kw in keywords):
                        keyword_results.append(item)
                
                if keyword_results:
                    deduplicated = keyword_results

        # 5. Return limited results
        results = []
        for item in deduplicated[:limit]:
            results.append({
                "source": item["source"],
                "title": item["title"],
                "summary": item["summary"],
                "link": item["link"],
                "date": item["date"]
            })

        # 6. Final Fallback: If ZERO results and query provided, return top 5 current news
        if not results and query and news_storage:
            print(f"Warning: No match for '{query}'. Providing top cache instead.")
            # Use Recursion-safe slice to avoid infinite loops
            for item in list(news_storage)[:5]:
                results.append({
                    "source": item["source"], "title": item["title"],
                    "summary": item["summary"], "link": item["link"], "date": item["date"]
                })

        return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info"
    )
