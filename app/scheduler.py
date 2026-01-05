#!/usr/bin/env python3
"""
Python-based scheduler for explicit-labeler.
Replaces cron to allow running without root privileges.

This script schedules mark_explicit_music.py to run at configured intervals
and handles log rotation before each run.
"""

import os
import sys
import subprocess
import gzip
import shutil
import re
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Environment variables
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/explicit-labeler.log")
LOG_RETENTION_RUNS = int(os.getenv("LOG_RETENTION_RUNS", "7"))
APP_TIMES = os.getenv("APP_TIMES", "02:00")
RUN_AT_START = os.getenv("RUN_AT_START", "true").lower() in ("true", "1", "yes")

# Validate LOG_RETENTION_RUNS
if LOG_RETENTION_RUNS < 1:
    LOG_RETENTION_RUNS = 7

def rotate_logs():
    """Rotate log file before each run (Python implementation of cron-wrapper.sh logic)."""
    log_path = Path(LOG_FILE)
    
    if not log_path.exists():
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return
    
    log_dir = log_path.parent
    log_base = log_path.stem  # filename without extension
    log_ext = log_path.suffix  # .log
    
    # Remove oldest log if we're at the retention limit
    oldest_log = log_dir / f"{log_base}-{LOG_RETENTION_RUNS}{log_ext}"
    oldest_log_gz = log_dir / f"{log_base}-{LOG_RETENTION_RUNS}{log_ext}.gz"
    
    if oldest_log.exists():
        oldest_log.unlink()
    if oldest_log_gz.exists():
        oldest_log_gz.unlink()
    
    # Shift existing rotated logs backwards (move .2 to .3, .1 to .2, etc.)
    for i in range(LOG_RETENTION_RUNS, 1, -1):
        prev = i - 1
        prev_log = log_dir / f"{log_base}-{prev}{log_ext}"
        prev_log_gz = log_dir / f"{log_base}-{prev}{log_ext}.gz"
        curr_log = log_dir / f"{log_base}-{i}{log_ext}"
        curr_log_gz = log_dir / f"{log_base}-{i}{log_ext}.gz"
        
        # Move previous to current position
        if prev_log.exists():
            shutil.move(str(prev_log), str(curr_log))
        elif prev_log_gz.exists():
            shutil.move(str(prev_log_gz), str(curr_log_gz))
    
    # Compress the current log before moving it
    if log_path.exists():
        rotated_log = log_dir / f"{log_base}-1{log_ext}"
        rotated_log_gz = log_dir / f"{log_base}-1{log_ext}.gz"
        
        # Only compress if -1.log.gz doesn't already exist
        if not rotated_log_gz.exists():
            try:
                with open(log_path, 'rb') as f_in:
                    with gzip.open(rotated_log_gz, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                log_path.unlink()
            except Exception:
                # If compression fails, just move the file
                shutil.move(str(log_path), str(rotated_log))
        else:
            # If -1.log.gz exists, just move current log to -1.log
            shutil.move(str(log_path), str(rotated_log))

def log_message(message):
    """Append a message to the log file with timestamp."""
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def run_labeler():
    """Run the mark_explicit_music.py script."""
    # Rotate logs before running
    rotate_logs()
    
    # Log run start
    log_message("=" * 60)
    log_message(f"Started scheduled run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("=" * 60)
    
    # Change to app directory
    os.chdir("/app")
    
    # Build command
    cmd = [sys.executable, "-u", "mark_explicit_music.py"]
    
    # Run the script and capture output
    try:
        # Run with unbuffered output and redirect to log file
        with open(LOG_FILE, 'a') as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
                text=True
            )
            exit_code = process.wait()
        
        # Log completion
        log_message(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_message(f"Exit code: {exit_code}")
        log_message("")
        
        return exit_code
    except Exception as e:
        log_message(f"ERROR running script: {e}")
        log_message("")
        return 1

def parse_schedule(time_str):
    """
    Parse military time format (HH:MM) into CronTrigger parameters.
    
    Format: HH:MM (24-hour format)
    Examples:
        "02:00"         -> daily at 2 AM
        "14:00"         -> daily at 2 PM
        "00:30"         -> daily at 12:30 AM
    
    Returns dict with fields for apscheduler CronTrigger.
    """
    time_str = time_str.strip()
    
    # Match HH:MM format where HH is 00-23 and MM is 00-59
    pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    if not re.match(pattern, time_str):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM format (e.g., 02:00, 14:00)")
    
    hour_str, minute_str = time_str.split(':')
    hour = int(hour_str)
    minute = int(minute_str)
    
    # Validate ranges (should already be validated by regex, but double-check)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time values: hour={hour}, minute={minute}")
    
    # Return parameters for daily schedule (minute hour day month weekday)
    # Use None for "*" (any value) for day, month, and weekday
    return {
        "minute": str(minute),
        "hour": str(hour),
        "day": None,  # "*" -> None for any day
        "month": None,  # "*" -> None for any month
        "day_of_week": None,  # "*" -> None for any weekday
    }

def main():
    """Main scheduler entry point."""
    print("=" * 60)
    print("Explicit Labeler - Python Scheduler")
    print("=" * 60)
    print(f"Schedule(s): {APP_TIMES}")
    print(f"Log file: {LOG_FILE}")
    print(f"Log retention: {LOG_RETENTION_RUNS} runs")
    print(f"Run at start: {RUN_AT_START}")
    print("=" * 60)
    print()
    
    # Parse APP_TIMES - support comma-separated multiple schedules
    # Split by comma and strip whitespace
    schedule_strings = [s.strip() for s in APP_TIMES.split(",") if s.strip()]
    
    if not schedule_strings:
        print(f"ERROR: APP_TIMES is empty or invalid: '{APP_TIMES}'", file=sys.stderr)
        sys.exit(1)
    
    triggers = []
    for idx, schedule_str in enumerate(schedule_strings):
        try:
            # Store original format for display
            original_format = schedule_str
            schedule_params = parse_schedule(schedule_str)
            # Create CronTrigger - apscheduler accepts None for "*" (any value)
            trigger = CronTrigger(
                minute=schedule_params["minute"],
                hour=schedule_params["hour"],
                day=schedule_params["day"],
                month=schedule_params["month"],
                day_of_week=schedule_params["day_of_week"],
            )
            triggers.append((trigger, original_format))
        except Exception as e:
            print(f"ERROR: Failed to parse schedule '{schedule_str}' in APP_TIMES: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Run at start if configured
    if RUN_AT_START:
        print("Running initial scan at startup...")
        run_labeler()
        print("Initial run complete. Scheduler will continue on schedule.")
        print()
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add scheduled jobs for each trigger
    for idx, (trigger, schedule_str) in enumerate(triggers):
        job_id = f"explicit-labeler-{idx}"
        scheduler.add_job(
            run_labeler,
            trigger=trigger,
            id=job_id,
            name=f"Run explicit labeler ({schedule_str})",
            replace_existing=True
        )
    
    # Display next run times
    jobs = scheduler.get_jobs()
    if jobs:
        print(f"Scheduler started with {len(jobs)} schedule(s).")
        for job in jobs:
            print(f"  Next run: {job.next_run_time} ({job.name})")
    print("Press Ctrl+C to stop.")
    print()
    
    try:
        # Run scheduler (blocks until stopped)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    main()


