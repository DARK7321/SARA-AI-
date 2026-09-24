"""Real-Time Internet Web Research & Grounding Engine for SARA.

Searches live web (DuckDuckGo, Google News RSS, Wikipedia) in real-time
and formats cited snippets for AI synthesis.
"""
import logging
import urllib.parse
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger("omnibrain.brain.web_research")

RESEARCH_KEYWORDS = [
    "search", "research", "internet", "google", "news", "khabar", "aaj",
    "today", "latest", "current", "price", "bhav", "score", "weather",
    "mausam", "kya chal raha", "trends", "update", "updates", "who is",
    "kon hai", "dhundho", "dhundo", "khojo", "check karo", "online",
    "समाचार", "ताज़ा", "खबर", "सर्च", "इंटरनेट", "रिसर्च"
]


def is_research_query(message: str) -> bool:
    """Detect if a user prompt requires real-time live internet information."""
    msg = message.lower().strip()
    return any(kw in msg for kw in RESEARCH_KEYWORDS)


def search_web_realtime(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Fetch multi-source real-time search results (DDG + Google News + Wikipedia)."""
    clean_q = query.strip()
    if not clean_q:
        return []

    # Clean conversational filler for better search query
    filler_words = [
        "sara", "mujhe", "batao", "kya", "hai", "karo", "can", "you", "please",
        "search", "research", "on", "the", "internet", "google", "par", "pe"
    ]
    words = clean_q.split()
    meaningful = [w for w in words if w.lower() not in filler_words]
    search_q = " ".join(meaningful) if len(meaningful) >= 2 else clean_q

    results: List[Dict[str, str]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # 1. DuckDuckGo Live Web Search
    try:
        with httpx.Client(timeout=7.0, follow_redirects=True) as client:
            resp = client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": search_q},
                headers=headers
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for res in soup.find_all("div", class_="result")[:max_results]:
                    title_el = res.find("a", class_="result__a")
                    snippet_el = res.find("a", class_="result__snippet")
                    if title_el and snippet_el:
                        results.append({
                            "title": title_el.text.strip(),
                            "url": title_el.get("href", ""),
                            "snippet": snippet_el.text.strip(),
                            "source": "Web"
                        })
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    # 2. Google News RSS for live headlines & breaking news
    if len(results) < 2 or any(k in clean_q.lower() for k in ["news", "latest", "today", "aaj", "headline"]):
        try:
            news_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_q)}&hl=en-IN&gl=IN&ceid=IN:en"
            with httpx.Client(timeout=5.0) as client:
                n_resp = client.get(news_url)
                if n_resp.status_code == 200:
                    root = ET.fromstring(n_resp.text)
                    for item in root.findall(".//item")[:max_results]:
                        t = item.find("title")
                        l = item.find("link")
                        d = item.find("pubDate")
                        if t is not None:
                            results.append({
                                "title": t.text,
                                "url": l.text if l is not None else "",
                                "snippet": f"Published: {d.text if d is not None else 'Recently'}",
                                "source": "Google News"
                            })
        except Exception as ex:
            logger.warning(f"Google News RSS failed: {ex}")

    # 3. Wikipedia for definitions, people, entities
    if not results:
        try:
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(search_q)}"
            with httpx.Client(timeout=4.0) as client:
                w_resp = client.get(wiki_url)
                if w_resp.status_code == 200:
                    w_data = w_resp.json()
                    results.append({
                        "title": w_data.get("title", search_q),
                        "url": w_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "snippet": w_data.get("extract", ""),
                        "source": "Wikipedia"
                    })
        except Exception:
            pass

    return results[:max_results]


def format_research_context(results: List[Dict[str, str]]) -> str:
    """Format search results into grounded markdown context for LLM prompt."""
    if not results:
        return ""

    lines = ["\n### 🌐 Real-Time Live Internet Research Data (Current Grounding):"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. [{r.get('source', 'Web')}] **{r.get('title', 'Source')}**\n"
            f"   - URL: {r.get('url', 'N/A')}\n"
            f"   - Facts: {r.get('snippet', '')}"
        )
    lines.append("\nINSTRUCTION FOR SARA: Ground your response in the real-time facts above. Mention key sources naturally and deliver a deep, accurate, well-reasoned answer in your warm personality.\n")
    return "\n".join(lines)
