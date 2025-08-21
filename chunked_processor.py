#!/usr/bin/env python3
"""
Chunked processor that breaks work into smaller batches for GitHub Actions
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import your main processor
from daily_call_processor_dev_optimized import DevTierOptimizedProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChunkedProcessor(DevTierOptimizedProcessor):
    def __init__(self):
        super().__init__()
        # Reduce time limit for GitHub Actions (5 hours max)
        self.max_processing_time = 4.5 * 3600  # 4.5 hours safety limit
    
    def process_in_chunks(self, target_date: str, chunk_size: int = 20):
        """Process recordings in smaller chunks"""
        logger.info(f"🔄 Starting chunked processing for {target_date}")
        
        # Get all call logs
        all_call_logs = self.get_call_logs(target_date)
        
        if not all_call_logs:
            logger.warning("⚠️ No recordings found")
            return
        
        # Create output directory
        output_dir = Path(f"daily_recordings/{target_date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check what's already been processed
        existing_results = []
        results_file = output_dir / f"transcriptions_{target_date}.json"
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
                logger.info(f"📂 Found {len(existing_results)} existing results")
            except:
                pass
        
        # Filter out already processed recordings
        processed_ids = {r.get('id') for r in existing_results}
        remaining_logs = [
            log for log in all_call_logs 
            if log.get('recording', {}).get('id') not in processed_ids
        ]
        
        logger.info(f"📊 Total: {len(all_call_logs)}, Already processed: {len(processed_ids)}, Remaining: {len(remaining_logs)}")
        
        if not remaining_logs:
            logger.info("✅ All recordings already processed!")
            return
        
        # Process in chunks
        for i in range(0, len(remaining_logs), chunk_size):
            chunk = remaining_logs[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(remaining_logs) + chunk_size - 1) // chunk_size
            
            logger.info(f"🔄 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} recordings)")
            
            # Process this chunk with simple sequential processing
            self._process_chunk_simple(chunk, output_dir, target_date)
            
            # Check if we're running out of time
            elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
            if elapsed > self.max_processing_time * 0.9:  # 90% of time limit
                logger.warning(f"⏰ Approaching time limit, stopping after chunk {chunk_num}")
                break
        
        # Final summary
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info(f"✅ Chunk processing completed in {elapsed/3600:.2f} hours")
        logger.info(f"📊 Processed: {self.stats['recordings_processed']} recordings")

    def _process_chunk_simple(self, chunk, output_dir, target_date):
        """Process a chunk of recordings with simple sequential processing"""
        results = []
        
        for i, call_log in enumerate(chunk, 1):
            logger.info(f"📊 Processing recording {i}/{len(chunk)}")
            
            # Download recording
            download_result = self.download_recording(call_log, output_dir)
            if not download_result:
                logger.warning(f"❌ Failed to download recording {call_log.get('id', 'N/A')}")
                continue
            
            audio_path, call_metadata = download_result
            
            # Transcribe recording
            transcription_result = self.transcribe_recording(audio_path, call_metadata)
            if transcription_result:
                results.append(transcription_result)
                logger.info(f"✅ Completed recording {i}/{len(chunk)}")
            else:
                logger.warning(f"❌ Failed to transcribe recording {call_log.get('id', 'N/A')}")
        
        # Save results for this chunk
        if results:
            self.save_results(results, output_dir, target_date)
            logger.info(f"💾 Saved {len(results)} transcriptions")

def main():
    # Get target date from environment or default to yesterday
    target_date = os.getenv("TARGET_DATE")
    if not target_date:
        central_tz = timezone(timedelta(hours=-6))
        yesterday = datetime.now(central_tz) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        logger.info(f"No date specified, defaulting to yesterday: {target_date}")
    
    # Get chunk size from environment (default 20 for large batches)
    chunk_size = int(os.getenv("CHUNK_SIZE", "20"))
    
    processor = ChunkedProcessor()
    processor.process_in_chunks(target_date, chunk_size)

if __name__ == "__main__":
    main()
