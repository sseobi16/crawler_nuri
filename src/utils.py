from datetime import datetime, timedelta

def get_today_str():
    # 현재 날짜를 YYYYMMDD 문자열로 반환
    return datetime.now().strftime("%Y%m%d")

def get_yesterday_str():
    # 어제 날짜를 YYYYMMDD 문자열로 반환
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

def clean_text(text):
    # 텍스트 전처리 함수
    if not text:
        return ""
    
    # 공백 제거 및 줄바꿈 문자를 공백으로 치환
    return text.strip().replace("\n", " ").replace("\r", "")