"""High-Level Browser Actions API and Dispatcher."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from packages.core.browser.controller import BrowserController, get_browser_controller
    from packages.core.browser.errors import BrowserError
except ImportError:
    from browser_controller.controller import BrowserController, get_browser_controller
    from browser_controller.errors import BrowserError

logger = logging.getLogger("omnibrain.browser.actions")


async def execute_browser_action(
    action: str,
    inputs: Dict[str, Any],
    controller: Optional[BrowserController] = None,
    cancel_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Dispatches high-level browser actions to BrowserController."""
    ctrl = controller or get_browser_controller()

    # Clean action string if formatted as capability (e.g. "browser.search" -> "search")
    op = action.replace("browser.", "").strip().lower()

    if op in ("open", "launch", "start"):
        return await ctrl.open_browser(cancel_token=cancel_token)

    elif op == "search":
        query = inputs.get("query") or inputs.get("text") or inputs.get("q")
        if not query:
            raise ValueError("Query is required for browser.search action")
        return await ctrl.search(query=query, cancel_token=cancel_token)

    elif op in ("search_images", "images", "image_search", "search_image"):
        query = inputs.get("query") or inputs.get("text") or inputs.get("q")
        if not query:
            raise ValueError("Query is required for browser.search_images action")
        return await ctrl.search_images(query=query, cancel_token=cancel_token)

    elif op == "navigate":
        url = inputs.get("url") or inputs.get("target")
        if not url:
            raise ValueError("URL is required for browser.navigate action")
        return await ctrl.navigate(url=url, cancel_token=cancel_token)

    elif op == "click":
        target = inputs.get("target") or inputs.get("text") or inputs.get("selector")
        if not target:
            raise ValueError("Target is required for browser.click action")
        return await ctrl.click(target=target, cancel_token=cancel_token)

    elif op in ("extract", "extract_content"):
        return await ctrl.extract_content(cancel_token=cancel_token)

    elif op == "close":
        await ctrl.close()
        return {"success": True, "action": "close"}

    else:
        raise ValueError(f"Unsupported browser action: {action}")
