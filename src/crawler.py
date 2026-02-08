import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError
from src.utils import clean_text

# 재시도 데코레이터
def retry_action(max_retries=3, delay=2):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (TimeoutError, Exception) as e:
                    last_exception = e
                    print(f"[WARN] Action failed ({func.__name__}), retrying {attempt + 1}/{max_retries}... Error: {e}")
                    await asyncio.sleep(delay)
            print(f"[ERROR] Action failed after {max_retries} attempts.")
            raise last_exception
        return wrapper
    return decorator

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
        self.browser = await p.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-extensions"
            ]
        )
        
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
            try:
                await self.browser.close()
                print("[INFO] Browser closed gracefully.")
            except Exception:
                pass

    # 팝업/모달 제거
    async def _clear_overlays(self):
 
        try:
            # 1. ESC 키로 닫기 시도
            await self.page.keyboard.press("Escape")
            
            # 2. '닫기' 버튼이 명확히 보이면 클릭
            close_btns = self.page.locator(".w2window_close, .w2popup_close, input[value='닫기'], button:has-text('닫기')")
            
            count = await close_btns.count()
            if count > 0:
                # 여러 개의 닫기 버튼 클릭
                for i in range(count):
                    btn = close_btns.nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await self.page.wait_for_timeout(200)

            #  해결되지 않은 팝업/모달 숨김 처리
            await self.page.evaluate("""
                () => {
                    const selectors = [
                        '.w2window',           // 팝업창
                        '.w2modal',            // 모달 배경
                        '.w2popup_window',     // 팝업 윈도우
                        '.w2modal_overlay',    // 투명 방해막
                        'div[role="dialog"]',  // 다이얼로그
                        '#___processbar2'      // 로딩바
                    ];
                    
                    const elements = document.querySelectorAll(selectors.join(','));
                    elements.forEach(el => {
                        el.style.display = 'none'; 
                        el.style.visibility = 'hidden';
                        el.style.zIndex = '-9999'; // 뒤로 보내버리기
                    });
                }
            """)
            
        except Exception:
            pass

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
    @retry_action(max_retries=3, delay=2)
    async def search_period(self, start_date, end_date):
            
            print(f"[INFO] Search initiated: {start_date} ~ {end_date}")

            try:
                await self.page.goto(self.base_url, wait_until="networkidle")
                
                try:
                    await self.page.wait_for_selector("#___processbar2", state="hidden", timeout=10000)
                except:
                    pass 

                await self._clear_overlays()

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

                await self.page.wait_for_timeout(1500)
                
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

    # 텍스트, 인풋 박스에 대한 데이터 추출
    async def _get_element_value(self, element):

        try:

            # 1. Select 태그 값 시도
            select_el = element.locator("select").first
            if await select_el.count() > 0:
                # 선택된 옵션의 텍스트 가져오기
                val = await select_el.evaluate("el => el.options[el.selectedIndex].text")
                if val and "선택" not in val: return clean_text(val)

            # 2. Input 태그 값 추출
            # 버튼 타입 제외
            input_el = element.locator("input:not([type='button']):not([type='submit']):not([type='hidden'])").first
            if await input_el.count() > 0:
                val = await input_el.get_attribute("value")
                if val: return clean_text(val)

            # 3. 일반 텍스트 추출
            text = clean_text(await element.inner_text())
            if text:
                return text
                
        except Exception:
            pass
        return ""

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
                
                loop_len = min(len(row_ths), len(row_tds))
                for j in range(loop_len):
                    key = clean_text(await row_ths[j].inner_text())
                    val = await self._get_element_value(row_tds[j])
                    if key:
                        data[key] = val
        except Exception as e:
            print(f"[Error] Table parsing error: {e}")
        return data
    
    # 그리드 내 정보 파싱
    async def _parse_grid(self, container_locator):
        data_list = []
        try:
            # 헤더 텍스트 추출하기
            headers = []
            header_row = container_locator.locator("thead tr").first
            
            if await header_row.count() > 0:
                ths = await header_row.locator("th").all()
                for th in ths:
                    # 헤더 텍스트 정제
                    text = clean_text(await th.inner_text())
                    headers.append(text)
            
            # 헤더를 못 찾았으면 빈 리스트 반환 (또는 기존 로직 fallback 가능하나 여기선 패스)
            if not headers:
                return data_list

            # 본문 데이터 추출
            tbody = container_locator.locator("tbody")
            if await tbody.count() == 0:
                return data_list
                
            rows = tbody.locator("tr")
            row_count = await rows.count()
            
            for i in range(row_count):
                row = rows.nth(i)
                # 데이터가 없는 그리드 건너뜀
                if "데이터가 없음" in await row.inner_text():
                    continue
                    
                row_data = {}
                cells = await row.locator("td").all()
                
                # 헤더 개수와 셀 개수 중 작은 쪽에 맞춰 루프
                loop_len = min(len(headers), len(cells))
                
                has_data = False
                for j in range(loop_len):
                    key = headers[j]
                    
                    # 의미 없는 컬럼(순서, 체크박스) 제외
                    if not key or key in ["No", "NO", "선택", "미리보기"]:
                        continue
                        
                    # value 값 추출
                    val = await self._get_element_value(cells[j])
                    
                    row_data[key] = val
                    if val: has_data = True
                
                if has_data:
                    data_list.append(row_data)
                    
        except Exception:
            pass
        return data_list
    
    # 동적 섹션 정보 추출 (실제 데이터 수집 로직)
    async def extract_detail_info(self):
        detail_data = {
            "sections": {},
            "files": []
        }

        #  입찰공고일반 탭으로 고정
        await self._ensure_general_tab_active()

        # 스크롤 다운
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(1000) # 렌더링 대기
        except Exception as e:
            print(f"[Error] Scroll down failed: {e}")

        # 각 세션별 데이터 추출
        try:
            # 존재하는 제목(.df_title) 추출
            titles = await self.page.locator(".df_tit").all()
            
            for title_el in titles:
                if not await title_el.is_visible():
                    continue
                    
                section_name = clean_text(await title_el.inner_text())
                
                # 빈 제목 제외
                if not section_name:
                    continue

                # 제목을 감싸는 박스(.dfbox) 찾기
                header_box = title_el.locator("xpath=ancestor::div[contains(@class, 'dfbox')]")
                
                # 컨텐츠 박스 찾기
                content_box = header_box.locator("xpath=following-sibling::div[1]")
                
                if await content_box.count() == 0 or not await content_box.is_visible():
                    continue 

                # 그리드 또는 테이블 존재 여부 확인
                has_grid = await content_box.locator(".w2grid").count() > 0
                has_table = await content_box.locator("table.w2tb").count() > 0

                # 단순 텍스트 건너뛰기
                if not (has_grid or has_table):
                    continue

                # 내용 텍스트 검사 
                content_text = await content_box.inner_text()
                
                # 달력(Calendar) 차단
                if ("Sunday" in content_text and "Monday" in content_text) or \
                   ("일요일" in content_text and "월요일" in content_text):
                    continue
                
                # 검색 필터 차단
                if "검색" in content_text and "초기화" in content_text:
                    continue

                # 데이터 추출
                if has_grid:
                    grid_el = content_box.locator("div.w2grid").first
                    grid_data = await self._parse_grid(grid_el)
                    
                    if "파일" in section_name:
                        detail_data["files"] = grid_data
                    else:
                        detail_data["sections"][section_name] = grid_data

                elif has_table:
                    table_el = content_box.locator("table.w2tb").first
                    table_data = await self._parse_table(table_el)
                    detail_data["sections"][section_name] = table_data

        except Exception as e:
            print(f"[WARN] Dynamic section scan failed: {e}")

        return detail_data

    # 입찰 공고 목록 상세 페이지 조회
    @retry_action(max_retries=3, delay=2)
    async def crawl_period_pages(self, save_callback, stop_on_duplicate=False, cutoff_date=None):

        current_page = 1

        cutoff_dt = None
        if cutoff_date:
            try:
                cutoff_dt = datetime.strptime(cutoff_date, "%Y%m%d")
            except:
                pass

        consecutive_old_count = 0
        MAX_OLD_COUNT = 3
        
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

                    # 컷오프 날짜 검사
                    if cutoff_dt:
                        row_text = await row.inner_text()
                        date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", row_text)
                        
                        if date_match:
                            row_date_str = f"{date_match.group(1)}{date_match.group(2)}{date_match.group(3)}"
                            row_dt = datetime.strptime(row_date_str, "%Y%m%d")
                            
                            # 공고 게시 일시가 설정한 시작일보다 과거인 경우
                            if row_dt < cutoff_dt:
                                consecutive_old_count += 1
                                print(f"[INFO] 과거 데이터 발견 ({row_date_str})")
                                
                                # 연속 3회 이상 과거 날짜면 종료 신호
                                if consecutive_old_count >= MAX_OLD_COUNT:
                                    print(f"[INFO] 날짜 범위 초과 확인. 수집을 종료합니다.")
                                    stop_signal = True
                                    break
                                
                                continue 
                            else:
                                # 최신 날짜가 나오면 카운트 리셋
                                consecutive_old_count = 0


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
                await self._clear_overlays()

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