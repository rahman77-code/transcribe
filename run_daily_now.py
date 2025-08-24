"""
Run the daily call processor immediately (for yesterday's calls)
"""
from daily_call_processor_multi_key import DailyCallProcessorMultiKey
from datetime import datetime, timedelta

if __name__ == "__main__":
    processor = DailyCallProcessorMultiKey()
    
    # Process yesterday's calls
    yesterday = datetime.now().date() - timedelta(days=1)
    print(f"Processing calls for: {yesterday}")
    
    processor.process_daily_calls(yesterday)
