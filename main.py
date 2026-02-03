import argparse
import sys
import os
from datetime import datetime

# 환경 검증
try:
    import pandas as pd
    from playwright.async_api import async_playwright
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    print("[System] 필수 라이브러리 로드 성공")
except ImportError as e:
    print(f"\n[Error] 라이브러리 로드 실패: {e}")
    sys.exit(1)

def parse_arguments():

    parser = argparse.ArgumentParser(description="누리장터 입찰공고 수집 시스템")
    
    # 실행 모드 선택 (history / interval / cron)
    parser.add_argument(
        "--mode", 
        choices=["history", "interval", "cron"], 
        required=True, 
        help="실행 모드 선택 (history: 과거수집 / interval: 주기적 실행 / cron: 정기실행)"
    )
    
    # History 모드용 날짜 (YYYYMMDD)
    parser.add_argument("--start", type=str, help="수집 시작일 (YYYYMMDD)")
    parser.add_argument("--end", type=str, help="수집 종료일 (YYYYMMDD)")
    
    # Interval 모드용 간격 (초 단위, 기본값 600초=10분)
    parser.add_argument("--interval", type=int, default=600, help="실행 간격 (초)")
    
    # Cron 모드용 시간 (0~23시, 기본값 9시)
    parser.add_argument("--hour", type=int, default=9, help="매일 실행할 시간 (0-23)")

    return parser.parse_args()

def main():
    
    args = parse_arguments()
    
    print(f"누리장터 크롤러 시스템 가동")
    print(f"시스템 시간 (KST): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} + \n")

    # 모드별 설정 값 검증 및 로깅
    if args.mode == "history":
        print("과거 데이터 수집 (History Mode)")
        
        # 유효성 검사: 날짜 인자 필수
        if not args.start or not args.end:
            print("[Error] History 모드는 --start와 --end 인자가 필수입니다.")
            print("예시: python main.py --mode history --start 20260101 --end 20260131")
            sys.exit(1)
            
        print(f"- 수집 구간: {args.start} ~ {args.end}")
        print("- 동작 방식: 지정된 기간의 모든 공고를 수집합니다. + \n")

    elif args.mode == "interval":
        print("실시간 간격 감시 (Interval Mode)")
        print(f"- 실행 주기: {args.interval}초 ({args.interval/60:.1f}분)")
        print("- 동작 방식: 주기적으로 접속하여 신규 공고만 수집하고 종료합니다. + \n")

    elif args.mode == "cron":
        print("정기 스케줄 실행 (Cron Mode)")
        print(f"- 실행 시간: 매일 오전 {args.hour}시")
        print("- 동작 방식: 하루에 한 번, 정해진 시간에 수집을 수행합니다. + \n")

    print("환경 설정 및 인자 검증 완료.")

if __name__ == "__main__":
    main()