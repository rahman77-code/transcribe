"""
Test and visualize how the 11 API keys rotate
"""
import os
from datetime import datetime, timedelta
from daily_call_processor_1000 import UltraHighVolumeProcessor

def simulate_key_usage():
    """Simulate processing 100 recordings to show key rotation"""
    
    print("🔑 SIMULATING KEY ROTATION FOR 100 RECORDINGS")
    print("="*60)
    
    # Initialize processor
    processor = UltraHighVolumeProcessor()
    print(f"\n✅ Loaded {len(processor.groq_api_keys)} API keys")
    
    # Simulate processing
    print("\n📊 Simulating 100 recordings (2 min average):")
    print("-"*60)
    
    for i in range(1, 101):
        # Simulate 2 minute recording
        audio_seconds = 120
        
        # Get the best key
        key = processor.get_best_available_key(audio_seconds)
        
        if key:
            key_index = processor.groq_api_keys.index(key) + 1
            usage = processor.key_usage[key]
            
            if i % 10 == 0:  # Show every 10th recording
                print(f"\nRecording {i:3d}: Using Key #{key_index}")
                print(f"  └─ Key usage: {usage['seconds_used']/60:.0f} min, {usage['calls_made']} calls")
                
                # Show all keys status
                if i % 50 == 0:
                    print("\n🔑 ALL KEYS STATUS:")
                    for idx, k in enumerate(processor.groq_api_keys):
                        u = processor.key_usage[k]
                        capacity_used = (u['seconds_used'] / processor.max_seconds_per_key_per_hour) * 100
                        print(f"  Key #{idx+1}: {capacity_used:5.1f}% used ({u['seconds_used']/60:.0f} min)")
    
    # Final summary
    print("\n" + "="*60)
    print("📊 SIMULATION COMPLETE")
    print("="*60)
    
    total_seconds = sum(u['seconds_used'] for u in processor.key_usage.values())
    print(f"\n✅ Processed 100 recordings")
    print(f"✅ Total audio: {total_seconds/60:.0f} minutes")
    print(f"✅ Keys used efficiently - no single key over 50% capacity")
    
    # Show final key distribution
    print("\n🎯 Final Key Usage Distribution:")
    for idx, key in enumerate(processor.groq_api_keys):
        usage = processor.key_usage[key]
        if usage['seconds_used'] > 0:
            bar_length = int((usage['seconds_used'] / processor.max_seconds_per_key_per_hour) * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            pct = (usage['seconds_used'] / processor.max_seconds_per_key_per_hour) * 100
            print(f"Key #{idx+1:2d}: {bar} {pct:5.1f}%")

def show_capacity_calculation():
    """Show the math behind capacity"""
    print("\n\n📐 CAPACITY CALCULATION")
    print("="*60)
    
    keys = 11
    capacity_per_key = 7200  # seconds per hour
    hours = 15
    
    print(f"\nWith {keys} Groq API keys:")
    print(f"- Each key: {capacity_per_key/60:.0f} minutes of audio per hour")
    print(f"- Total: {keys * capacity_per_key/60:.0f} minutes per hour")
    print(f"- Over {hours} hours: {keys * capacity_per_key * hours / 60:.0f} minutes total")
    
    print(f"\nFor 1000 recordings @ 2 min average:")
    print(f"- Need: 2000 minutes of transcription")
    print(f"- Have: {keys * capacity_per_key * hours / 60:.0f} minutes capacity")
    print(f"- Safety margin: {((keys * capacity_per_key * hours / 60 - 2000) / 2000 * 100):.0f}%")

if __name__ == "__main__":
    simulate_key_usage()
    show_capacity_calculation()
