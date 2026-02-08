# 누리장터 입찰공고 수집 시스템
이 프로젝트는 Playwright와 Docker를 활용하여, 대한민국 조달청 누리장터의 입찰 공고를 동적으로 수집 및 모니터링하는 자동화 시스템입니다.
수집된 데이터는 JSONL 및 Excel 형식으로 저장되며, Web DashBoard를 통해 실시간으로 현황을 파악할 수 있습니다.

## 개발 환경 및 의존성
Docker 환경에서의 실행을 최우선으로 지원합니다. 로컬 실행 시 아래의 버전 및 라이브러리가 필요합니다

* Python(v3.10): 도커 playwright 이미지와 동일 버전
* Playwright(v1.58.0): 동적 웹 페이지 크롤링 및 브라우저 제어
* Pandas(v2.2.0) & OpenPyXL(v3.1.5): 데이터 처리 및 엑셀 파일 변환
* APScheduler(v3.10.4): 주기적 작업(Interval/Cron) 스케줄링
* Streamlit(v1.54.0): 실시간 데이터 모니터링 대시보드 구현

## 사전 요구 사항
이 프로젝트를 실행하기 위해 아래 소프트웨어가 설치되어 있어야 합니다.

1. Git 설치: 소스 코드를 다운로드하기 위해 필요합니다.
2. Docker Desktop 설치 및 실행: 가상 실행 환경을 구성하기 위해 필요합니다.
3. 터미널을 열고 아래 명령어를 순서대로 입력해주세요.
```bash
# 1. 프로젝트 다운로드
git clone https://github.com/sseobi16/crawler_nuri.git

# 2. 프로젝트 폴더로 이동
cd crawler_nuri

# 3. 데이터 저장 폴더 생성
mkdir data
```

## 실행 방법 (Docker Compose)

### 1. 실시간 대시보드
수집된 현황을 웹페이지에서 시각화하여 모니터링합니다.
대시보드를 먼저 실행하여 Docker 환경 빌드를 우선 진행합니다.

```bash
# 대시보드 실행
docker-compose up -d --build dashboard

# 대시보드 중지
docker-compose stop dashboard
```
* 접속 주소: http://localhost:8501
* 검색 및 필터링, 요약 통계 확인 가능

### 2. 과거 데이터 수집 (History Mode)
원하는 날짜 구간을 지정하여 데이터를 수집합니다.

```bash
# 2026/02/01 - 2026/02/07 데이터 수집

# Mac / Linux
HISTORY_START=20260201 HISTORY_END=20260207 docker-compose up history-loader

# Windows (PowerShell)
$env:HISTORY_START="20260201"; $env:HISTORY_END="20260207"; docker-compose up history-loader
```

### 3-1. 실시간 감지
원하는 간격마다 데이터를 수집합니다.

```bash
# 10분(600초) 간격 실행

# Mac / Linux
INTERVAL_SEC=600 docker-compose up monitor-interval

# Windows (PowerShell)
$env:INTERVAL_SEC="600"; docker-compose up monitor-interval

# 크롤링 종료
docker-compose stop monitor-interval

# 크롤링 재시작
docker-compose start monitor-interval
```

### 3-2. 주기적 스케줄링
매일 지정된 시간(0~23시)에 데이터를 수집합니다.

```bash
# 매일 오전 9시 실행

# Mac / Linux
CRON_HOUR=9 docker-compose up monitor-cron

# Windows (PowerShell)
$env:CRON_HOUR="9"; docker-compose up monitor-cron

# 크롤링 종료
docker-compose stop monitor-cron

# 크롤링 재시작
docker-compose start monitor-cron
```

## 결과물 (Output)
수집된 데이터는 프로젝트 폴더 내 data/ 디렉토리에 저장됩니다.
* **nuri_data.jsonl**: 수집된 입찰 공고 상세 정보가 저장되는 파일 (JSON Lines 포맷)
* **nuri_data.xlsx**: 사용자가 보기 편하게 정리한 엑셀 파일
* **visited_ids.txt**: 중복 수집 방지를 위해 수집 완료된 공고 번호 목록

## 설계 및 주요 구현

### 1. 개발 진행 과정
* **Git Branch Strategy**: 기능 단위로 브랜치를 생성하여 개발하고, 테스트가 완료된 코드를 메인 브랜치에 병합(Merge)하는 전략을 사용했습니다.
* **Testing**: 크롤링 로직 수정 시, 별도의 검증 스크립트(check_data.py)를 통해 수집된 데이터에 대한 테스트를 진행하였습니다.
* **Evidence-based PR**: Pull Request에서 단순한 코드 변경 사항뿐만 아니라, 실제 동작을 증명하는 로그와 스크린샷을 첨부하여 리뷰 효율성을 높였습니다.

### 2. 주요 가정 사항
* **데이터 수집 범위**: interval/cron 모드에서는 수집 실행일의 전날부터 오늘까지를 검색 범위로 설정하였습니다.
* **공고 식별자**: 누리장터의 입찰공고번호(ID)는 유일하며, 동일한 ID를 가진 공고는 내용이 동일하다고 가정하였습니다.


### 3. 안정적인 동적 크롤링
응답 속도가 불규칙하고, 예상치 못한 팝업과 같은 문제를 해결하기 위해 다음과 같은 전략을 적용했습니다.
* **Input Validation**: 잘못 입력된 파라미터로 인한 런타임 에러나 서버 부하를 방지하기 위해 유효성 검사를 수행하였습니다. 
    * 날짜 형식 및 시작일과 종료일 순서 검증
    * Interval 모드 실행 시, 과도한 요청으로 인한 수집 차단을 방지하기 위해 최소 주기 설정
    * 유효성 검사 실패 시, 에러 메시지와 함께 프로세스 종료
* **Retry Decorator Pattern**: 네트워크 불안정이나 렌더링 지연에 대비하여, 주요 동작 실패 시 자동으로 재시도하는 데코레이터를 구현하였습니다.
* **Waiting**: time.sleep()과 같은 고정 대기 대신, Playwright의 Auto-waiting 기능을 활용하여 DOM 요소가 렌더링될 때까지 대기합니다.
* **Overlay Defense**: 화면을 가리는 로딩바와 불필요한 팝업을 감지하고 제거하는 로직(_clear_overlays)을 적용했습니다.

### 4. 데이터 처리 방식
수집 도중 발생할 수 있는 예외(프로세스 강제 종료 등)로부터 데이터를 보호하고 사용자의 편의를 위해 이중 저장 구조를 채택했습니다.
* **Master (Jsonl)**: 쓰기 속도가 빠르고, 파일 손상 가능성이 낮은 JSONL 포맷을 사용합니다.
* **View (Excel)**: 백그라운드 스레드에서 비동기로 처리하여 수집 속도에 영향을 주지 않습니다.
* **DashBoard(Streamlit)**: 사용자 편의를 위해 실시간 데이터 수집 현황을 보여줍니다. 
* **Graceful Shutdown(atexit)**: 컨테이너 종료 또는 인터럽트 발생 시 메모리 버퍼에 존재하는 데이터를 저장하고 안전하게 종료합니다.

### 5. 운영 및 배포 전략
실제 상용 서비스를 가정하여 구현하였습니다.
* Docker를 활용하여 로컬 개발 환경과 배포 환경을 일치시켜, 안정적으로 동일한 결과를 가져올 수 있도록 설계하였습니다.
* 시스템이 재시작되더라도 데이터가 중복으로 수집되지 않도록 visited_ids.txt에 수집된 공고 ID를 저장하여 일관성을 유지합니다.
* 과거의 데이터를 수집할 수 있는 History 모드와 최신 데이터를 지속적으로 수집하는 Interval/Cron 모드로 구성하여 운영 목적에 따른 확장이 가능합니다.

### 6. 한계점 및 향후 개선 사항
1. 실시간 알림 서비스 연동
* 현재: 수집 현황을 파악하기 위해 직접 대시보드에 접속하는 수동 모니터링 방식
* 개선: Webhook을 사용하여, 특정 키워드가 포함된 공고가 수집되거나 시스템 에러가 발생했을 때, 알림을 보내는 모니터링 시스템 구축

2. 수집 데이터 저장소 고도화
* 현재: Jsonl, Excel 사용하여 데이터를 저장(파일 락으로 인한 동시 쓰기 작업 불가)
* 개선: DBMS를 도입하여 데이터 무결성을 보장하고, 복잡한 쿼리 및 통계 분석 기능 강화
