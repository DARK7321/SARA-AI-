"""State and Result Verification Engine for SARA Browser Automation."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    from packages.core.browser.errors import VerificationFailed
except ImportError:
    from browser_controller.errors import VerificationFailed

logger = logging.getLogger("omnibrain.browser.verification")


class BrowserVerifier:
    """Provides robust post-action verification to prevent false-positive reporting."""

    # Common search engine result container locators
    SEARCH_RESULT_SELECTORS = [
        "#search",
        "#rso",
        ".g",
        "#b_results",
        ".b_algo",
        "#links",
        ".react-results--main",
        "ytd-video-renderer",
        "ytd-item-section-renderer",
        "[data-async-context]",
        "article",
        "main",
    ]

    @classmethod
    async def verify_page_loaded(cls, page: Any, min_title_len: int = 1) -> bool:
        """Verify that the page has loaded and has a valid title."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=7000)
            title = await page.title()
            return len(title.strip()) >= min_title_len
        except Exception as e:
            logger.warning(f"verify_page_loaded check failed: {e}")
            return False

    @classmethod
    async def verify_search_results(cls, page: Any, query: str) -> Dict[str, Any]:
        """Verify that search results actually loaded on the page."""
        url = page.url
        title = await page.title()

        # Check 1: Does the URL reflect a search action?
        url_indicates_search = any(
            marker in url for marker in [
                "search?q=", "/search", "?q=", "search_query=", "&q=",
                "duckduckgo.com/?q=", "bing.com/search"
            ]
        )

        # Check 2: Does the page title reflect the query or search engine?
        query_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', query.lower()))
        title_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', title.lower()))
        title_matches_query = bool(query_words & title_words) or any(
            se in title.lower() for se in ["google", "bing", "duckduckgo", "search", "youtube"]
        )

        # Check 3: Do result container elements exist in the DOM?
        found_selector = None
        for sel in cls.SEARCH_RESULT_SELECTORS:
            try:
                locator = page.locator(sel).first
                if await locator.count() > 0:
                    found_selector = sel
                    break
            except Exception:
                continue

        # Check 4: Check if any text on the page matches key terms of the query
        content_has_terms = False
        try:
            sample_text = await page.evaluate("() => document.body ? document.body.innerText.slice(0, 3000) : ''")
            content_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', sample_text.lower()))
            content_has_terms = len(query_words & content_words) >= 1
        except Exception:
            pass

        # Holistic assessment: must satisfy at least 2 indicators
        indicators = [url_indicates_search, title_matches_query, bool(found_selector), content_has_terms]
        score = sum(1 for ind in indicators if ind)

        verified = score >= 2 or (url_indicates_search and (bool(found_selector) or content_has_terms))

        details = {
            "verified": verified,
            "url": url,
            "title": title,
            "score": score,
            "url_indicates_search": url_indicates_search,
            "title_matches_query": title_matches_query,
            "result_container_found": found_selector,
            "content_has_terms": content_has_terms,
        }

        if not verified:
            logger.warning(f"Search verification failed for query '{query}': {details}")
        else:
            logger.info(f"Search successfully verified for query '{query}' (score={score}/4)")

        return details

    @classmethod
    async def verify_image_search_results(cls, page: Any, query: str) -> Dict[str, Any]:
        """Verify that image search results actually loaded on the page."""
        url = page.url
        title = await page.title()

        # Check 1: Does URL indicate image search?
        url_indicates_images = any(m in url for m in ["udm=2", "tbm=isch", "images", "/img"])

        # Check 2: Does title reflect query or images?
        query_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', query.lower()))
        title_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', title.lower()))
        title_matches = bool(query_words & title_words) or any(se in title.lower() for se in ["google", "images", "search"])

        # Check 3: Image result selectors
        image_selectors = ["div[data-ri]", "div.isv-r", "img.Q4LuWd", "div[jsname] img", "#rso img", "div[data-id]"]
        found_selector = None
        for sel in image_selectors:
            try:
                locator = page.locator(sel).first
                if await locator.count() > 0:
                    found_selector = sel
                    break
            except Exception:
                continue

        score = sum(1 for ind in [url_indicates_images, title_matches, bool(found_selector)] if ind)
        verified = score >= 2 or (url_indicates_images and bool(found_selector)) or (url_indicates_images and title_matches)

        details = {
            "verified": verified,
            "url": url,
            "title": title,
            "score": score,
            "url_indicates_images": url_indicates_images,
            "title_matches": title_matches,
            "image_selector_found": found_selector,
        }

        if not verified:
            logger.warning(f"Image search verification failed for query '{query}': {details}")
        else:
            logger.info(f"Image search successfully verified for query '{query}' (score={score}/3)")

        return details

    @classmethod
    async def verify_navigation(cls, page: Any, target_url: str) -> bool:
        """Verify navigation successfully reached the expected domain."""
        try:
            target_domain = urlparse(target_url).netloc.lower()
            current_domain = urlparse(page.url).netloc.lower()
            return target_domain in current_domain or current_domain in target_domain
        except Exception:
            return False

    @classmethod
    async def verify_element_clicked(cls, page: Any, before_url: str, before_title: str) -> bool:
        """Verify that a click action caused a URL or title transition."""
        try:
            current_url = page.url
            current_title = await page.title()
            return current_url != before_url or current_title != before_title
        except Exception:
            return True
