"""
Calculate optimal settings for processing 800+ calls daily
"""

def calculate_requirements(num_recordings, current_delays=75):
    """Calculate time and API key requirements"""
    
    print(f"🎯 Target: {num_recordings} recordings per day\n")
    
    # Current settings
    download_delay = 30
    transcription_delay = 45
    total_delay = download_delay + transcription_delay
    
    # Calculate with current delays
    total_seconds = num_recordings * total_delay
    total_hours = total_seconds / 3600
    
    print(f"With current delays ({total_delay}s per recording):")
    print(f"- Total time needed: {total_hours:.1f} hours")
    
    if total_hours > 23:
        print(f"⚠️  WARNING: Exceeds 24-hour limit!")
        
        # Calculate optimal delays
        max_seconds = 23 * 3600  # 23 hours (leave 1 hour buffer)
        optimal_delay = max_seconds / num_recordings
        
        # Split delays proportionally
        optimal_download = int(optimal_delay * 0.4)  # 40% for download
        optimal_transcribe = int(optimal_delay * 0.6)  # 60% for transcription
        
        print(f"\n✅ Optimized delays for {num_recordings} recordings in 23 hours:")
        print(f"- Download delay: {optimal_download}s")
        print(f"- Transcription delay: {optimal_transcribe}s")
        print(f"- Total per recording: {optimal_download + optimal_transcribe}s")
        
        total_delay = optimal_download + optimal_transcribe
    
    # Calculate API keys needed
    print(f"\n🔑 Groq API Key Requirements:")
    
    # Assume average call duration of 2 minutes (conservative)
    avg_call_minutes = 2
    total_audio_minutes = num_recordings * avg_call_minutes
    total_audio_hours = total_audio_minutes / 60
    
    # Each key can handle 100 minutes per hour safely (6000 seconds with buffer)
    capacity_per_key_per_hour = 100  # minutes
    
    # How many hours will processing take?
    processing_hours = (num_recordings * total_delay) / 3600
    
    # Total capacity needed
    total_capacity_needed = total_audio_minutes
    
    # Total capacity available per key
    capacity_per_key = capacity_per_key_per_hour * processing_hours
    
    # Keys needed
    keys_needed = int(total_capacity_needed / capacity_per_key) + 1
    
    print(f"- Estimated total audio: {total_audio_hours:.1f} hours")
    print(f"- Processing duration: {processing_hours:.1f} hours")
    print(f"- Capacity per key: {capacity_per_key:.0f} minutes over {processing_hours:.1f} hours")
    print(f"- **Keys needed: {keys_needed}**")
    
    return {
        'recordings': num_recordings,
        'total_hours': total_hours,
        'keys_needed': keys_needed,
        'download_delay': optimal_download if total_hours > 23 else download_delay,
        'transcribe_delay': optimal_transcribe if total_hours > 23 else transcription_delay
    }

# Calculate for different scenarios
print("="*60)
print("📊 SCALING ANALYSIS FOR HIGH VOLUME")
print("="*60)

for recordings in [600, 700, 800, 900, 1000]:
    print(f"\n{'='*40}")
    result = calculate_requirements(recordings)
    print(f"\n💡 For {recordings} recordings: Use {result['keys_needed']} Groq API keys")
    print(f"   Set delays to: {result['download_delay']}s download, {result['transcribe_delay']}s transcribe")
    
print("\n" + "="*60)
print("📌 RECOMMENDATIONS FOR 800 CALLS:")
print("- Use 5-6 Groq API keys")
print("- Adjust delays to: 40s download, 60s transcription")
print("- Total processing time: ~22 hours")
print("- Leaves 2-hour buffer for GitHub Actions")
print("="*60)
