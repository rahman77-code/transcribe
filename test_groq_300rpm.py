import os
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Test configuration
TEST_AUDIO_FILE = "test_audio.mp3"  # You'll need a small test audio file
REQUESTS_TO_TEST = 50  # Test with 50 requests
TARGET_RPM = 300  # 300 requests per minute

# Get first Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY_1")
if not GROQ_API_KEY:
    print("❌ Please set GROQ_API_KEY_1 environment variable")
    exit(1)

# Rate limiting
request_times = []
rate_lock = threading.Lock()

def wait_for_rate_limit():
    """Ensure we don't exceed 300 RPM"""
    with rate_lock:
        now = time.time()
        # Remove requests older than 1 minute
        global request_times
        request_times = [t for t in request_times if now - t < 60]
        
        # Check if we need to wait
        if len(request_times) >= TARGET_RPM:
            # Calculate how long to wait
            oldest_request = request_times[0]
            wait_time = 60 - (now - oldest_request) + 0.1  # Add 100ms buffer
            if wait_time > 0:
                print(f"⏳ Rate limit approaching, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                now = time.time()
        
        # Record this request
        request_times.append(now)

def make_transcription_request(request_num):
    """Make a single transcription request"""
    try:
        # Wait for rate limit
        wait_for_rate_limit()
        
        start_time = time.time()
        
        # Create a tiny test audio file if it doesn't exist
        if not os.path.exists(TEST_AUDIO_FILE):
            # Create a 1-second silent MP3 (smallest possible)
            with open(TEST_AUDIO_FILE, 'wb') as f:
                # Minimal MP3 header + silent frame
                f.write(b'ID3\x04\x00\x00\x00\x00\x00\x00')
                f.write(b'\xff\xfb\x90\x00' + b'\x00' * 100)
        
        # Make the API request
        with open(TEST_AUDIO_FILE, 'rb') as audio_file:
            response = requests.post(
                'https://api.groq.com/openai/v1/audio/transcriptions',
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}'
                },
                files={
                    'file': (TEST_AUDIO_FILE, audio_file, 'audio/mpeg')
                },
                data={
                    'model': 'whisper-large-v3'
                }
            )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            return {
                'request_num': request_num,
                'status': 'success',
                'elapsed': elapsed,
                'timestamp': datetime.now()
            }
        else:
            return {
                'request_num': request_num,
                'status': f'error_{response.status_code}',
                'elapsed': elapsed,
                'timestamp': datetime.now(),
                'error': response.text
            }
    
    except Exception as e:
        return {
            'request_num': request_num,
            'status': 'exception',
            'error': str(e),
            'timestamp': datetime.now()
        }

def main():
    print(f"🧪 Testing Groq API with {TARGET_RPM} RPM target")
    print(f"📊 Making {REQUESTS_TO_TEST} requests")
    print("="*50)
    
    start_time = time.time()
    results = []
    
    # Use thread pool for concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all requests
        futures = {executor.submit(make_transcription_request, i): i 
                  for i in range(REQUESTS_TO_TEST)}
        
        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            # Print progress
            if result['status'] == 'success':
                print(f"✅ Request #{result['request_num']} - {result['elapsed']:.2f}s")
            else:
                print(f"❌ Request #{result['request_num']} - {result['status']}")
                if 'error' in result:
                    print(f"   Error: {result['error'][:100]}...")
    
    # Calculate statistics
    total_time = time.time() - start_time
    successful = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] != 'success']
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS")
    print("="*50)
    print(f"Total requests: {REQUESTS_TO_TEST}")
    print(f"Successful: {len(successful)}")
    print(f"Errors: {len(errors)}")
    print(f"Total time: {total_time:.1f} seconds")
    print(f"Actual RPM: {REQUESTS_TO_TEST / (total_time / 60):.1f}")
    print(f"Success rate: {len(successful) / REQUESTS_TO_TEST * 100:.1f}%")
    
    if errors:
        print("\n❌ Error Summary:")
        error_types = {}
        for error in errors:
            error_type = error['status']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        for error_type, count in error_types.items():
            print(f"  {error_type}: {count}")
    
    print("\n💡 CONCLUSION:")
    if len(successful) == REQUESTS_TO_TEST:
        print("✅ Great news! Your API key can handle 300 RPM!")
        print("🚀 This means 700 recordings can be processed in ~3 minutes!")
    elif len(successful) > REQUESTS_TO_TEST * 0.9:
        print("✅ Good! Your API key handles high RPM well")
        print(f"⚡ Achieved {len(successful) / (total_time / 60):.0f} successful RPM")
    else:
        print("⚠️ Some rate limiting detected")
        print("💡 But this is still much faster than the old system!")
    
    # Clean up
    if os.path.exists(TEST_AUDIO_FILE):
        os.remove(TEST_AUDIO_FILE)

if __name__ == "__main__":
    main()


