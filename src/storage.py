import os
import sys
import json
import signal
import asyncio
import atexit
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class DataStorage:
    def __init__(self, save_dir="data"):
        self.save_dir = save_dir
        
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        # 중복 ID 저장 파일
        self.visited_file = os.path.join(self.save_dir, "visited_ids.txt")
        # .jsonl 확장자 사용
        self.output_file = os.path.join(self.save_dir, "nuri_data.jsonl")
        # 대시보드 출력용 엑셀파일
        self.output_excel = os.path.join(self.save_dir, "nuri_data.xlsx")
        
        self.visited_ids = self._load_visited_ids()

        self.excel_buffer = [] 
        self.BUFFER_SIZE = 10  # 데이터 10개마다 엑셀 저장
        self.executor = ThreadPoolExecutor(max_workers=1) 

        # 프로그램 종료 시, 버퍼에 남은 데이터 저장
        atexit.register(self._cleanup)
        # Docker 종료 신호 처리
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        print("[SYSTEM] Docker 종료 신호 감지. 데이터 저장 중...")
        self._cleanup()
        print("[SYSTEM] 종료 완료.")
        sys.exit(0)

    def _cleanup(self):
        if not self.excel_buffer:
            return

        if self.excel_buffer:
            print(f"[INFO] 프로그램 종료 전 버퍼에 남은 {len(self.excel_buffer)}건 엑셀 저장 중...")
            self._flush_to_excel(self.excel_buffer, is_async=False)
            self.excel_buffer = []

    def _load_visited_ids(self):
        ids = set()
        if os.path.exists(self.visited_file):
            try:
                with open(self.visited_file, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_id = line.strip()
                        if clean_id:
                            ids.add(clean_id)
            except Exception as e:
                print(f"[ERROR] Loading visited IDs failed: {e}")
        return ids

    def is_new(self, notice_id):
        return notice_id not in self.visited_ids

    def save_data(self, data_dict, notice_id):
        if not data_dict:
            return

        try:
            # ID 목록 업데이트
            if notice_id not in self.visited_ids:
                self.visited_ids.add(notice_id)
                with open(self.visited_file, "a", encoding="utf-8") as f:
                    f.write(f"{notice_id}\n")

            # 데이터 저장 (JSONL 방식 - 한 줄에 JSON 하나씩 추가)
            json_str = json.dumps(data_dict, ensure_ascii=False)
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json_str + "\n")
            
            # 2. [버퍼링] 엑셀용 버퍼에 담기
            self.excel_buffer.append(data_dict)
            print(f"[INFO] Saved: {notice_id}")
            
            if len(self.excel_buffer) >= self.BUFFER_SIZE:
                data_to_save = self.excel_buffer[:]
                self.excel_buffer = []
                
                # 별도 스레드 실행을 통해 크롤러 영향 최소화
                asyncio.get_event_loop().run_in_executor(
                    self.executor, 
                    self._flush_to_excel, 
                    data_to_save
                )

        except Exception as e:
            print(f"[ERROR] Save failed ({notice_id}): {e}")

    def _flush_to_excel(self, data_list, is_async=True):
        try:
            # 데이터 변환 (Jsonl -> 엑셀 Row)
            flattened_rows = []
            for item in data_list:
                row = {
                    "수집ID": item.get("id"),
                    "공고명": item.get("title"),
                    "수집일시": item.get("crawled_at")
                }
                
                sections = item.get("sections", {})
                for section_name, section_data in sections.items():
                    
                    # 테이블 데이터 - 키를 컬럼으로 사용
                    if isinstance(section_data, dict):
                        for key, value in section_data.items():
                            # 컬럼명 충돌 방지 (섹션명_키)
                            # 공고일반은 자주 쓰니까 접두어 없이, 나머지는 접두어 붙임
                            col_name = key if section_name == "공고일반" else f"{section_name}_{key}"
                            if col_name not in row:
                                row[col_name] = value

                    # 그리드 데이터 - 요약 정보로 변환
                    elif isinstance(section_data, list):
                        summary_list = []
                        for idx, grid_row in enumerate(section_data):
                            row_str = " | ".join([str(v) for v in grid_row.values()])
                            summary_list.append(f"[{idx+1}] {row_str}")                        
                        row[section_name] = "\n".join(summary_list)
                
                # 첨부파일 정보 요약
                files = item.get("files", [])
                row["첨부파일_개수"] = len(files)
                
                file_names = []
                for f in files:
                    name = f.get("파일명") or f.get("orgnlAtchFileNm")
                    file_names.append(name)
                    
                row["첨부파일_목록"] = "\n".join(file_names)

                flattened_rows.append(row)

            new_df = pd.DataFrame(flattened_rows)

            # 기존 엑셀 파일이 있으면 합치기
            if os.path.exists(self.output_excel):
                existing_df = pd.read_excel(self.output_excel)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                final_df = new_df
            if not is_async:
                print("종료 전 엑셀 저장 실행")

            # 최종 저장
            final_df.to_excel(self.output_excel, index=False)
            print(f"[Excel] {len(data_list)}건 백그라운드 저장 완료 (Total: {len(final_df)}행)")

        except PermissionError:
            print(f"[WARN] 엑셀 파일이 열려있어 저장 실패! 닫고 다시 시도하세요: {self.output_excel}")
        except Exception as e:
            print(f"[WARN] 엑셀 저장 중 오류: {e}")

    def get_stats(self):
        return len(self.visited_ids)