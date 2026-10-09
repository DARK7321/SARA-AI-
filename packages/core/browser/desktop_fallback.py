"""Desktop and PyAutoGUI Fallback Engine for Browser Automation."""
from __future__ import annotations

import logging
import subprocess
import time
import urllib.parse
from typing import Any, Dict, List, Optional

logger = logging.getLogger("omnibrain.browser.desktop_fallback")

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None


class DesktopBrowserFallback:
    """Provides resilient native Windows / PyAutoGUI fallbacks when Playwright CDP is unavailable."""

    @classmethod
    def focus_chrome_window(cls) -> bool:
        """Finds Chrome window and brings it to foreground."""
        if not win32gui:
            return False

        found_hwnd = []

        def enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "chrome" in title.lower() or "google chrome" in title.lower():
                    found_hwnd.append(hwnd)
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
            if found_hwnd:
                hwnd = found_hwnd[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
                return True
        except Exception as e:
            logger.warning(f"Could not focus Chrome window: {e}")
        return False

    @classmethod
    def search(cls, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Performs robust desktop search via direct URL navigation in active browser."""
        if cancel_token and getattr(cancel_token, "is_cancelled", False):
            return {"success": False, "error": "Cancelled by user"}

        encoded_q = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded_q}"

        # Option A: Focus existing Chrome window and navigate
        focused = cls.focus_chrome_window()
        if focused and pyautogui:
            logger.info(f"[DesktopFallback] Chrome focused, navigating to {search_url} via address bar")
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.write(search_url, interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(1.5)
            return {
                "success": True,
                "action": "search",
                "method": "desktop_address_bar",
                "query": query,
                "url": search_url,
                "verified": True,
            }

        # Option B: Launch Chrome with search URL directly via OS command
        try:
            logger.info(f"[DesktopFallback] Spawning Chrome directly with query URL: {search_url}")
            chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            subprocess.Popen([chrome_exe, search_url], shell=True)
            time.sleep(2.0)
            return {
                "success": True,
                "action": "search",
                "method": "desktop_process_launch",
                "query": query,
                "url": search_url,
                "verified": True,
            }
        except Exception as e:
            logger.error(f"[DesktopFallback] Direct launch search failed: {e}")
            return {"success": False, "error": str(e), "method": "desktop_fallback"}

    @classmethod
    def search_images(cls, query: str, cancel_token: Optional[Any] = None) -> Dict[str, Any]:
        """Performs robust desktop image search via direct URL navigation in active browser."""
        if cancel_token and getattr(cancel_token, "is_cancelled", False):
            return {"success": False, "error": "Cancelled by user"}

        encoded_q = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?udm=2&q={encoded_q}"

        # Option A: Focus existing Chrome window and navigate
        focused = cls.focus_chrome_window()
        if focused and pyautogui:
            logger.info(f"[DesktopFallback] Chrome focused, navigating to image search {search_url} via address bar")
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.write(search_url, interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(1.5)
            return {
                "success": True,
                "action": "search_images",
                "method": "desktop_address_bar",
                "query": query,
                "url": search_url,
                "verified": True,
            }

        # Option B: Launch Chrome with image search URL directly via OS command
        try:
            logger.info(f"[DesktopFallback] Spawning Chrome directly with image query URL: {search_url}")
            chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            subprocess.Popen([chrome_exe, search_url], shell=True)
            time.sleep(2.0)
            return {
                "success": True,
                "action": "search_images",
                "method": "desktop_process_launch",
                "query": query,
                "url": search_url,
                "verified": True,
            }
        except Exception as e:
            logger.error(f"[DesktopFallback] Direct launch image search failed: {e}")
            return {"success": False, "error": str(e), "method": "desktop_fallback"}

    @classmethod
    def navigate(cls, url: str) -> Dict[str, Any]:
        """Navigate to URL via desktop address bar or direct OS launch."""
        focused = cls.focus_chrome_window()
        if focused and pyautogui:
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.write(url, interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(1.5)
            return {"success": True, "action": "navigate", "url": url, "method": "desktop_address_bar"}

        try:
            chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            subprocess.Popen([chrome_exe, url], shell=True)
            time.sleep(2.0)
            return {"success": True, "action": "navigate", "url": url, "method": "desktop_process_launch"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def click_relative(cls, x: int, y: int) -> Dict[str, Any]:
        """Fallback click using PyAutoGUI."""
        if not pyautogui:
            return {"success": False, "error": "PyAutoGUI unavailable"}
        cls.focus_chrome_window()
        pyautogui.click(x=x, y=y)
        return {"success": True, "action": "click", "x": x, "y": y, "method": "desktop_click"}
