import os
import json

class DataStorage:
    def __init__(self, save_dir="data"):
        self.save_dir = save_dir
        
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        self.visited_file = os.path.join(self.save_dir, "visited_ids.txt")
        # .jsonl 확장자 사용
        self.output_file = os.path.join(self.save_dir, "nuri_data.jsonl")
        
        self.visited_ids = self._load_visited_ids()

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
            
            print(f"[INFO] Saved: {notice_id}")

        except Exception as e:
            print(f"[ERROR] Save failed ({notice_id}): {e}")

    def get_stats(self):
        return len(self.visited_ids)