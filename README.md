# 누리장터 입찰공고 수집 시스템
이 프로젝트는 Playwright와 Docker를 활용하여, 대한민국 조달청 누리장터의 입찰 공고를 동적으로 수집 및 모니터링하는 자동화 시스템입니다.

## 사전 요구 사항
이 프로젝트를 실행하기 위해 아래 소프트웨어가 설치되어 있어야 합니다.

1. Git 설치: 소스 코드를 다운로드하기 위해 필요합니다.
2. Docker Desktop 설치: 가상 실행 환경을 구성하기 위해 필요합니다.
3. Docker Desktop 프로그램을 실행해주세요.

4. 터미널을 열고 아래 명령어를 순서대로 입력해주세요.
```bash
# 1. 프로젝트 다운로드
git clone https://github.com/sseobi16/crawler_nuri.git

# 2. 프로젝트 폴더로 이동
cd nuri_crawler

# 3. 데이터 저장 폴더 생성 (없을 경우 자동 생성됨)
mkdir data
```

## 실행 방법 (Docker Compose)

### 1. 과거 데이터 수집 (History Mode)
원하는 날짜 구간을 지정하여 실행합니다. (YYYYMMDD)

```bash
# 2026/01/01 - 2026/01/31 데이터 수집

# Mac / Linux
HISTORY_START=20260101 HISTORY_END=20260131 docker-compose up history-loader

# Windows (PowerShell)
$env:HISTORY_START="20260101"; $env:HISTORY_END="20260131"; docker-compose up history-loader
```

### 2. 실시간 감지
원하는 간격(초)마다 데이터를 수집합니다.

```bash
# 10분(600초) 간격 실행

# Mac / Linux
INTERVAL_SEC=600 docker-compose up monitor-interval

# Windows (PowerShell)
$env:INTERVAL_SEC="600"; docker-compose up monitor-interval
```

### 3. 주기적 스케줄링

```bash
# 매일 오전 9시 실행

# Mac / Linux
CRON_HOUR=9 docker-compose up monitor-cron

# Windows (PowerShell)
$env:CRON_HOUR="9"; docker-compose up monitor-cron
```

## 결과물 확인 (Output)
수집된 데이터는 프로젝트 폴더 내 data/ 디렉토리에 저장됩니다.

* output.csv: 수집된 입찰 공고 상세 정보 (Excel로 열람 가능)

* visited_ids.txt: 중복 수집 방지를 위한 ID 기록