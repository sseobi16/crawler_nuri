from datetime import datetime, timedelta
import re

# 현재 날짜를 YYYYMMDD 문자열로 반환
def get_today_str():
    return datetime.now().strftime("%Y%m%d")

# 어제 날짜를 YYYYMMDD 문자열로 반환
def get_yesterday_str():
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

# 텍스트 전처리 함수
def clean_text(text):
    if not text:
        return ""
    
    # 날짜 포맷 정규화 
    date_pattern = re.compile(r'(\d{4}/\d{2}/\d{2})(\d{2}:\d{2})')
    text = date_pattern.sub(r'\1 \2', text)

    # 금액이 없는 경우, 0 원 처리
    if text == "원":
        return "0 원"
    
    # 유니코드 공백 및 일반 공백 처리
    text = str(text).replace("\xa0", " ")
    
    # 줄바꿈, 탭, 연속된 공백을 스페이스 하나로 통일하고 양쪽 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 공백 제거 및 줄바꿈 문자를 공백으로 치환
    return text.strip().replace("\n", " ").replace("\r", "")