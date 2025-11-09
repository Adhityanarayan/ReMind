#!/usr/bin/env python3
"""
Quick test to verify thread-safe database operations
"""
import threading
import time
from database import EncounterDatabase

def test_database_thread():
    """Test database access from thread"""
    print(f"Thread {threading.current_thread().name} starting...")

    # Create database connection
    db = EncounterDatabase("test_thread.db")

    # Start an encounter
    encounter_id = db.start_encounter()
    print(f"Thread {threading.current_thread().name}: Created encounter {encounter_id}")

    # Add some transcript chunks (simulating audio thread)
    for i in range(5):
        text = f"Test transcript chunk {i} from {threading.current_thread().name}"
        db.add_transcript_chunk(encounter_id, text)
        print(f"Thread {threading.current_thread().name}: Added chunk {i}")
        time.sleep(0.1)

    # End encounter
    db.end_encounter(encounter_id)

    # Close connection
    db.close()
    print(f"Thread {threading.current_thread().name} finished!")

def main():
    print("Testing thread-safe database operations...")
    print("=" * 60)

    # Create multiple threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=test_database_thread, name=f"Worker-{i+1}")
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print("=" * 60)
    print("✅ All threads completed successfully!")
    print("\nIf you see this message without errors, the thread safety fix worked!")

if __name__ == "__main__":
    main()
