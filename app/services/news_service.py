"""
Service to fetch, clean, and extract stock entities from Google News RSS.
Uses 7-day lookback queries ('when:7d').
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import html
from typing import List, Dict, Any
from app.config import DOMAINS, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    return html.unescape(" ".join(clean_text.split()))

def score_text_sentiment(text: str) -> float:
    """Calculate basic sentiment score from -1.0 (bearish) to 1.0 (bullish)."""
    text_lower = text.lower()
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return round((pos_count - neg_count) / total, 3)

def match_stock_tickers(text: str, domain_stocks: Dict[str, Dict[str, str]]) -> List[str]:
    """Find which tickers or company names are mentioned in the text."""
    matched = set()
    text_lower = text.lower()

    for ticker, info in domain_stocks.items():
        name = info["name"].lower()
        # Clean common corporate suffixes for matching
        short_name = re.sub(r"\b(corporation|corp|inc|incorporated|holdings|holding|technologies|platforms|ltd|company)\b", "", name).strip()

        # Check ticker symbol as a whole word
        ticker_pattern = rf"\b{re.escape(ticker)}\b"
        if re.search(ticker_pattern, text):
            matched.add(ticker)
            continue

        # Check company name or short name
        if short_name and len(short_name) >= 3 and short_name in text_lower:
            matched.add(ticker)
        elif name in text_lower:
            matched.add(ticker)

    return list(matched)

def fetch_google_news_rss(query: str, max_items: int = 40) -> List[Dict[str, Any]]:
    """Fetch and parse RSS items from Google News for a specific query."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error fetching Google News for '{query}': {e}")
        return []

    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"Error parsing RSS XML: {e}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    articles = []
    items = channel.findall("item")

    for item in items[:max_items]:
        title_elem = item.find("title")
        link_elem = item.find("link")
        pub_date_elem = item.find("pubDate")
        desc_elem = item.find("description")
        source_elem = item.find("source")

        raw_title = title_elem.text if title_elem is not None else ""
        link = link_elem.text if link_elem is not None else ""
        pub_date = pub_date_elem.text if pub_date_elem is not None else ""
        raw_desc = desc_elem.text if desc_elem is not None else ""
        source = source_elem.text if source_elem is not None else ""

        # Clean title: often formatted as "Headline - Source Name"
        title = raw_title
        if " - " in title and not source:
            parts = title.rsplit(" - ", 1)
            title = parts[0].strip()
            source = parts[1].strip()
        elif " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()

        snippet = clean_html(raw_desc)

        articles.append({
            "title": title,
            "url": link,
            "source": source or "Financial News",
            "published_at": pub_date,
            "snippet": snippet
        })

    return articles

def fetch_domain_news(domain_key: str) -> List[Dict[str, Any]]:
    """
    Fetch 7-day news for a specific domain (AI, Chips, Energy).
    Extracts relevant stocks and sentiment for each article.
    """
    domain_cfg = DOMAINS.get(domain_key)
    if not domain_cfg:
        return []

    queries = domain_cfg.get("queries", [])
    domain_stocks = domain_cfg.get("stocks", {})

    seen_titles = set()
    aggregated_articles = []

    for q in queries:
        items = fetch_google_news_rss(q, max_items=25)
        for it in items:
            t_norm = it["title"].lower().strip()
            if t_norm in seen_titles:
                continue
            seen_titles.add(t_norm)

            combined_text = f"{it['title']} {it['snippet']}"
            matched_tickers = match_stock_tickers(combined_text, domain_stocks)
            sent_score = score_text_sentiment(combined_text)

            sentiment_label = "bullish" if sent_score > 0.1 else ("bearish" if sent_score < -0.1 else "neutral")

            # Associate article
            it["domain"] = domain_key
            it["matched_tickers"] = matched_tickers
            it["sentiment_score"] = sent_score
            it["sentiment"] = sentiment_label
            # Primary ticker if available
            it["ticker"] = matched_tickers[0] if matched_tickers else ""

            aggregated_articles.append(it)

    return aggregated_articles
