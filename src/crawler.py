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

    # 입찰 공고 목록 검색 
    async def search_period(self, start_date, end_date):
            
            print(f"[INFO] Search initiated: {start_date} ~ {end_date}")

            try:
                await self.page.goto(self.base_url, wait_until="networkidle")
                
                try:
                    await self.page.wait_for_selector("#___processbar2", state="hidden", timeout=10000)
                except:
                    pass 

                print("[DEBUG] Hovering main menu...")
                main_menu = self.page.locator("text=입찰공고").locator("visible=true").first
                await main_menu.hover()
                
                print("[DEBUG] Clicking sub menu...")
                sub_menu = self.page.locator("text=입찰공고목록").locator("visible=true").first
                await sub_menu.click()
                
                await self.page.wait_for_selector("input[title*='시작 날짜']", timeout=10000)

                await self._input_date_field("input[title*='시작 날짜']", start_date)
                await self._input_date_field("input[title*='종료 날짜']", end_date)

                print("[DEBUG] Clicking search button...")
                await self.page.click("input[value='검색']")
                
                try:
                    await self.page.wait_for_selector("#___processbar2", state="hidden", timeout=5000)
                except:
                    pass
                
                await self.page.wait_for_selector("td[col_id='bidPbancNum']", timeout=10000)
                print("[INFO] Search results loaded.")
                return True

            except Exception as e:
                print(f"[ERROR] Search failed: {e}")
                return False
    
    # 입찰 공고 일반 탭으로 고정
    async def _ensure_general_tab_active(self):
        try:
            tab_link = self.page.locator("a[title='입찰공고일반']")
            if await tab_link.count() > 0:
                parent_li = tab_link.locator("xpath=../..") 
                class_attr = await parent_li.get_attribute("class")
                
                if "w2tabcontrol_selected" not in class_attr:
                    # print("[INFO] Switching to '입찰공고일반' tab...")
                    await tab_link.click()
                    await self.page.wait_for_selector("#mf_wfm_container_tabControl1_contents_content1_body", state="visible", timeout=5000)
                    await self.page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] Tab switching error: {e}")

    # 테이블 파싱 (th, td 쌍 매핑)
    async def _parse_table(self, container_locator):
        data = {}
        try:
            rows = container_locator.locator("tr")
            count = await rows.count()
            
            for i in range(count):
                row = rows.nth(i)
                
                row_ths = await row.locator("th").all()
                row_tds = await row.locator("td").all()
                
                # 보통 th 다음에 td가 오는 구조이므로 순서대로 짝을 맞춤
                loop_len = min(len(row_ths), len(row_tds))
                for j in range(loop_len):
                    key = clean_text(await row_ths[j].inner_text())
                    val = clean_text(await row_tds[j].inner_text())
                    if key:
                        data[key] = val
        except Exception as e:
            print(f"[WARN] Table parsing error: {e}")
        return data
    
    # 그리드 내 정보 파싱
    async def _parse_grid(self, container_locator):
        data_list = []
        try:
            tbody = container_locator.locator("tbody")
            if await tbody.count() == 0:
                return data_list
                
            rows = tbody.locator("tr")
            row_count = await rows.count()
            
            for i in range(row_count):
                row = rows.nth(i)
                if "데이터가 없음" in await row.inner_text():
                    continue
                    
                row_data = {}
                cells = await row.locator("td").all()
                
                has_data = False
                for cell in cells:
                    col_id = await cell.get_attribute("col_id")
                    # 체크박스나 버튼 컬럼은 제외
                    if col_id and "chk" not in col_id.lower() and "btn" not in col_id.lower():
                        val = clean_text(await cell.inner_text())
                        row_data[col_id] = val
                        if val: has_data = True
                
                if has_data:
                    data_list.append(row_data)
        except Exception:
            pass
        return data_list
    
    

    # 입찰 공고 목록 상세 페이지 조회
    async def crawl_period_pages(self, save_callback, stop_on_duplicate=False):

        current_page = 1
        
        while True:
            print(f"[INFO] Processing list page {current_page}...")
            
            try:
                await self.page.wait_for_selector("tr.grid_body_row", timeout=5000)
            except:
                print("[INFO] No data rows found.")
                break

            rows = self.page.locator("tr.grid_body_row")
            count = await rows.count()
            
            if count == 0:
                break

            stop_signal = False

            for i in range(count):
                try:
                    row = self.page.locator("tr.grid_body_row").nth(i)
                    id_cell = row.locator("td[col_id='bidPbancNum']")
                    title_link = row.locator("td[col_id='bidPbancNm'] a")
                    
                    if await id_cell.count() == 0 or await title_link.count() == 0:
                        continue

                    notice_id = clean_text(await id_cell.inner_text())
                    title = clean_text(await title_link.inner_text())

                    should_process = save_callback(None, notice_id, check_only=True)
                    
                    if not should_process:
                        # Interval / Cron 모드에서 중복 발견 시 종료
                        if stop_on_duplicate:
                            print(f"[INFO] Found existing data ({notice_id}). Stopping crawler.")
                            stop_signal = True
                            break
                        # History 모드에서 중복 발견 시 스킵
                        else:
                            print(f"[DEBUG] Skipping duplicate: {notice_id}")
                            continue

                    await title_link.click()
                    await self.page.wait_for_selector("td[data-title='입찰공고번호']", timeout=15000)

                    extracted_data = await self.extract_detail_info()
                    extracted_data["id"] = notice_id
                    extracted_data["title"] = title
                    extracted_data["crawled_at"] = datetime.now().isoformat()

                    save_callback(extracted_data, notice_id, check_only=False)

                    await self.page.click("input[value='목록']")
                    await self.page.wait_for_selector("td[col_id='bidPbancNum']", timeout=10000)

                except Exception as e:
                    print(f"[ERROR] Failed to process row {i}: {e}")
                    try:
                        await self.page.go_back()
                        await self.page.wait_for_selector("td[col_id='bidPbancNum']")
                    except:
                        pass

            # 동일 페이지 존재 시 종료
            if stop_signal:
                break

            next_page = current_page + 1
            try:
                next_num_btn = self.page.locator(f"a.w2pageList_control_label[index='{next_page}']")
                next_group_btn = self.page.locator("#mf_wfm_container_pagelist_next_btn")

                if await next_num_btn.is_visible():
                    print(f"[DEBUG] Clicking page {next_page}")
                    await next_num_btn.click()
                elif await next_group_btn.is_visible():
                    print("[DEBUG] Clicking next group button")
                    await next_group_btn.click()
                else:
                    print("[INFO] Reached last page.")
                    break
                
                await self.page.wait_for_timeout(1000)
                try:
                    await self.page.wait_for_selector("#___processbar2", state="hidden", timeout=5000)
                except:
                    pass
                current_page += 1

            except Exception as e:
                print(f"[ERROR] Pagination error: {e}")
                break