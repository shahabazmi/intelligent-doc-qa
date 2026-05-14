"""
Capture Streamlit UI screenshots of the running Enterprise Doc AI for the
report and presentation.

Three PDFs are expected to be indexed already:
  - NVIDIA-2025-Annual-Report.pdf
  - NASDAQ_TSLA_2024.pdf
  - pia-ncic-020723.pdf

Requires the dev servers to be running:
  uvicorn backend.main:app --reload --reload-dir backend   # :8000
  streamlit run frontend/app.py                            # :8501

Outputs PNG files into report/figures/.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://localhost:8501"
HERE = Path(__file__).parent
OUT = HERE / "figures"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}
DEVICE_SCALE = 2

LLM_TIMEOUT_MS = 240_000
SETTLE_MS = 1500


def shot(page, name: str, *, full_page: bool = True):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  saved -> {path}")
    return path


def wait_for_message_count(page, expected: int, timeout_ms: int = LLM_TIMEOUT_MS):
    deadline = time.time() + timeout_ms / 1000
    count = 0
    while time.time() < deadline:
        count = page.locator('[data-testid="stChatMessage"]').count()
        if count >= expected:
            return count
        time.sleep(0.5)
    raise PWTimeout(f"only saw {count} messages, expected {expected}")


def submit_query(page, text: str):
    box = page.locator('[data-testid="stChatInput"] textarea')
    box.click()
    box.fill(text)
    box.press("Enter")


def new_conversation(page):
    """Click the 'New conversation' button if present; otherwise reload."""
    try:
        btn = page.get_by_role("button", name="New chat")
        if btn.count():
            btn.first.click()
            page.wait_for_timeout(SETTLE_MS)
            return
    except Exception:
        pass
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(SETTLE_MS)


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=DEVICE_SCALE,
        )
        page = ctx.new_page()

        print(f"[1/5] Loading {BASE} ...")
        page.goto(BASE, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30_000)
        page.wait_for_timeout(SETTLE_MS + 1500)
        shot(page, "01_main_ui")

        # ---- PDF 1: NVIDIA ----
        print("[2/5] PDF 1 (NVIDIA Annual Report) - factual query ...")
        new_conversation(page)
        submit_query(page, "Who is the CEO of NVIDIA?")
        wait_for_message_count(page, 2)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "02_nvidia_query")

        # ---- PDF 2: Tesla ----
        print("[3/5] PDF 2 (Tesla 10-K) - numerical query ...")
        new_conversation(page)
        submit_query(page, "What was Tesla's total automotive revenue in 2024?")
        wait_for_message_count(page, 2)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "03_tesla_query")

        # ---- PDF 3: NCIC PIA ----
        print("[4/5] PDF 3 (NCIC PIA) - reasoning query ...")
        new_conversation(page)
        submit_query(page, "What is the purpose of the NCIC system as described in this document?")
        wait_for_message_count(page, 2)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "04_ncic_query")

        # ---- Multi-turn chat illustrating router behaviour ----
        print("[5/5] Multi-turn (router demo) ...")
        new_conversation(page)
        submit_query(page, "Summarise the NVIDIA annual report in three points")
        wait_for_message_count(page, 2)
        page.wait_for_timeout(SETTLE_MS)
        submit_query(page, "hello how are you")
        wait_for_message_count(page, 4)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "05_multi_turn_router")

        browser.close()

    print("\nAll screenshots saved to:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
