"""Browser Web Extractor Action handlers with sandbox support."""
import re
import time
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
import httpx


class SimpleHTMLTextExtractor(HTMLParser):
    """HTML parser to extract text and links cleanly without external deps."""

    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.title = ""
        self.links: List[Dict[str, str]] = []
        self._in_title = False
        self._skip_tag = False
        self._current_href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._skip_tag = True
        elif tag_lower == "title":
            self._in_title = True
        elif tag_lower == "a":
            for attr_name, val in attrs:
                if attr_name.lower() == "href" and val:
                    self._current_href = val

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._skip_tag = False
        elif tag_lower == "title":
            self._in_title = False
        elif tag_lower == "a":
            self._current_href = None
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self.text_parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_tag:
            return
        cleaned = data.strip()
        if not cleaned:
            return
        if self._in_title:
            self.title += (" " if self.title else "") + cleaned
        else:
            self.text_parts.append(cleaned)
            if self._current_href:
                self.links.append({"text": cleaned, "href": self._current_href})

    def get_text(self) -> str:
        raw = " ".join(self.text_parts)
        # Normalize punctuation spacing and excessive newlines
        raw = re.sub(r"\s+([.,!?:;])", r"\1", raw)
        return re.sub(r"\n\s*\n+", "\n\n", raw).strip()


class BrowserSandbox:
    """In-memory browser extractor sandbox for testing and offline execution."""

    def __init__(self):
        self.mock_pages: Dict[str, Dict[str, Any]] = {
            "https://news.ycombinator.com": {
                "title": "Hacker News",
                "text": "1. OmniBrain v2 Released: Autonomous AI Operating System (omnibrain.dev) | 452 points by ai_builder 2 hours ago | 128 comments\n2. Show HN: High-performance pgvector workflows (github.com) | 210 points | 45 comments",
                "links": [
                    {"text": "OmniBrain v2 Released", "href": "https://omnibrain.dev"},
                    {"text": "Show HN: High-performance pgvector workflows", "href": "https://github.com"},
                ],
            },
            "https://docs.omnibrain.local": {
                "title": "OmniBrain Documentation",
                "text": "OmniBrain is a 100% free autonomous AI operating system powered by Gemini, PostgreSQL, and Redis.",
                "links": [
                    {"text": "Getting Started", "href": "/getting-started"},
                    {"text": "Architecture", "href": "/architecture"},
                ],
            },
        }

    def extract_content(
        self,
        url: str,
        include_links: bool = False,
    ) -> Dict[str, Any]:
        if url in self.mock_pages:
            page = self.mock_pages[url]
            res = {
                "url": url,
                "title": page["title"],
                "content": page["text"],
                "word_count": len(page["text"].split()),
            }
            if include_links:
                res["links"] = page.get("links", [])
            return res

        # Generic simulated web page
        domain = url.split("//")[-1].split("/")[0]
        content = f"Simulated web page content extracted from {url}. Contains key operational metrics and technical documentation."
        res = {
            "url": url,
            "title": f"Page at {domain}",
            "content": content,
            "word_count": len(content.split()),
        }
        if include_links:
            res["links"] = [{"text": "Home", "href": f"https://{domain}"}]
        return res


class BrowserActions:
    """Dispatches web extraction actions to live web or sandbox."""

    def __init__(self, sandbox: Optional[BrowserSandbox] = None):
        self.sandbox = sandbox or BrowserSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        force_sandbox: bool = False,
    ) -> Any:
        if action in ("browser.search", "browser.search_images", "browser.open", "browser.navigate"):
            from packages.core.browser.actions import execute_browser_action
            return await execute_browser_action(action, inputs)

        if action != "browser.extract_content":
            raise ValueError(f"Unsupported Browser action: {action}")

        url = inputs.get("url", "")
        if not url:
            raise ValueError("URL is required for browser.extract_content")

        include_links = bool(inputs.get("include_links", False))

        # Check for mock/test URLs or forced sandbox
        if force_sandbox or url.startswith(("mock://", "test://", "http://mock", "https://mock")):
            return self.sandbox.extract_content(url=url, include_links=include_links)

        # Attempt live web page fetch
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OmniBrain/2.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html_body = resp.text

            parser = SimpleHTMLTextExtractor()
            parser.feed(html_body)

            extracted_text = parser.get_text()
            title = parser.title or url

            result = {
                "url": url,
                "title": title,
                "content": extracted_text[:10000],  # cap at 10k chars for prompt safety
                "word_count": len(extracted_text.split()),
                "status_code": resp.status_code,
            }
            if include_links:
                result["links"] = parser.links[:50]
            return result

        except Exception as err:
            # Fall back gracefully to sandbox if network is unavailable
            fallback = self.sandbox.extract_content(url=url, include_links=include_links)
            fallback["warning"] = f"Live fetch failed ({str(err)}), returned sandbox snapshot"
            return fallback

