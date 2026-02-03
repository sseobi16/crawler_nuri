# Playwright 공식 이미지 
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# 파이썬 로그 즉시 출력 (버퍼링 끔)
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 생성
WORKDIR /app

# 1. 의존성 파일 복사
COPY requirements.txt .

# 2.필요 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 3. 나머지 소스 코드 복사
COPY . .

# 4. 실행 명령어
ENTRYPOINT ["python", "main.py"]