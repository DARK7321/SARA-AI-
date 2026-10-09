"""Playwright DOM-Aware Automation Engine for SARA."""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from packages.core.browser.errors import (
        BrowserActionCancelled,
        BrowserConnectionError,
        ElementNotFound,
        NavigationTimeout,
        PageNotFound,
        SearchFailed,
        VerificationFailed,
        is_cancelled,
    )
    from packages.core.browser.verification import BrowserVerifier
except ImportError:
    from browser_controller.errors import (
        BrowserActionCancelled,
        BrowserConnectionError,
        ElementNotFound,
        NavigationTimeout,
        PageNotFound,
        SearchFailed,
        VerificationFailed,
        is_cancelled,
    )
    from browser_controller.verification import BrowserVerifier

logger = logging.getLogger("omnibrain.browser.playwright_engine")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
except ImportError:
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None
    Playwright = None


class PlaywrightBrowserEngine:
    """Manages Playwright browser lifecycle with CDP attachment, persistent state, and DOM automation."""

    CDP_URL = "http://127.0.0.1:9222"
    DEFAULT_TIMEOUT_MS = 15000

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None
        self._is_cdp: bool = False
        self._lock = asyncio.Lock()

    async def is_ready(self) -> bool:
        """Check if browser engine has an active page and browser instance."""
        return self._browser is not None and self._active_page is not None and not self._active_page.is_closed()

    async def connect_or_launch(self, cancel_token: Optional[Any] = None) -> Page:
        """Connects via CDP to running Chrome, or launches a new browser instance."""
        if is_cancelled(cancel_token):
            raise BrowserActionCancelled("Cancelled before browser launch")

        if async_playwright is None:
            raise BrowserConnectionError("Playwright library is not installed in the Python environment")

        async with self._lock:
            # 1. Reuse existing valid page if alive
            if self._active_page and not self._active_page.is_closed():
                return self._active_page

            if not self._pw:
                self._pw = await async_playwright().start()

            # 2. Attempt CDP attachment (connect to existing Chrome session)
            try:
                logger.info(f"[Playwright] Attempting CDP connection to {self.CDP_URL}...")
                self._browser = await self._pw.chromium.connect_over_cdp(self.CDP_URL, timeout=2000)
                contexts = self._browser.contexts
                if contexts:
                    self._context = contexts[0]
                    pages = self._context.pages
                    self._active_page = pages[0] if pages else await self._context.new_page()
                else:
                    self._context = await self._browser.new_context()
                    self._active_page = await self._context.new_page()
                self._is_cdp = True
                logger.info("[Playwright] Successfully connected to existing Chrome instance over CDP.")
                return self._active_page
            except Exception as cdp_err:
                logger.info(f"[Playwright] CDP connection not available ({cdp_err}). Launching managed browser...")

            # 3. Launch Chrome with channel="chrome" and remote debugging enabled
            try:
                logger.info("[Playwright] Launching Chrome executable with remote debugging enabled...")
                self._browser = await self._pw.chromium.launch(
                    channel="chrome",
                    headless=self.headless,
                    args=[
                        "--remote-debugging-port=9222",
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                        "--no-default-browser-check",
                    ],
                    timeout=self.DEFAULT_TIMEOUT_MS,
                )
                self._context = await self._browser.new_context(no_viewport=True)
                self._active_page = await self._context.new_page()
                self._is_cdp = False
                logger.info("[Playwright] Managed Chrome launched successfully.")
                return self._active_page
            except Exception as chrome_err:
                logger.warning(f"[Playwright] Could not launch system Chrome ({chrome_err}). Trying bundled Chromium...")

            # 4. Fallback to bundled Chromium
            try:
                self._browser = await self._pw.chromium.launch(
                    headless=self.headless,
                    args=["--start-maximized", "--remote-debugging-port=9222"],
                    timeout=self.DEFAULT_TIMEOUT_MS,
                )
                self._context = await self._browser.new_context(no_viewport=True)
                self._active_page = await self._context.new_page()
                self._is_cdp = False
                logger.info("[Playwright] Bundled Chromium launched successfully.")
                return self._active_page
            except Exception as chromium_err:
                raise BrowserConnectionError(f"Failed all browser startup methods: {chromium_err}")

    async def search(self, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Perform DOM-aware browser search, wait for results, and verify outcome."""
        start_time = time.time()
        page = await self.connect_or_launch(cancel_token)

        if is_cancelled(cancel_token):
            raise BrowserActionCancelled("Search cancelled by user")

        logger.info(f"[Playwright] Starting search for: '{query}'")

        # 1. Check if page is already on a search engine
        current_url = page.url
        is_already_on_search = any(se in current_url for se in ["google.com", "bing.com", "duckduckgo.com"])

        # Semantic Locators for search input fields
        SEARCH_LOCATORS = [
            'textarea[name="q"]',
            'input[name="q"]',
            'input[type="search"]',
            'textarea[type="search"]',
            '[aria-label*="Search"]',
            '[aria-label*="खोजें"]',
            '[placeholder*="Search"]',
            '[placeholder*="खोजें"]',
            '#searchboxinput',
            'input.gLFyf',
        ]

        filled = False
        if is_already_on_search:
            for sel in SEARCH_LOCATORS:
                try:
                    locator = page.locator(sel).first
                    if await locator.count() > 0 and await locator.is_visible():
                        await locator.click()
                        await locator.fill(query)
                        await locator.press("Enter")
                        filled = True
                        logger.info(f"[Playwright] Filled search query using locator: {sel}")
                        break
                except Exception:
                    continue

        # 2. If not filled, navigate to Google directly with encoded query
        if not filled:
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            logger.info(f"[Playwright] Navigating directly to search URL: {search_url}")
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT_MS)
            except Exception as e:
                logger.warning(f"[Playwright] Direct navigation warning: {e}")

        # 3. Wait for search results container to appear
        try:
            await page.wait_for_selector(
                "#search, #rso, .g, #b_results, #links, div[data-async-context]",
                timeout=7000,
            )
        except Exception:
            # Let verification evaluate if results are rendered anyway
            pass

        # 4. Strict State & Result Verification
        verification = await BrowserVerifier.verify_search_results(page, query)
        duration_ms = int((time.time() - start_time) * 1000)

        result_payload = {
            "success": verification["verified"],
            "action": "search",
            "query": query,
            "url": verification["url"],
            "title": verification["title"],
            "method": "playwright",
            "duration_ms": duration_ms,
            "verification": verification,
        }

        if not verification["verified"]:
            raise VerificationFailed(f"Search results could not be verified for '{query}'", details=result_payload)

        return result_payload

    async def search_images(self, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Perform DOM-aware browser image search, wait for image results, and verify outcome."""
        start_time = time.time()
        page = await self.connect_or_launch(cancel_token)

        if is_cancelled(cancel_token):
            raise BrowserActionCancelled("Image search cancelled by user")

        logger.info(f"[Playwright] Starting image search for: '{query}'")

        # Direct navigation to Google Images with encoded query
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?udm=2&q={encoded_query}"
        logger.info(f"[Playwright] Navigating directly to image search URL: {search_url}")
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT_MS)
        except Exception as e:
            logger.warning(f"[Playwright] Image direct navigation warning: {e}")

        # Wait for image results container / grid items to appear
        try:
            await page.wait_for_selector(
                "div[data-ri], div.isv-r, img.Q4LuWd, div[jsname] img, #rso img",
                timeout=7000,
            )
        except Exception:
            pass

        # Strict State & Result Verification
        verification = await BrowserVerifier.verify_image_search_results(page, query)
        duration_ms = int((time.time() - start_time) * 1000)

        result_payload = {
            "success": verification["verified"],
            "action": "search_images",
            "query": query,
            "url": verification["url"],
            "title": verification["title"],
            "method": "playwright",
            "duration_ms": duration_ms,
            "verification": verification,
        }

        if not verification["verified"]:
            raise VerificationFailed(f"Image search results could not be verified for '{query}'", details=result_payload)

        return result_payload

    async def navigate(self, url: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Navigate to a specified URL and verify completion."""
        start_time = time.time()
        page = await self.connect_or_launch(cancel_token)

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        logger.info(f"[Playwright] Navigating to: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT_MS)
        except Exception as e:
            raise NavigationTimeout(f"Navigation timed out for {url}: {e}")

        title = await page.title()
        verified = await BrowserVerifier.verify_navigation(page, url)
        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "success": verified,
            "action": "navigate",
            "url": page.url,
            "title": title,
            "method": "playwright",
            "duration_ms": duration_ms,
        }

    async def click(self, target: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Click an element using semantic locator (text, role, or selector)."""
        page = await self.connect_or_launch(cancel_token)
        before_url = page.url
        before_title = await page.title()

        clicked = False
        # Strategy A: By exact/fuzzy text
        try:
            loc = page.get_by_text(target, exact=False).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=4000)
                clicked = True
        except Exception:
            pass

        # Strategy B: By role or selector
        if not clicked:
            try:
                loc = page.locator(target).first
                if await loc.count() > 0:
                    await loc.click(timeout=4000)
                    clicked = True
            except Exception:
                pass

        if not clicked:
            raise ElementNotFound(f"Could not locate clickable element matching '{target}'")

        await asyncio.sleep(1.0)
        verified = await BrowserVerifier.verify_element_clicked(page, before_url, before_title)

        return {
            "success": True,
            "action": "click",
            "target": target,
            "url": page.url,
            "state_changed": verified,
            "method": "playwright",
        }

    async def extract_content(self, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Extract readable text content and title from active page."""
        page = await self.connect_or_launch(cancel_token)
        title = await page.title()
        url = page.url
        try:
            text = await page.evaluate("() => document.body ? document.body.innerText.slice(0, 5000) : ''")
        except Exception:
            text = ""

        return {
            "success": True,
            "action": "extract",
            "url": url,
            "title": title,
            "content": text.strip(),
            "method": "playwright",
        }

    async def screenshot_diagnostic(self, output_path: Optional[str] = None) -> Optional[str]:
        """Capture screenshot for troubleshooting on failure."""
        if not self._active_page or self._active_page.is_closed():
            return None
        try:
            out_file = output_path or f"logs/browser_diagnostic_{int(time.time())}.png"
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            await self._active_page.screenshot(path=out_file)
            return out_file
        except Exception as e:
            logger.warning(f"Failed to capture diagnostic screenshot: {e}")
            return None

    async def close(self) -> None:
        """Safely close context and browser."""
        async with self._lock:
            try:
                if self._browser and not self._is_cdp:
                    await self._browser.close()
                if self._pw:
                    await self._pw.stop()
            except Exception:
                pass
            finally:
                self._browser = None
                self._context = None
                self._active_page = None
                self._pw = None
