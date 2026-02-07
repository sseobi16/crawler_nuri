# Playwright 공식 이미지 
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# 비대화형 설치 모드 설정
ARG DEBIAN_FRONTEND=noninteractive

# 서버 속도 최적화를 위한 국내 미러 사용
RUN sed -i 's/archive.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list

# 파이썬 로그 즉시 출력 (버퍼링 끔)
ENV PYTHONUNBUFFERED=1

# 한글 폰트 및 타임존 설정을 위한 패키지 설치
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 한국 표준시 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 작업 디렉토리 생성
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 소스 코드 복사
COPY . .

# 실행 명령어
CMD ["python", "main.py"]