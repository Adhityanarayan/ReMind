#!/usr/bin/env python3
"""
Face Recognition Database Module for ReMind
Handles face encoding storage, matching, and enrollment using face_recognition library
"""

import numpy as np
import face_recognition
import cv2
from typing import Optional, List, Dict, Any, Tuple
from .person_db import PersonDatabase


class FaceRecognitionManager:
    """Manages face recognition with database integration"""

    def __init__(self, db_path: str = "remind.db", tolerance: float = 0.6):
        """
        Initialize face recognition manager

        Args:
            db_path: Path to SQLite database
            tolerance: Face matching tolerance (lower = stricter, default 0.6)
        """
        self.person_db = PersonDatabase(db_path)
        self.tolerance = tolerance
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame using Haar Cascade (fast initial detection)

        Args:
            frame: BGR image from camera

        Returns:
            List of face rectangles (x, y, w, h)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5
        )
        return faces

    def encode_face(self, frame: np.ndarray, face_location: Tuple = None) -> Optional[np.ndarray]:
        """
        Generate face encoding from a frame

        Args:
            frame: BGR image from camera
            face_location: Optional (top, right, bottom, left) face location

        Returns:
            128-d face encoding array or None if no face found
        """
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if face_location is None:
            # Auto-detect face locations
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return None
            face_location = face_locations[0]

        # Generate encoding
        encodings = face_recognition.face_encodings(rgb_frame, [face_location])
        if encodings:
            return encodings[0]
        return None

    def recognize_face(self, frame: np.ndarray,
                      face_rect: Tuple[int, int, int, int] = None) -> Optional[Dict[str, Any]]:
        """
        Recognize a face in the frame by matching against database

        Args:
            frame: BGR image from camera
            face_rect: Optional (x, y, w, h) rectangle from Haar cascade

        Returns:
            Dictionary with person info and confidence, or None if no match
        """
        # Get face encoding from current frame
        if face_rect:
            # Convert (x, y, w, h) to (top, right, bottom, left)
            x, y, w, h = face_rect
            face_location = (y, x + w, y + h, x)
        else:
            face_location = None

        current_encoding = self.encode_face(frame, face_location)
        if current_encoding is None:
            return None

        # Get all people with face encodings from database
        all_people = self.person_db.list_all_people(active_only=True)

        known_encodings = []
        known_people = []

        for person in all_people:
            if person.get('face_encoding') is not None:
                known_encodings.append(person['face_encoding'])
                known_people.append(person)

        if not known_encodings:
            return None

        # Compare with all known faces
        face_distances = face_recognition.face_distance(known_encodings, current_encoding)
        best_match_index = np.argmin(face_distances)

        if face_distances[best_match_index] <= self.tolerance:
            person = known_people[best_match_index]
            confidence = (1 - face_distances[best_match_index]) * 100
            person['match_confidence'] = confidence
            return person

        return None

    def enroll_person(self, frames: List[np.ndarray], name: str,
                     relationship: str = None, **kwargs) -> Optional[int]:
        """
        Enroll a new person by capturing multiple face samples

        Args:
            frames: List of BGR images containing the person's face
            name: Person's name
            relationship: Relationship to patient
            **kwargs: Additional person info (phone, email, important_info, etc.)

        Returns:
            Person ID if successful, None otherwise
        """
        # Extract face encodings from all frames
        encodings = []
        for frame in frames:
            encoding = self.encode_face(frame)
            if encoding is not None:
                encodings.append(encoding)

        if not encodings:
            print("❌ No valid face encodings found in provided frames")
            return None

        # Average the encodings for better accuracy
        avg_encoding = np.mean(encodings, axis=0)

        # Check if person already exists by face
        existing_person = self.person_db.find_person_by_face(
            avg_encoding, tolerance=self.tolerance
        )

        if existing_person:
            print(f"⚠️  Similar face already enrolled: {existing_person['name']}")
            return existing_person['id']

        # Add person to database
        person_id = self.person_db.add_person(
            name=name,
            relationship=relationship,
            face_encoding=avg_encoding,
            **kwargs
        )

        print(f"✅ Enrolled {name} with {len(encodings)} face samples (ID: {person_id})")
        return person_id

    def update_face_encoding(self, person_id: int, frames: List[np.ndarray]) -> bool:
        """
        Update face encoding for an existing person

        Args:
            person_id: Person's database ID
            frames: List of new face images

        Returns:
            True if successful
        """
        encodings = []
        for frame in frames:
            encoding = self.encode_face(frame)
            if encoding is not None:
                encodings.append(encoding)

        if not encodings:
            return False

        avg_encoding = np.mean(encodings, axis=0)
        self.person_db.add_face_encoding(person_id, avg_encoding)
        return True

    def capture_enrollment_samples(self, frame: np.ndarray,
                                   samples_needed: int = 15) -> List[np.ndarray]:
        """
        Helper to collect face samples from video frames for enrollment

        Args:
            frame: Current video frame
            samples_needed: Number of samples to collect

        Returns:
            List of cropped face images
        """
        samples = []

        # Detect face
        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return samples

        # Use largest face
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face

        # Extract face region with some padding
        padding = int(w * 0.2)
        face_img = frame[
            max(0, y-padding):y+h+padding,
            max(0, x-padding):x+w+padding
        ]

        if face_img.size > 0:
            samples.append(face_img)

        return samples

    def get_all_enrolled_people(self) -> List[Dict[str, Any]]:
        """Get all people enrolled in the database"""
        return self.person_db.list_all_people(active_only=True)

    def close(self):
        """Close database connection"""
        self.person_db.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
