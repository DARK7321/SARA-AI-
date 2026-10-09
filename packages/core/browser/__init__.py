"""SARA Browser Automation Layer."""
try:
    from packages.core.browser.controller import BrowserController, get_browser_controller
    from packages.core.browser.actions import execute_browser_action
    from packages.core.browser.errors import (
        BrowserError,
        BrowserNotFound,
        BrowserConnectionError,
        PageNotFound,
        ElementNotFound,
        NavigationTimeout,
        SearchFailed,
        VerificationFailed,
        BrowserActionCancelled,
    )
    from packages.core.browser.verification import BrowserVerifier
except ImportError:
    from browser_controller.controller import BrowserController, get_browser_controller
    from browser_controller.actions import execute_browser_action
    from browser_controller.errors import (
        BrowserError,
        BrowserNotFound,
        BrowserConnectionError,
        PageNotFound,
        ElementNotFound,
        NavigationTimeout,
        SearchFailed,
        VerificationFailed,
        BrowserActionCancelled,
    )
    from browser_controller.verification import BrowserVerifier

__all__ = [
    "BrowserController",
    "get_browser_controller",
    "execute_browser_action",
    "BrowserError",
    "BrowserNotFound",
    "BrowserConnectionError",
    "PageNotFound",
    "ElementNotFound",
    "NavigationTimeout",
    "SearchFailed",
    "VerificationFailed",
    "BrowserActionCancelled",
    "BrowserVerifier",
]
