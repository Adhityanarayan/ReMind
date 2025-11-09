#!/usr/bin/env python3
"""
Person Database Module for ReMind
Manages people, their face encodings, and metadata
"""

import sqlite3
import json
import pickle
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np


class PersonDatabase:
    """Database manager for people and their information"""

    def __init__(self, db_path: str = "remind.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._initialize_schema()

    def _connect(self):
        """Create database connection"""
        # Allow connection to be used across threads
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()
        # Thread lock for database operations
        self._lock = threading.Lock()

    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        schema_path = Path(__file__).parent / "schema.sql"

        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                self.conn.executescript(schema_sql)
        else:
            # Fallback: create basic schema
            self._create_basic_schema()

        self.conn.commit()

    def _create_basic_schema(self):
        """Create basic schema if schema.sql not found"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                relationship TEXT,
                photo_path TEXT,
                face_encoding BLOB,
                notes TEXT,
                important_info TEXT,
                typical_topics TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

    def add_person(self, name: str, relationship: str = None,
                   face_encoding: np.ndarray = None, photo_path: str = None,
                   notes: str = None, **kwargs) -> int:
        """
        Add a new person to the database

        Args:
            name: Person's name
            relationship: Relationship to patient (e.g., "Daughter", "Nurse")
            face_encoding: Face encoding array from face recognition
            photo_path: Path to person's photo
            notes: Any notes about the person
            **kwargs: Additional fields (phone, email, important_info, etc.)

        Returns:
            Person ID
        """
        # Serialize face encoding
        face_blob = pickle.dumps(face_encoding) if face_encoding is not None else None

        query = """
            INSERT INTO people
            (name, relationship, face_encoding, photo_path, notes,
             important_info, phone, email, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.cursor.execute(query, (
            name,
            relationship,
            face_blob,
            photo_path,
            notes,
            kwargs.get('important_info'),
            kwargs.get('phone'),
            kwargs.get('email'),
            kwargs.get('address')
        ))

        self.conn.commit()
        return self.cursor.lastrowid

    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        Get person by ID

        Args:
            person_id: Person's database ID

        Returns:
            Dictionary with person information or None
        """
        query = "SELECT * FROM people WHERE id = ?"
        self.cursor.execute(query, (person_id,))
        row = self.cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    def get_person_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get person by name

        Args:
            name: Person's name (case-insensitive)

        Returns:
            Dictionary with person information or None
        """
        query = "SELECT * FROM people WHERE LOWER(name) = LOWER(?)"
        self.cursor.execute(query, (name,))
        row = self.cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    def find_person_by_face(self, face_encoding: np.ndarray,
                           tolerance: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        Find person by matching face encoding

        Args:
            face_encoding: Face encoding to match
            tolerance: Match tolerance (lower = stricter)

        Returns:
            Best matching person or None
        """
        # Get all people with face encodings
        query = "SELECT * FROM people WHERE face_encoding IS NOT NULL AND is_active = 1"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        best_match = None
        best_distance = float('inf')

        for row in rows:
            stored_encoding = pickle.loads(row['face_encoding'])

            # Calculate Euclidean distance
            distance = np.linalg.norm(face_encoding - stored_encoding)

            if distance < tolerance and distance < best_distance:
                best_distance = distance
                best_match = row

        if best_match:
            person = self._row_to_dict(best_match)
            person['match_confidence'] = 1 - (best_distance / tolerance)
            return person

        return None

    def update_person(self, person_id: int, **kwargs):
        """
        Update person information

        Args:
            person_id: Person's ID
            **kwargs: Fields to update
        """
        # Build dynamic update query
        allowed_fields = [
            'name', 'relationship', 'photo_path', 'notes', 'important_info',
            'phone', 'email', 'address', 'typical_topics', 'visit_frequency',
            'usual_visit_time', 'is_active', 'is_trusted'
        ]

        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                if field == 'face_encoding' and isinstance(value, np.ndarray):
                    values.append(pickle.dumps(value))
                else:
                    values.append(value)

        if not updates:
            return

        # Add last_updated
        updates.append("last_updated = CURRENT_TIMESTAMP")
        values.append(person_id)

        query = f"UPDATE people SET {', '.join(updates)} WHERE id = ?"
        self.cursor.execute(query, values)
        self.conn.commit()

    def add_face_encoding(self, person_id: int, face_encoding: np.ndarray):
        """
        Add or update face encoding for a person

        Args:
            person_id: Person's ID
            face_encoding: Face encoding array
        """
        face_blob = pickle.dumps(face_encoding)
        query = "UPDATE people SET face_encoding = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?"
        self.cursor.execute(query, (face_blob, person_id))
        self.conn.commit()

    def list_all_people(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of all people

        Args:
            active_only: Only return active people

        Returns:
            List of person dictionaries
        """
        query = "SELECT * FROM people"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def search_people(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search people by name or relationship

        Args:
            search_term: Search query

        Returns:
            List of matching people
        """
        query = """
            SELECT * FROM people
            WHERE LOWER(name) LIKE LOWER(?)
               OR LOWER(relationship) LIKE LOWER(?)
            ORDER BY name
        """
        pattern = f"%{search_term}%"
        self.cursor.execute(query, (pattern, pattern))
        rows = self.cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_person_statistics(self, person_id: int) -> Dict[str, Any]:
        """
        Get statistics about a person's visits

        Args:
            person_id: Person's ID

        Returns:
            Dictionary with statistics
        """
        query = """
            SELECT
                COUNT(*) as total_visits,
                MAX(start_time) as last_visit,
                AVG(duration_seconds) as avg_duration,
                SUM(duration_seconds) as total_duration
            FROM encounters
            WHERE person_id = ?
        """
        self.cursor.execute(query, (person_id,))
        row = self.cursor.fetchone()

        return dict(row) if row else {}

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        d = dict(row)

        # Deserialize face encoding
        if d.get('face_encoding'):
            try:
                d['face_encoding'] = pickle.loads(d['face_encoding'])
            except:
                d['face_encoding'] = None

        # Parse JSON fields
        for field in ['typical_topics', 'key_topics']:
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


# Convenience functions
def create_person(name: str, relationship: str = None, **kwargs) -> int:
    """
    Quick function to create a person

    Args:
        name: Person's name
        relationship: Relationship to patient
        **kwargs: Additional fields

    Returns:
        Person ID
    """
    with PersonDatabase() as db:
        return db.add_person(name, relationship, **kwargs)


def get_person(person_id: int) -> Optional[Dict[str, Any]]:
    """Quick function to get person by ID"""
    with PersonDatabase() as db:
        return db.get_person(person_id)


def find_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Quick function to find person by name"""
    with PersonDatabase() as db:
        return db.get_person_by_name(name)