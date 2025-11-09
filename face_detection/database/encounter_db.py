#!/usr/bin/env python3
"""
Encounter Database Module for ReMind
Manages encounters/visits and conversation logs
"""

import sqlite3
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


class EncounterDatabase:
    """Database manager for encounters and conversations"""

    def __init__(self, db_path: str = "remind.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Allow connection to be used across threads
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        # Thread lock for database operations
        self._lock = threading.Lock()

    def start_encounter(self, person_id: Optional[int] = None,
                       location: str = None) -> int:
        """
        Start a new encounter/visit

        Args:
            person_id: ID of the person (None if unknown initially)
            location: Where the encounter is happening

        Returns:
            Encounter ID
        """
        query = """
            INSERT INTO encounters (person_id, location, start_time)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """
        self.cursor.execute(query, (person_id, location))
        self.conn.commit()
        return self.cursor.lastrowid

    def end_encounter(self, encounter_id: int):
        """
        End an encounter and calculate duration

        Args:
            encounter_id: Encounter ID
        """
        query = """
            UPDATE encounters
            SET end_time = CURRENT_TIMESTAMP,
                duration_seconds = (
                    SELECT (julianday(CURRENT_TIMESTAMP) - julianday(start_time)) * 86400
                    FROM encounters WHERE id = ?
                )
            WHERE id = ?
        """
        self.cursor.execute(query, (encounter_id, encounter_id))
        self.conn.commit()

    def update_encounter(self, encounter_id: int, **kwargs):
        """
        Update encounter information

        Args:
            encounter_id: Encounter ID
            **kwargs: Fields to update
        """
        allowed_fields = [
            'person_id', 'full_transcript', 'summary', 'key_topics',
            'mentioned_names', 'mentioned_dates', 'mentioned_places',
            'action_items', 'patient_mood', 'confusion_level',
            'repetitive_questions', 'recognition_confidence', 'location'
        ]

        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")

                # Convert lists/dicts to JSON
                if isinstance(value, (list, dict)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if not updates:
            return

        values.append(encounter_id)
        query = f"UPDATE encounters SET {', '.join(updates)} WHERE id = ?"

        self.cursor.execute(query, values)
        self.conn.commit()

    def add_transcript_chunk(self, encounter_id: int, text: str):
        """
        Append text to encounter transcript

        Args:
            encounter_id: Encounter ID
            text: Transcript text to append
        """
        query = """
            UPDATE encounters
            SET full_transcript = COALESCE(full_transcript || ' ', '') || ?
            WHERE id = ?
        """
        with self._lock:
            self.cursor.execute(query, (text, encounter_id))
            self.conn.commit()

    def get_encounter(self, encounter_id: int) -> Optional[Dict[str, Any]]:
        """
        Get encounter by ID

        Args:
            encounter_id: Encounter ID

        Returns:
            Encounter dictionary or None
        """
        query = "SELECT * FROM encounters WHERE id = ?"
        self.cursor.execute(query, (encounter_id,))
        row = self.cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    def get_recent_encounters(self, person_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent encounters for a person

        Args:
            person_id: Person's ID
            limit: Maximum number of encounters to return

        Returns:
            List of encounter dictionaries
        """
        query = """
            SELECT * FROM encounters
            WHERE person_id = ?
            ORDER BY start_time DESC
            LIMIT ?
        """
        self.cursor.execute(query, (person_id, limit))
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_last_encounter(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent encounter for a person

        Args:
            person_id: Person's ID

        Returns:
            Encounter dictionary or None
        """
        encounters = self.get_recent_encounters(person_id, limit=1)
        return encounters[0] if encounters else None

    def get_encounters_by_date_range(self, start_date: datetime,
                                    end_date: datetime = None) -> List[Dict[str, Any]]:
        """
        Get encounters within a date range

        Args:
            start_date: Start of date range
            end_date: End of date range (default: now)

        Returns:
            List of encounters
        """
        if end_date is None:
            end_date = datetime.now()

        query = """
            SELECT e.*, p.name, p.relationship
            FROM encounters e
            LEFT JOIN people p ON e.person_id = p.id
            WHERE e.start_time BETWEEN ? AND ?
            ORDER BY e.start_time DESC
        """
        self.cursor.execute(query, (start_date, end_date))
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_todays_encounters(self) -> List[Dict[str, Any]]:
        """Get all encounters from today"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_encounters_by_date_range(today)

    def add_topic(self, encounter_id: int, topic: str,
                  category: str = None, importance: int = 1):
        """
        Add a topic/keyword to an encounter

        Args:
            encounter_id: Encounter ID
            topic: Topic text
            category: Topic category (Health, Family, etc.)
            importance: Importance level (1-5)
        """
        query = """
            INSERT INTO topics (encounter_id, topic, category, importance)
            VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(query, (encounter_id, topic, category, importance))
        self.conn.commit()

    def get_topics_for_encounter(self, encounter_id: int) -> List[Dict[str, Any]]:
        """
        Get all topics for an encounter

        Args:
            encounter_id: Encounter ID

        Returns:
            List of topic dictionaries
        """
        query = """
            SELECT * FROM topics
            WHERE encounter_id = ?
            ORDER BY importance DESC, timestamp DESC
        """
        self.cursor.execute(query, (encounter_id,))
        rows = self.cursor.fetchall()

        return [dict(row) for row in rows]

    def get_common_topics(self, person_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most common topics discussed with a person

        Args:
            person_id: Person's ID
            limit: Maximum number of topics

        Returns:
            List of topics with counts
        """
        query = """
            SELECT t.topic, t.category, COUNT(*) as frequency,
                   MAX(t.timestamp) as last_mentioned
            FROM topics t
            JOIN encounters e ON t.encounter_id = e.id
            WHERE e.person_id = ?
            GROUP BY t.topic, t.category
            ORDER BY frequency DESC, last_mentioned DESC
            LIMIT ?
        """
        self.cursor.execute(query, (person_id, limit))
        rows = self.cursor.fetchall()

        return [dict(row) for row in rows]

    def log_activity(self, activity_type: str, description: str,
                    person_id: Optional[int] = None):
        """
        Log an activity (for tracking patterns)

        Args:
            activity_type: Type of activity
            description: Activity description
            person_id: Associated person ID (optional)
        """
        query = """
            INSERT INTO activity_log (activity_type, description, person_id)
            VALUES (?, ?, ?)
        """
        self.cursor.execute(query, (activity_type, description, person_id))
        self.conn.commit()

    def get_time_since_last_seen(self, person_id: int) -> Optional[str]:
        """
        Get human-readable time since last encounter

        Args:
            person_id: Person's ID

        Returns:
            String like "2 days ago" or None
        """
        last = self.get_last_encounter(person_id)
        if not last or not last.get('start_time'):
            return None

        last_time = datetime.fromisoformat(last['start_time'])
        delta = datetime.now() - last_time

        if delta.days == 0:
            if delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"

    def get_encounter_summary(self, person_id: int) -> Dict[str, Any]:
        """
        Get summary of all encounters with a person

        Args:
            person_id: Person's ID

        Returns:
            Summary dictionary
        """
        query = """
            SELECT
                COUNT(*) as total_encounters,
                MAX(start_time) as last_seen,
                MIN(start_time) as first_seen,
                AVG(duration_seconds) as avg_duration,
                SUM(duration_seconds) as total_duration
            FROM encounters
            WHERE person_id = ?
        """
        self.cursor.execute(query, (person_id,))
        row = self.cursor.fetchone()

        summary = dict(row) if row else {}

        # Add time since last seen
        if person_id:
            summary['time_since_last_seen'] = self.get_time_since_last_seen(person_id)

        # Add common topics
        summary['common_topics'] = self.get_common_topics(person_id, limit=5)

        return summary

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        d = dict(row)

        # Parse JSON fields
        json_fields = [
            'key_topics', 'mentioned_names', 'mentioned_dates',
            'mentioned_places', 'action_items'
        ]

        for field in json_fields:
            if field in d and d[field]:
                try:
                    d[field] = json.loads(d[field])
                except:
                    pass

        return d

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()