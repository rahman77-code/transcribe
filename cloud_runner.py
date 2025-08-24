#!/usr/bin/env python3
"""
Cloud-optimized runner for the daily call processor
Handles both scheduled runs and one-time executions
"""
import os
import sys
from datetime import datetime, timedelta
from daily_call_processor_multi_key import DailyCallProcessorMultiKey

def main():
    # Check if we should run as scheduler or one-time
    run_mode = os.environ.get('RUN_MODE', 'once')
    
    processor = DailyCallProcessorMultiKey()
    
    if run_mode == 'scheduler':
        print("Starting in scheduler mode...")
        processor.run_scheduled()
    else:
        # Run once for yesterday's calls
        yesterday = datetime.now().date() - timedelta(days=1)
        print(f"Processing calls for {yesterday}")
        processor.process_daily_calls(yesterday)

if __name__ == "__main__":
    main()
