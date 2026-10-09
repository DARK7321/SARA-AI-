"""Unified Browser Controller for SARA.

Orchestrates Playwright DOM automation as primary engine, with graceful fallback to
native desktop / PyAutoGUI, controlled retry ladders, telemetry, and cancellation checks.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

try:
    from packages.core.browser.desktop_fallback import DesktopBrowserFallback
    from packages.core.browser.errors import (
        BrowserActionCancelled,
        BrowserError,
        SearchFailed,
        VerificationFailed,
        is_cancelled,
    )
    from packages.core.browser.playwright_engine import PlaywrightBrowserEngine
except ImportError:
    from browser_controller.desktop_fallback import DesktopBrowserFallback
    from browser_controller.errors import (
        BrowserActionCancelled,
        BrowserError,
        SearchFailed,
        VerificationFailed,
        is_cancelled,
    )
    from browser_controller.playwright_engine import PlaywrightBrowserEngine

logger = logging.getLogger("omnibrain.browser.controller")


class BrowserController:
    """High-level browser automation controller with primary Playwright and desktop fallback."""

    MAX_RETRIES = 3

    def __init__(self, headless: bool = False, diagnostic_mode: bool = False):
        self.diagnostic_mode = diagnostic_mode
        self.playwright_engine = PlaywrightBrowserEngine(headless=headless)
        self.desktop_fallback = DesktopBrowserFallback()
        
        # State tracking across multi-step commands
        self.current_url: Optional[str] = None
        self.current_title: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_search_query: Optional[str] = None

    async def open_browser(self, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Ensures browser is open and accessible."""
        self.last_action = "open"
        try:
            page = await self.playwright_engine.connect_or_launch(cancel_token)
            self.current_url = page.url
            self.current_title = await page.title()
            return {
                "success": True,
                "action": "open",
                "method": "playwright",
                "url": self.current_url,
                "title": self.current_title,
            }
        except Exception as e:
            logger.warning(f"[BrowserController] Playwright launch failed: {e}. Attempting desktop fallback...")
            # Fallback to desktop Chrome focus / launch
            res = self.desktop_fallback.focus_chrome_window()
            return {
                "success": res,
                "action": "open",
                "method": "desktop_fallback",
            }

    async def search(self, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Executes a search action with Playwright primary and desktop fallback."""
        start_time = time.time()
        self.last_action = "search"
        self.last_search_query = query

        last_error = None
        # Attempt 1 & 2: Playwright DOM automation
        for attempt in range(1, self.MAX_RETRIES):
            if is_cancelled(cancel_token):
                raise BrowserActionCancelled("Search cancelled by user")

            try:
                logger.info(f"[BrowserController] Executing search (Attempt {attempt}) for: '{query}'")
                result = await self.playwright_engine.search(query=query, cancel_token=cancel_token)
                self.current_url = result.get("url")
                self.current_title = result.get("title")

                # Telemetry record
                result["attempt"] = attempt
                result["fallback_used"] = False
                logger.info(f"[BrowserController] Search succeeded and verified on attempt {attempt}")
                return result
            except BrowserActionCancelled:
                raise
            except Exception as ex:
                logger.warning(f"[BrowserController] Search attempt {attempt} failed: {ex}")
                last_error = ex
                await asyncio.sleep(0.5)

        # Attempt 3: Desktop Fallback (PyAutoGUI + OS address bar)
        logger.info(f"[BrowserController] Falling back to desktop automation for query: '{query}'")
        try:
            fb_res = self.desktop_fallback.search(query=query, cancel_token=cancel_token)
            fb_res["attempt"] = self.MAX_RETRIES
            fb_res["fallback_used"] = True
            fb_res["duration_ms"] = int((time.time() - start_time) * 1000)
            if fb_res.get("success"):
                self.current_url = fb_res.get("url")
                return fb_res
        except Exception as fb_err:
            last_error = fb_err

        # Diagnostic capture on total failure
        if self.diagnostic_mode:
            screenshot_path = await self.playwright_engine.screenshot_diagnostic()
            logger.info(f"[BrowserController] Diagnostic screenshot captured at: {screenshot_path}")

        raise SearchFailed(
            f"Failed to complete search for '{query}' after {self.MAX_RETRIES} attempts. Reason: {last_error}",
            details={"query": query, "last_error": str(last_error)},
        )

    async def search_images(self, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Executes an image search action with Playwright primary and desktop fallback."""
        start_time = time.time()
        self.last_action = "search_images"
        self.last_search_query = query

        last_error = None
        # Attempt 1 & 2: Playwright DOM automation
        for attempt in range(1, self.MAX_RETRIES):
            if is_cancelled(cancel_token):
                raise BrowserActionCancelled("Image search cancelled by user")

            try:
                logger.info(f"[BrowserController] Executing image search (Attempt {attempt}) for: '{query}'")
                result = await self.playwright_engine.search_images(query=query, cancel_token=cancel_token)
                self.current_url = result.get("url")
                self.current_title = result.get("title")

                result["attempt"] = attempt
                result["fallback_used"] = False
                logger.info(f"[BrowserController] Image search succeeded and verified on attempt {attempt}")
                return result
            except BrowserActionCancelled:
                raise
            except Exception as ex:
                logger.warning(f"[BrowserController] Image search attempt {attempt} failed: {ex}")
                last_error = ex
                await asyncio.sleep(0.5)

        # Attempt 3: Desktop Fallback (PyAutoGUI + OS address bar)
        logger.info(f"[BrowserController] Falling back to desktop automation for image search: '{query}'")
        try:
            fb_res = self.desktop_fallback.search_images(query=query, cancel_token=cancel_token)
            fb_res["attempt"] = self.MAX_RETRIES
            fb_res["fallback_used"] = True
            fb_res["duration_ms"] = int((time.time() - start_time) * 1000)
            if fb_res.get("success"):
                self.current_url = fb_res.get("url")
                return fb_res
        except Exception as fb_err:
            last_error = fb_err

        if self.diagnostic_mode:
            screenshot_path = await self.playwright_engine.screenshot_diagnostic()
            logger.info(f"[BrowserController] Diagnostic screenshot captured at: {screenshot_path}")

        raise SearchFailed(
            f"Failed to complete image search for '{query}' after {self.MAX_RETRIES} attempts. Reason: {last_error}",
            details={"query": query, "last_error": str(last_error)},
        )

    async def navigate(self, url: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Navigate to URL with retry and desktop fallback."""
        self.last_action = "navigate"
        try:
            res = await self.playwright_engine.navigate(url=url, cancel_token=cancel_token)
            self.current_url = res.get("url")
            self.current_title = res.get("title")
            return res
        except Exception as e:
            logger.warning(f"[BrowserController] Playwright navigation failed: {e}. Trying desktop fallback...")
            fb_res = self.desktop_fallback.navigate(url)
            fb_res["fallback_used"] = True
            return fb_res

    async def click(self, target: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Click element by target text, role, or selector."""
        self.last_action = "click"
        try:
            return await self.playwright_engine.click(target=target, cancel_token=cancel_token)
        except Exception as e:
            logger.warning(f"[BrowserController] Playwright click failed: {e}")
            raise

    async def extract_content(self, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Extract content from active page."""
        self.last_action = "extract"
        return await self.playwright_engine.extract_content(cancel_token=cancel_token)

    async def close(self) -> None:
        """Close browser resources."""
        await self.playwright_engine.close()


# Global Singleton for SARA
_browser_controller_instance: Optional[BrowserController] = None

def get_browser_controller() -> BrowserController:
    global _browser_controller_instance
    if _browser_controller_instance is None:
        _browser_controller_instance = BrowserController(headless=False)
    return _browser_controller_instance
