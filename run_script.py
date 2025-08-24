#!/usr/bin/env python3
"""
Bulletproof script runner that can survive computer restarts and interruptions
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('script_runner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_with_restarts():
    """Run the main script with automatic restarts on failure"""
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Starting attempt {attempt}/{max_attempts}")
        
        try:
            # Run the main script
            result = subprocess.run([
                sys.executable, 
                "daily_call_processor_dev_optimized.py"
            ], capture_output=False, text=True)
            
            if result.returncode == 0:
                logger.info("Script completed successfully!")
                break
            else:
                logger.error(f"Script failed with return code {result.returncode}")
                
        except KeyboardInterrupt:
            logger.info("Script interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        if attempt < max_attempts:
            wait_time = 60 * attempt  # Wait longer each attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    logger.info("Script runner finished")

if __name__ == "__main__":
    run_with_restarts()

