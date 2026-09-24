"""Web Search Connector for OmniBrain.

Enables Sara to search the internet in real-time using DuckDuckGo.
"""
from typing import Any, Dict, List
from duckduckgo_search import DDGS
import logging
import time

from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import ToolRequest, ToolResponse, ToolMetadata, ToolError, ErrorClass

logger = logging.getLogger("omnibrain.connectors.websearch")

class WebSearchConnector(BaseConnector):
    """Provides real-time internet search capabilities."""

    def __init__(self):
        super().__init__(
            connector_id="connector-websearch",
            name="Web Search",
            version="1.0"
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        start_time = time.time()
        try:
            if request.action == "web.search":
                raw_inputs = request.input or {}
                query = (
                    raw_inputs.get("query")
                    or raw_inputs.get("raw_command")
                    or raw_inputs.get("goal")
                    or raw_inputs.get("message")
                    or "latest news headlines"
                )
                max_results = raw_inputs.get("max_results", 4)
                results = self._search(str(query).strip(), max_results)
                from packages.core.security.injection import wrap_dict
                results = wrap_dict("websearch", results)
                latency_ms = int((time.time() - start_time) * 1000)
                return ToolResponse(
                    success=True,
                    data={"results": results},
                    metadata=ToolMetadata(latency_ms=latency_ms)
                )
            else:
                return ToolResponse(
                    success=False,
                    error=ToolError(error_class=ErrorClass.VALIDATION, message=f"Unknown capability: {request.action}")
                )
        except Exception as e:
            return ToolResponse(
                success=False,
                error=ToolError(error_class=ErrorClass.TOOL_UNAVAILABLE, message=str(e))
            )

    def _search(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        clean_q = (query or "").strip()
        if not clean_q:
            clean_q = "latest news headlines"

        logger.info(f"Executing multi-source web search for: '{query}'")
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # 1. Primary: DuckDuckGo HTML Live Web Search
        try:
            import httpx
            from bs4 import BeautifulSoup
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
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
                                "source": "web"
                            })
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")

        # 2. Fallback / Supplement: Google News RSS for real-time current news
        if len(results) < 2 and any(k in query.lower() for k in ["news", "latest", "today", "aaj", "current", "update"]):
            try:
                import httpx
                import xml.etree.ElementTree as ET
                import urllib.parse
                q_encoded = urllib.parse.quote(query)
                news_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=en-IN&gl=IN&ceid=IN:en"
                with httpx.Client(timeout=6.0) as client:
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
                                    "source": "google_news"
                                })
            except Exception as ex:
                logger.warning(f"Google News RSS error: {ex}")

        # 3. Fallback: Wikipedia Summary for entities, people, concepts
        if not results:
            try:
                import httpx
                import urllib.parse
                clean_q = query.replace("who is", "").replace("what is", "").replace("kya hai", "").strip()
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q)}"
                with httpx.Client(timeout=5.0) as client:
                    w_resp = client.get(wiki_url)
                    if w_resp.status_code == 200:
                        w_data = w_resp.json()
                        results.append({
                            "title": w_data.get("title", clean_q),
                            "url": w_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "snippet": w_data.get("extract", ""),
                            "source": "wikipedia"
                        })
            except Exception as ex:
                logger.warning(f"Wikipedia lookup error: {ex}")

        return results[:max_results]

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE",
            "connector_id": self.connector_id
        }

    def get_capabilities(self) -> List[str]:
        return ["web.search"]

