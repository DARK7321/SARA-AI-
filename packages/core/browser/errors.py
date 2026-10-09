"""Structured exceptions for SARA Browser Automation Layer."""
from __future__ import annotations

from typing import Any, Dict, Optional


class BrowserError(Exception):
    """Base exception for all browser automation errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BrowserNotFound(BrowserError):
    """Raised when the target browser binary or process cannot be located."""
    pass


class BrowserConnectionError(BrowserError):
    """Raised when failing to attach via CDP or launch the browser instance."""
    pass


class PageNotFound(BrowserError):
    """Raised when an active page/tab is missing or was abruptly closed."""
    pass


class ElementNotFound(BrowserError):
    """Raised when a semantic locator fails to find the target element."""
    pass


class NavigationTimeout(BrowserError):
    """Raised when page load or navigation exceeds timeout limit."""
    pass


class SearchFailed(BrowserError):
    """Raised when a browser search action fails to submit or retrieve results."""
    pass


class VerificationFailed(BrowserError):
    """Raised when an action finishes but fails state-verification assertions."""
    pass


class BrowserActionCancelled(BrowserError):
    """Raised when execution is cancelled by STOP / ESC kill switch."""
    pass


def is_cancelled(token: Any = None) -> bool:
    """Check if cancellation has been requested across various token types."""
    if not token:
        return False
    if callable(token):
        try:
            return bool(token())
        except Exception:
            return False
    if hasattr(token, "is_cancelled"):
        return bool(token.is_cancelled)
    if hasattr(token, "is_set"):
        return bool(token.is_set())
    return False
