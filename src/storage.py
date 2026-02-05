import os
import json
import pandas as pd

class DataStorage:
    def __init__(self, save_dir="data"):

        # 저장 디렉토리 설정
        self.save_dir = save_dir
        
        # 데이터 디렉토리가 없으면 생성
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        # 파일 경로 설정
        self.visited_file = os.path.join(self.save_dir, "visited_ids.txt")
        self.output_file = os.path.join(self.save_dir, "output.csv")
        
        # 메모리에 방문 ID 로드
        self.visited_ids = self._load_visited_ids()

    def _load_visited_ids(self):
    
        # visited_ids.txt 파일에서 기존 ID들을 읽어와 Set으로 반환    
        ids = set()
        if os.path.exists(self.visited_file):
            try:
                with open(self.visited_file, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_id = line.strip()
                        if clean_id:
                            ids.add(clean_id)
            except Exception as e:
                print(f"[ERROR] Failed to load visited IDs: {e}")
        return ids

    def is_new(self, notice_id):
        # 새로운 공고 ID인지 확인
        return notice_id not in self.visited_ids

    def save_data(self, data_dict, notice_id):
        # 데이터 저장 및 방문 기록 업데이트
        
        if not data_dict:
            return

        try:
            # 방문 기록 업데이트
            if notice_id not in self.visited_ids:
                self.visited_ids.add(notice_id)
                with open(self.visited_file, "a", encoding="utf-8") as f:
                    f.write(f"{notice_id}\n")

            # CSV 저장을 위해 리스트나 딕셔너리 형태의 필드를 JSON 문자열로 변환
            processed_data = data_dict.copy()
          
            # CSV 저장 
            df = pd.DataFrame([processed_data])
            
            file_exists = os.path.isfile(self.output_file)
            
            df.to_csv(
                self.output_file, 
                mode='a', 
                header=not file_exists,
                index=False, 
                encoding='utf-8-sig' # 엑셀 호환성을 위한 BOM 추가
            )
            
            print(f"[INFO] Saved data: {notice_id}")

        except Exception as e:
            print(f"[ERROR] Failed to save data ({notice_id}): {e}")

    def get_stats(self):
        # 현재 수집된 데이터 개수 반환
        return len(self.visited_ids)