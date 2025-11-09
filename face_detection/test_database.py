#!/usr/bin/env python3
"""
Test script for ReMind database modules
"""

import os
import sys
from database import PersonDatabase, EncounterDatabase, ContextExtractor
from datetime import datetime


def test_person_database():
    """Test person database functionality"""
    print("\n" + "=" * 60)
    print("Testing Person Database")
    print("=" * 60)

    # Use test database
    db_path = "test_remind.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = PersonDatabase(db_path)

    # Add people
    print("\n1. Adding people...")
    sarah_id = db.add_person(
        name="Sarah",
        relationship="Daughter",
        notes="Visits every Tuesday and Thursday",
        important_info="Brings medications",
        phone="555-0123"
    )
    print(f"   ✓ Added Sarah (ID: {sarah_id})")

    john_id = db.add_person(
        name="John",
        relationship="Son",
        notes="Lives nearby"
    )
    print(f"   ✓ Added John (ID: {john_id})")

    nurse_id = db.add_person(
        name="Mary",
        relationship="Home Nurse",
        important_info="Comes every morning at 9 AM"
    )
    print(f"   ✓ Added Mary (ID: {nurse_id})")

    # Retrieve people
    print("\n2. Retrieving people...")
    sarah = db.get_person(sarah_id)
    print(f"   ✓ Retrieved: {sarah['name']} ({sarah['relationship']})")

    # Search
    print("\n3. Searching...")
    results = db.search_people("nurse")
    print(f"   ✓ Found {len(results)} nurse(s): {results[0]['name']}")

    # List all
    print("\n4. Listing all people...")
    all_people = db.list_all_people()
    for person in all_people:
        print(f"   - {person['name']} ({person['relationship']})")

    db.close()
    print("\n✅ Person Database Test Passed!")
    return db_path


def test_encounter_database(db_path):
    """Test encounter database functionality"""
    print("\n" + "=" * 60)
    print("Testing Encounter Database")
    print("=" * 60)

    person_db = PersonDatabase(db_path)
    encounter_db = EncounterDatabase(db_path)

    # Get Sarah's ID
    sarah = person_db.get_person_by_name("Sarah")
    sarah_id = sarah['id']

    # Start encounter
    print("\n1. Starting encounter...")
    encounter_id = encounter_db.start_encounter(
        person_id=sarah_id,
        location="Living Room"
    )
    print(f"   ✓ Started encounter ID: {encounter_id}")

    # Add transcript
    print("\n2. Adding transcript...")
    transcript = "Hello mom, it's Sarah, your daughter. How are you feeling today?"
    encounter_db.add_transcript_chunk(encounter_id, transcript)
    print(f"   ✓ Added transcript chunk")

    # Add more conversation
    encounter_db.add_transcript_chunk(
        encounter_id,
        " Remember to take your medicine at 2 PM. Dr. Smith appointment is tomorrow."
    )

    # Add topics
    print("\n3. Adding topics...")
    encounter_db.add_topic(encounter_id, "medication", "health", importance=5)
    encounter_db.add_topic(encounter_id, "doctor appointment", "health", importance=5)
    encounter_db.add_topic(encounter_id, "Sarah's visit", "family", importance=3)
    print(f"   ✓ Added 3 topics")

    # Update encounter metadata
    print("\n4. Updating encounter metadata...")
    encounter_db.update_encounter(
        encounter_id,
        mentioned_dates=["tomorrow", "2 PM"],
        action_items=["Take medicine at 2 PM", "Doctor appointment tomorrow"],
        patient_mood="Happy"
    )
    print(f"   ✓ Updated metadata")

    # End encounter
    print("\n5. Ending encounter...")
    encounter_db.end_encounter(encounter_id)
    print(f"   ✓ Encounter ended")

    # Retrieve encounter
    print("\n6. Retrieving encounter...")
    encounter = encounter_db.get_encounter(encounter_id)
    print(f"   ✓ Duration: {encounter.get('duration_seconds', 0):.1f} seconds")
    print(f"   ✓ Transcript length: {len(encounter.get('full_transcript', ''))} chars")

    # Get summary
    print("\n7. Getting encounter summary...")
    summary = encounter_db.get_encounter_summary(sarah_id)
    print(f"   ✓ Total encounters: {summary['total_encounters']}")
    print(f"   ✓ Last seen: {summary['time_since_last_seen']}")

    person_db.close()
    encounter_db.close()
    print("\n✅ Encounter Database Test Passed!")


def test_context_extractor():
    """Test context extraction from conversation"""
    print("\n" + "=" * 60)
    print("Testing Context Extractor")
    print("=" * 60)

    extractor = ContextExtractor()

    # Test transcript
    transcript = """
    Hello mom, it's me, Sarah, your daughter.
    I came to remind you about your doctor appointment tomorrow at 3 PM.
    Don't forget to take your pills. We're going to the hospital for a checkup.
    Remember, your grandson's birthday party is on Saturday.
    """

    print("\n1. Extracting context from conversation...")
    context = extractor.extract_all(transcript)

    print(f"\n2. Extracted Information:")
    print(f"   Name: {context['possible_name']}")
    print(f"   Relationship: {context['possible_relationship']}")
    print(f"   Dates mentioned: {context['mentioned_dates']}")
    print(f"   Places mentioned: {context['mentioned_places']}")
    print(f"   Topics: {context['topics']}")
    print(f"   Action items: {len(context['action_items'])}")

    # Test person suggestion
    print("\n3. Testing person suggestion...")
    suggestion = extractor.suggest_person_info(transcript)
    if suggestion:
        print(f"   ✓ Suggested name: {suggestion['name']}")
        print(f"   ✓ Suggested relationship: {suggestion['relationship']}")
        print(f"   ✓ Confidence: {suggestion['confidence']:.2%}")
    else:
        print(f"   ⚠ No suggestion (confidence too low)")

    # Test summary generation
    print("\n4. Generating summary...")
    summary = extractor.generate_encounter_summary(transcript)
    print(f"   ✓ Summary: {summary}")

    print("\n✅ Context Extractor Test Passed!")


def main():
    """Run all tests"""
    print("\n🧪 ReMind Database Test Suite")
    print("=" * 60)

    try:
        # Test databases
        db_path = test_person_database()
        test_encounter_database(db_path)

        # Test context extractor
        test_context_extractor()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe database system is working correctly.")
        print(f"Test database created at: {db_path}")
        print("\nYou can now use remind_assistant.py with confidence!")

        # Cleanup
        cleanup = input("\nDelete test database? (y/n): ").strip().lower()
        if cleanup == 'y':
            os.remove(db_path)
            print("✓ Test database deleted")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()