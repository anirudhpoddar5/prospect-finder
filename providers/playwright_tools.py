from playwright.sync_api import sync_playwright
from typing import Optional

_BROWSER = None
_CONTEXT = None


def _get_context():
    global _BROWSER, _CONTEXT
    if _CONTEXT is None:
        p = sync_playwright().start()
        _BROWSER = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        _CONTEXT = _BROWSER.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )
        _CONTEXT.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)
    return _CONTEXT


def fetch_page(url: str, timeout: int = 20) -> Optional[str]:
    try:
        ctx = _get_context()
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_timeout(3000)
        html = page.content()
        page.close()
        return html
    except Exception:
        return None


def close():
    global _BROWSER, _CONTEXT
    if _BROWSER:
        _BROWSER.close()
        _BROWSER = None
        _CONTEXT = None
