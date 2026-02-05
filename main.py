import argparse
import sys
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.storage import DataStorage
from src.crawler import NuriCrawler
from src.utils import get_today_str, get_yesterday_str

async def run_task(mode, args, storage):

    # 디버깅 시 False
    crawler = NuriCrawler(headless=True) 

    try:
        await crawler.start_browser()
        
        # 날짜 범위 설정
        start_date = ""
        end_date = ""
        stop_on_duplicate = False

        if mode == "history":
            start_date = args.start
            end_date = args.end
            # History 모드는 중복이 있어도 멈추지 않고 기간 내 데이터를 모두 갱신/확인
            stop_on_duplicate = False 
        else:
            # Interval / Cron 모드
            start_date = get_today_str()
            end_date = get_yesterday_str
            # 이미 수집한 데이터가 나오면 즉시 종료
            stop_on_duplicate = True

        # 검색 수행
        search_success = await crawler.search_period(start_date, end_date)
        
        if search_success:
            # 데이터 처리 콜백 함수 정의
            # check_only=True: ID 중복 여부만 리턴 (True: 진행, False: 중복/스킵)
            # check_only=False: 데이터 저장 수행
            def save_callback(data, notice_id, check_only=False):

                is_new = storage.is_new(notice_id)
                
                if check_only:
                    # 새로운 데이터면 진행(True), 아니면 스킵(False)
                    return is_new
                
                if data:
                    storage.save_data(data, notice_id)
                    return True
                return False

            # 페이지 순회 시작
            await crawler.crawl_period_pages(
                save_callback=save_callback,
                stop_on_duplicate=stop_on_duplicate
            )
            
    except Exception as e:
        print(f"[Error] Crawler task error: {e}")
    finally:
        await crawler.close_browser()


def main():
    
    parser = argparse.ArgumentParser(description="누리장터 입찰공고 수집 시스템")
    parser.add_argument("--mode", choices=["history", "interval", "cron"], required=True, help="Execution mode")
    parser.add_argument("--start", type=str, help="Start date (YYYYMMDD) for history mode")
    parser.add_argument("--end", type=str, help="End date (YYYYMMDD) for history mode")
    parser.add_argument("--interval", type=int, default=600, help="Interval seconds (default: 600)")
    parser.add_argument("--hour", type=int, default=9, help="Cron hour (0-23)")
    
    args = parser.parse_args()

    # 저장소 초기화
    storage = DataStorage()
    print(f"[System] Storage loaded. Current items: {storage.get_stats()}")

    # 모드별 실행 로직
    if args.mode == "history":
        if not args.start or not args.end:
            print("[ERROR] History mode requires --start and --end arguments.")
            sys.exit(1)
            
        print(f"[System] Starting History Mode: {args.start} ~ {args.end}")
        asyncio.run(run_task("history", args, storage))

    elif args.mode == "interval":
        print(f"[System] Starting Interval Mode (Every {args.interval}s)")
        scheduler = AsyncIOScheduler()
        
        # 첫 실행
        scheduler.add_job(run_task, 'date', args=["interval", args, storage])
        # 주기적 실행
        scheduler.add_job(run_task, 'interval', seconds=args.interval, args=["interval", args, storage])
        
        scheduler.start()
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            print("[System] Scheduler stopped.")

    elif args.mode == "cron":
        print(f"[System] Starting Cron Mode (Daily at {args.hour}:00)")
        scheduler = AsyncIOScheduler()
        
        scheduler.add_job(run_task, 'cron', hour=args.hour, args=["cron", args, storage])
        
        scheduler.start()
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            print("[System] Scheduler stopped.")

if __name__ == "__main__":
    main()