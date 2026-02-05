import json
import os

def view_latest_data(file_path="data/nuri_data.jsonl", num_lines=3):
    
    if not os.path.exists(file_path):
        print(f"파일이 없습니다: {file_path}")
        return

    print(f"[{file_path}]의 최신 데이터 {num_lines}건을 조회합니다...\n")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # 파일의 모든 라인을 읽음
            lines = f.readlines()
            
            # 데이터가 없으면 종료
            if not lines:
                print("데이터가 비어있습니다.")
                return

            # 뒤에서부터 n개 가져오기
            latest_lines = lines[-num_lines:]
            
            for i, line in enumerate(reversed(latest_lines)):
                if not line.strip(): continue
                
                # JSON 파싱 및 출력
                data = json.loads(line)
                pretty_json = json.dumps(data, ensure_ascii=False, indent=4)
                
                print(f"[No. {len(lines) - i}] ID: {data.get('id', 'Unknown')}")
                print(pretty_json)
                print("="*60)
                
    except Exception as e:
        print(f"읽기 중 오류 발생: {e}")

if __name__ == "__main__":
    # 실행하면 data/nuri_data.jsonl 파일의 최신 3개를 보여줌
    view_latest_data()