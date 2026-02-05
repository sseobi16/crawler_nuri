import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError
from src.utils import clean_text

class NuriCrawler:
    def __init__(self, headless=True):
        self.base_url = "https://nuri.g2b.go.kr/"
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None

    async def start_browser(self):
        print("[INFO] Starting browser...")
        p = await async_playwright().start()
        # 디버깅 시 headless=False 사용
        self.browser = await p.chromium.launch(headless=self.headless)
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()

        try:
            await self.page.add_locator_handler(
                self.page.locator("div.popup input[value='닫기']"),
                lambda locator: locator.click()
            )
        except Exception:
            pass

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            print("[INFO] Browser closed.")

    async def _input_date_field(self, selector, date_str):
        try:
            await self.page.click(selector)
            await self.page.keyboard.press("Control+A") 
            await self.page.keyboard.press("Backspace")
            await self.page.keyboard.type(date_str, delay=100)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(500)
        except Exception as e:
            print(f"[ERROR] Date input failed ({selector}): {e}")

