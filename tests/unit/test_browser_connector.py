"""Unit tests for Browser Web Extractor Universal Tool Connector."""
import pytest
from packages.connectors.browser.client import BrowserConnector
from packages.connectors.browser.actions import SimpleHTMLTextExtractor
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_browser_extract_content_sandbox():
    connector = BrowserConnector(force_sandbox=True)
    req = ToolRequest(
        request_id="req_browser_1",
        tool="connector-browser",
        action="browser.extract_content",
        input={"url": "https://news.ycombinator.com", "include_links": True},
        context=ToolContext(task_id="t_br", step_id="s_br1"),
        idempotency_key="key_br_1",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "Hacker News" in res.data["title"]
    assert "OmniBrain" in res.data["content"]
    assert res.data["word_count"] > 0
    assert len(res.data.get("links", [])) > 0
    assert res.verification_hints["check"] == "content_extracted"

    # Verification check
    verified = await connector.verify(req.action, res.data)
    assert verified is True


@pytest.mark.asyncio
async def test_browser_extract_generic_url_sandbox():
    connector = BrowserConnector(force_sandbox=True)
    req = ToolRequest(
        request_id="req_browser_2",
        tool="connector-browser",
        action="browser.extract_content",
        input={"url": "https://example.com/blog/article"},
        context=ToolContext(task_id="t_br", step_id="s_br2"),
        idempotency_key="key_br_2",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "example.com" in res.data["title"]
    assert len(res.data["content"]) > 0


@pytest.mark.asyncio
async def test_browser_dry_run():
    connector = BrowserConnector()
    req = ToolRequest(
        request_id="req_browser_3",
        tool="connector-browser",
        action="browser.extract_content",
        input={"url": "https://python.org"},
        context=ToolContext(task_id="t_br", step_id="s_br3"),
        idempotency_key="key_br_3",
        dry_run=True,
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["simulated"] is True
    assert res.verification_hints["dry_run"] is True


def test_html_parser_extractor():
    parser = SimpleHTMLTextExtractor()
    html_content = """
    <html>
        <head><title>Test Page Title</title></head>
        <body>
            <script>var x = 10;</script>
            <style>body { color: red; }</style>
            <h1>Welcome to OmniBrain</h1>
            <p>This is a paragraph with a <a href="https://example.com">link</a>.</p>
        </body>
    </html>
    """
    parser.feed(html_content)
    assert parser.title == "Test Page Title"
    text = parser.get_text()
    assert "Welcome to OmniBrain" in text
    assert "This is a paragraph with a link." in text
    assert "var x = 10" not in text
    assert "color: red" not in text
    assert len(parser.links) == 1
    assert parser.links[0]["href"] == "https://example.com"

