"""
CISCE Result Checker — Playwright + EasyOCR
============================================
• Runs 10 tabs in parallel
• Loops FOREVER until results are live
• Full-page screenshot saved on success
• All tabs stop the moment any one succeeds

Install dependencies:
    pip install playwright easyocr pillow opencv-python-headless
    playwright install chromium
"""

import asyncio
import re
import os
import cv2
import numpy as np
import easyocr
from PIL import Image, ImageEnhance, ImageFilter
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG — edit these before running
# ─────────────────────────────────────────────
URL           = "https://results.cisce.org/"
CENTER_CODE   = "1266827"   # INDEX NO. first field  → #CenterCode
SERIAL_NO     = "067"       # INDEX NO. second field → #SerialNumber
UNIQUE_ID     = "8843111"   # UID field              → #UniqueId
COURSE        = "ICSE"      # dropdown               → #courseDropDown
NUM_TABS      = 10              # parallel tabs
RETRY_DELAY   = 5               # seconds between retries per tab
HEADLESS      = False           # set True to hide browser
SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "CISCE_Results")
# ─────────────────────────────────────────────

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Global stop flag — set to True the moment any tab succeeds
stop_event = asyncio.Event()

print("⏳ Loading EasyOCR model (first run may take ~30 sec)...")
reader = easyocr.Reader(["en"], gpu=False, verbose=False)
print("✅ EasyOCR ready.\n")


# ──────────────────────────────────────────────────────────
#  IMAGE PROCESSING
# ──────────────────────────────────────────────────────────

def preprocess_captcha(path: str) -> str:
    """Grayscale → upscale 3x → sharpen → binarise for better OCR."""
    img = Image.open(path).convert("L")
    img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(2.5)
    arr = np.array(img)
    _, arr = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out_path = path.replace(".png", "_proc.png")
    Image.fromarray(arr).save(out_path)
    return out_path


def clean_ocr(raw: str) -> str:
    """Strip everything except alphanumeric characters."""
    return re.sub(r"[^A-Za-z0-9]", "", raw.strip().replace(" ", ""))


# ──────────────────────────────────────────────────────────
#  CAPTCHA SOLVER
# ──────────────────────────────────────────────────────────

async def solve_captcha(page, tab_id: int) -> str:
    captcha_selectors = [
        "img[src*='captcha']",
        "img[id*='captcha' i]",
        "img[class*='captcha' i]",
        "#captchaImage",
        ".captchaImage",
    ]

    captcha_el = None
    for sel in captcha_selectors:
        try:
            captcha_el = await page.wait_for_selector(sel, timeout=4000)
            if captcha_el:
                break
        except PlaywrightTimeout:
            continue

    raw_path = os.path.join(SCREENSHOT_DIR, f"captcha_tab{tab_id}.png")

    if captcha_el:
        await captcha_el.screenshot(path=raw_path)
    else:
        await page.screenshot(path=raw_path)

    proc_path = preprocess_captcha(raw_path)
    results = reader.readtext(
        proc_path, detail=0,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    )
    text = clean_ocr(" ".join(results))
    print(f"   [Tab {tab_id:02d}] 🔤 CAPTCHA → '{text}'")
    return text


# ──────────────────────────────────────────────────────────
#  SINGLE ATTEMPT
# ──────────────────────────────────────────────────────────

async def run_attempt(page, tab_id: int, attempt: int) -> bool:
    log = lambda msg: print(f"[Tab {tab_id:02d}] {msg}")

    # 1. Load page
    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    except PlaywrightTimeout:
        log("⚠️  Page load timed out")
        return False

    # 2. Wait for form fields to appear
    try:
        await page.wait_for_selector("#CenterCode", timeout=20000)
    except PlaywrightTimeout:
        log("⚠️  Form not visible — results probably not live yet")
        return False

    # 3. Select ICSE from dropdown
    try:
        await page.select_option("#courseDropDown", label=COURSE)
        await page.wait_for_timeout(600)
    except Exception as e:
        log(f"⚠️  Dropdown error: {e}")
        return False

    # 4. Fill input fields
    await page.fill("#CenterCode",   CENTER_CODE)
    await page.fill("#SerialNumber", SERIAL_NO)
    await page.fill("#UniqueId",     UNIQUE_ID)

    # 5. Solve CAPTCHA
    captcha_text = await solve_captcha(page, tab_id)
    if not captcha_text:
        log("⚠️  Empty CAPTCHA — retrying")
        return False

    # 6. Enter CAPTCHA text
    captcha_input_selectors = [
        "input[name*='captcha' i]",
        "input[id*='captcha' i]",
        "#captchaTextBox",
        "#CaptchaInputText",
        ".captcha input",
    ]
    captcha_input = None
    for sel in captcha_input_selectors:
        try:
            captcha_input = await page.wait_for_selector(sel, timeout=3000)
            if captcha_input:
                break
        except PlaywrightTimeout:
            continue

    if not captcha_input:
        log("⚠️  CAPTCHA input box not found")
        return False

    await captcha_input.fill(captcha_text)

    # 7. Submit the form
    submit_selectors = [
        "input[type='submit']",
        "button[type='submit']",
        "#btnShow",
        "#submitBtn",
        "button:has-text('Show Result')",
        "input[value*='Show' i]",
    ]
    submitted = False
    for sel in submit_selectors:
        try:
            btn = await page.wait_for_selector(sel, timeout=3000)
            if btn:
                await btn.click()
                submitted = True
                break
        except PlaywrightTimeout:
            continue

    if not submitted:
        log("⚠️  Submit button not found")
        return False

    # 8. Check what loaded
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
        page_text = (await page.inner_text("body")).lower()

        # Wrong CAPTCHA
        if any(k in page_text for k in ["invalid captcha", "wrong captcha", "captcha incorrect"]):
            log("❌ Wrong CAPTCHA — retrying")
            return False

        # Results are live!
        if any(k in page_text for k in ["total marks", "marks obtained", "your result", "candidate name"]):
            timestamp = datetime.now().strftime("%H%M%S")
            shot_path  = os.path.join(SCREENSHOT_DIR, f"RESULT_tab{tab_id}_{timestamp}.png")
            await page.screenshot(path=shot_path, full_page=True)
            log(f"🎉 SUCCESS! Full-page screenshot → {shot_path}")
            return True

        log("⚠️  Unknown response — retrying")
        return False

    except PlaywrightTimeout:
        log("⚠️  Result page timed out")
        return False


# ──────────────────────────────────────────────────────────
#  TAB WORKER — one per tab, loops until stop_event is set
# ──────────────────────────────────────────────────────────

async def tab_worker(context, tab_id: int):
    page    = await context.new_page()
    attempt = 0

    while not stop_event.is_set():
        attempt += 1
        print(f"\n[Tab {tab_id:02d}] ─── Attempt #{attempt} ───")

        success = await run_attempt(page, tab_id, attempt)

        if success:
            stop_event.set()   # tell every other tab to stop
            break

        if stop_event.is_set():
            break

        # Wait RETRY_DELAY seconds, but wake up immediately if another tab succeeds
        print(f"[Tab {tab_id:02d}] ⏳ Retrying in {RETRY_DELAY}s...")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RETRY_DELAY)
        except asyncio.TimeoutError:
            pass  # normal — just means no success yet, keep looping

    await page.close()
    print(f"[Tab {tab_id:02d}] 🛑 Worker stopped.")


# ──────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────

async def main():
    print("╔════════════════════════════════════════════════════╗")
    print("║   CISCE Result Checker  •  10 Tabs  •  Auto Loop  ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"📁 Screenshots → {SCREENSHOT_DIR}")
    print(f"🔁 Looping forever until results go live...")
    print(f"🚀 Launching {NUM_TABS} parallel tabs...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

        # All 10 tabs run at the same time
        await asyncio.gather(*[
            tab_worker(context, tab_id)
            for tab_id in range(1, NUM_TABS + 1)
        ])

        await browser.close()

    print("\n✅ Done! Open your Desktop → CISCE_Results folder for the screenshot.")


if __name__ == "__main__":
    asyncio.run(main())