#!/usr/bin/env python3
"""
Daily Metal Albums Orchestrator
Manages the daily scraper -> JSON -> Database cycle for website preparation
"""

import asyncio
import subprocess
import logging
import argparse
from datetime import datetime, date, timedelta, time as dt_time
from pathlib import Path
import sys
import time
import schedule
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DailyOrchestrator:
    """Orchestrates daily scraping and database updates with built-in scheduler"""
    
    def __init__(self, headless: bool = True, download_covers: bool = True, daily_time: str = "02:00"):
        # Force headless mode for server/automated environments
        self.headless = True  # Always run headless in orchestrator
        self.download_covers = download_covers
        self.script_dir = Path(__file__).parent
        self.daily_time = daily_time
        self.last_run_date = None
        self.is_running = False
    
    def run_scraper(self, target_date: date) -> tuple[bool, str]:
        """Run the scraper for a specific date"""
        date_str = target_date.strftime('%d-%m-%Y')
        
        # Build command
        cmd = [
            sys.executable, 
            str(self.script_dir / "scraper.py"),
            date_str,
            "--add-to-db"  # Always add to database
        ]
        
        if self.headless:
            cmd.append("--headless")
        
        if self.download_covers:
            cmd.append("--download-covers")
        
        logger.info(f"🚀 Starting scraper for {target_date}: {' '.join(cmd)}")
        
        try:
            # Run the scraper
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Scraper completed successfully for {target_date}")
                logger.info(f"Output: {result.stdout}")
                return True, result.stdout
            else:
                logger.error(f"❌ Scraper failed for {target_date}")
                logger.error(f"Error: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Scraper timed out for {target_date}")
            return False, "Scraper timed out after 1 hour"
        except Exception as e:
            logger.error(f"💥 Unexpected error running scraper for {target_date}: {e}")
            return False, str(e)
    
    def run_daily_update(self, target_date: date = None) -> dict:
        """Run daily update for a specific date (defaults to today)"""
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"📅 Starting daily update for {target_date}")
        start_time = time.time()
        
        # Run scraper
        success, output = self.run_scraper(target_date)
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "date": target_date.isoformat(),
            "success": success,
            "duration_seconds": round(duration, 2),
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        if success:
            logger.info(f"🎉 Daily update completed successfully for {target_date} in {duration:.2f}s")
        else:
            logger.error(f"💔 Daily update failed for {target_date} after {duration:.2f}s")
        
        return result
    
    def run_date_range(self, start_date: date, end_date: date) -> list[dict]:
        """Run scraper for a range of dates"""
        logger.info(f"📊 Starting batch update from {start_date} to {end_date}")
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            result = self.run_daily_update(current_date)
            results.append(result)
            
            # Small delay between dates to be respectful
            if current_date < end_date:
                logger.info("⏳ Waiting 30 seconds before next date...")
                time.sleep(30)
            
            current_date += timedelta(days=1)
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        logger.info(f"📈 Batch update completed: {successful}/{total} dates successful")
        
        return results
    
    def should_run_today(self) -> bool:
        """Check if we should run today (haven't run yet)"""
        today = date.today()
        return self.last_run_date != today
    
    def run_scheduled_task(self):
        """Run the daily task if it hasn't been run today"""
        if not self.should_run_today():
            logger.info(f"📅 Already processed today ({date.today()}), skipping...")
            return
        
        if self.is_running:
            logger.warning("⚠️ Scraper is already running, skipping this execution")
            return
        
        logger.info(f"🚀 Starting scheduled daily update for {date.today()}")
        self.is_running = True
        
        try:
            result = self.run_daily_update(date.today())
            if result["success"]:
                self.last_run_date = date.today()
                logger.info(f"✅ Scheduled update completed successfully")
            else:
                logger.error(f"❌ Scheduled update failed: {result['output']}")
        except Exception as e:
            logger.error(f"💥 Unexpected error in scheduled task: {e}")
        finally:
            self.is_running = False
    
    def start_scheduler(self):
        """Start the continuous scheduler"""
        logger.info(f"🕐 Starting daily scheduler - will run at {self.daily_time} every day")
        logger.info(f"📍 Current time: {datetime.now().strftime('%H:%M:%S')}")
        
        # Schedule daily task
        schedule.every().day.at(self.daily_time).do(self.run_scheduled_task)
        
        # Also run immediately if we haven't run today
        if self.should_run_today():
            logger.info("🔄 Haven't run today yet, executing immediately...")
            self.run_scheduled_task()
        
        logger.info("⏰ Scheduler started. Press Ctrl+C to stop.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("\n⏹️ Scheduler stopped by user")
        except Exception as e:
            logger.error(f"💥 Scheduler error: {e}")
            raise

def parse_date(date_str: str) -> date:
    """Parse a date string into a date object."""
    try:
        return datetime.strptime(date_str, '%d-%m-%Y').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format: DD-MM-YYYY")

async def main():
    """Main orchestrator function"""
    parser = argparse.ArgumentParser(
        description='Daily Metal Albums Orchestrator - Continuous scheduler for scraper -> JSON -> Database cycle'
    )
    
    # Scheduler mode (default)
    parser.add_argument('--scheduler', action='store_true', default=True,
                       help='Run as continuous scheduler (default mode)')
    parser.add_argument('--time', type=str, default='02:00',
                       help='Daily execution time in HH:MM format (default: 02:00)')
    
    # Manual execution modes
    parser.add_argument('--date', type=parse_date, default=None,
                       help='Run once for specific date (DD-MM-YYYY)')
    parser.add_argument('--start-date', type=parse_date, default=None,
                       help='Start date for range processing (DD-MM-YYYY)')
    parser.add_argument('--end-date', type=parse_date, default=None,
                       help='End date for range processing (DD-MM-YYYY)')
    parser.add_argument('--yesterday', action='store_true',
                       help='Run once for yesterday\'s date')
    parser.add_argument('--today', action='store_true',
                       help='Run once for today\'s date')
    
    # Scraper options (headless is always forced in orchestrator)
    parser.add_argument('--no-covers', action='store_true',
                       help='Skip downloading album covers')
    
    # Mode options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Validate time format
    try:
        datetime.strptime(args.time, '%H:%M')
    except ValueError:
        print("❌ Invalid time format. Use HH:MM (e.g., 02:00, 14:30)")
        return 1
    
    # Determine execution mode
    manual_modes = [args.date, args.start_date and args.end_date, args.yesterday, args.today]
    if sum(bool(mode) for mode in manual_modes) > 1:
        print("❌ Please specify only one execution mode")
        return 1
    
    # Determine target date(s) and mode
    if args.start_date and args.end_date:
        if args.start_date > args.end_date:
            print("❌ Start date must be before or equal to end date")
            return 1
        mode = "range"
        target_dates = (args.start_date, args.end_date)
    elif args.yesterday:
        mode = "single"
        target_dates = date.today() - timedelta(days=1)
    elif args.today:
        mode = "single"
        target_dates = date.today()
    elif args.date:
        mode = "single"
        target_dates = args.date
    else:
        mode = "scheduler"
    
    # Create orchestrator (headless is always True)
    orchestrator = DailyOrchestrator(
        headless=True,  # Always headless in orchestrator
        download_covers=not args.no_covers,
        daily_time=args.time
    )
    
    if args.dry_run:
        if mode == "scheduler":
            print(f"🔍 DRY RUN: Would start scheduler to run daily at {args.time}")
        elif mode == "single":
            print(f"🔍 DRY RUN: Would process {target_dates}")
        else:
            print(f"🔍 DRY RUN: Would process range {target_dates[0]} to {target_dates[1]}")
        return 0
    
    try:
        if mode == "scheduler":
            # Start continuous scheduler
            orchestrator.start_scheduler()
            return 0
        elif mode == "single":
            result = orchestrator.run_daily_update(target_dates)
            if result["success"]:
                print(f"\n🎉 SUCCESS: Daily update completed for {target_dates}")
                print(f"⏱️  Duration: {result['duration_seconds']}s")
                return 0
            else:
                print(f"\n💔 FAILED: Daily update failed for {target_dates}")
                print(f"❌ Error: {result['output']}")
                return 1
        else:
            results = orchestrator.run_date_range(target_dates[0], target_dates[1])
            successful = sum(1 for r in results if r["success"])
            total = len(results)
            
            print(f"\n📊 BATCH COMPLETE: {successful}/{total} dates processed successfully")
            
            # Show failed dates
            failed_dates = [r["date"] for r in results if not r["success"]]
            if failed_dates:
                print(f"❌ Failed dates: {', '.join(failed_dates)}")
            
            return 0 if successful == total else 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
