"""
Capture screenshots of the running Streamlit UI for the LaTeX report.

Requires the dev servers to be running:
  uvicorn backend.main:app --reload --reload-dir backend   # :8000
  streamlit run frontend/app.py                            # :8501

Outputs PNG files into report/figures/.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeout

BASE = "http://localhost:8501"
HERE = Path(__file__).parent
OUT = HERE / "figures"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}
DEVICE_SCALE = 2  # crisp PNG for print

LLM_TIMEOUT_MS = 180_000   # 3-min ceiling for slow local LLM
SETTLE_MS = 1500           # post-render breathing room


def shot(page, name: str, *, full_page: bool = True):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  saved → {path}")
    return path


def wait_for_message_count(page, expected: int, timeout_ms: int = LLM_TIMEOUT_MS):
    """Wait until at least `expected` chat messages are visible."""
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        count = page.locator('[data-testid="stChatMessage"]').count()
        if count >= expected:
            return count
        time.sleep(0.5)
    raise PWTimeout(f"only saw {count} chat messages, expected {expected}")


def submit_query(page, text: str):
    """Type into the Streamlit chat_input and submit."""
    box = page.locator('[data-testid="stChatInput"] textarea')
    box.click()
    box.fill(text)
    box.press("Enter")


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=DEVICE_SCALE,
        )
        page = ctx.new_page()

        print(f"[1/4] Loading {BASE} …")
        page.goto(BASE, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30_000)
        page.wait_for_timeout(SETTLE_MS + 1500)
        shot(page, "01_main_ui")

        print("[2/4] Submitting first query (extractive document QA)…")
        submit_query(page, "Who is the instructor of the NLP course?")
        # 2 messages = user + assistant
        wait_for_message_count(page, 2)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "02_query_with_citations")

        print("[3/4] Submitting second query (multi-turn, financial doc)…")
        submit_query(page, "What was Tesla's total automotive revenue in 2024?")
        wait_for_message_count(page, 4)
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "03_multi_turn_chat")

        print("[4/4] Opening upload popover…")
        # Click the paperclip popover trigger (above chat input)
        popover_btn = page.locator('[data-testid="stPopover"] button').first
        popover_btn.click()
        page.wait_for_timeout(SETTLE_MS)
        shot(page, "04_upload_dialog", full_page=False)

        browser.close()

    print("\nAll screenshots saved to:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
