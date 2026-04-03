#!/usr/bin/env python3
"""
OpenCV DNN-based Face Recognition (No dlib/face_recognition dependency)
Thread-safe implementation for web servers on macOS
"""

import numpy as np
import cv2
from typing import Optional, List, Dict, Any, Tuple
from .person_db import PersonDatabase


class OpenCVFaceRecognizer:
    """Face recognition using OpenCV DNN and LBPH recognizer (thread-safe)"""

    def __init__(self, db_path: str = "remind.db", confidence_threshold: float = 50.0):
        """
        Initialize OpenCV-based face recognition

        Args:
            db_path: Path to SQLite database
            confidence_threshold: Recognition confidence threshold (lower = stricter)
        """
        self.person_db = PersonDatabase(db_path)
        self.confidence_threshold = confidence_threshold

        # Haar Cascade for fast face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # LBPH Face Recognizer (thread-safe, no dlib)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_trained = False
        self.label_to_person_id = {}

        # Train recognizer on startup
        self._train_recognizer()

    def _train_recognizer(self):
        """Train LBPH recognizer on all enrolled faces"""
        all_people = self.person_db.list_all_people(active_only=True)

        faces = []
        labels = []

        for idx, person in enumerate(all_people):
            if person.get('face_encoding') is not None:
                # Reconstruct face image from encoding (stored as grayscale image data)
                face_data = person['face_encoding']

                # If we have face_samples stored, use them
                # Otherwise skip this person for now
                if isinstance(face_data, (list, np.ndarray)) and len(face_data) > 0:
                    if isinstance(face_data, list):
                        face_data = np.array(face_data)

                    # Ensure it's a valid grayscale image
                    if len(face_data.shape) == 2:
                        faces.append(face_data.astype(np.uint8))
                        labels.append(idx)
                        self.label_to_person_id[idx] = person['id']

        if len(faces) > 0:
            self.recognizer.train(faces, np.array(labels))
            self.is_trained = True
            print(f"✅ Trained face recognizer with {len(faces)} samples from {len(set(labels))} people")
        else:
            print("⚠️ No face samples found in database for training")

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame using Haar Cascade

        Args:
            frame: BGR image from camera

        Returns:
            List of face rectangles (x, y, w, h)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return faces

    def extract_face(self, frame: np.ndarray, face_rect: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Extract and normalize face region

        Args:
            frame: BGR image
            face_rect: (x, y, w, h) rectangle

        Returns:
            Normalized grayscale face image (100x100)
        """
        x, y, w, h = face_rect
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = gray[y:y+h, x:x+w]

        # Resize to standard size for recognition
        face_resized = cv2.resize(face, (100, 100))

        # Histogram equalization for better recognition
        face_normalized = cv2.equalizeHist(face_resized)

        return face_normalized

    def recognize_face(self, frame: np.ndarray,
                      face_rect: Tuple[int, int, int, int] = None) -> Optional[Dict[str, Any]]:
        """
        Recognize a face in the frame

        Args:
            frame: BGR image from camera
            face_rect: Optional (x, y, w, h) rectangle

        Returns:
            Dictionary with person info and confidence, or None if no match
        """
        # IMPORTANT: Return None if not trained to avoid crashes
        if not self.is_trained:
            return None

        # Detect face if not provided
        if face_rect is None:
            faces = self.detect_faces(frame)
            if len(faces) == 0:
                return None
            face_rect = faces[0]  # Use first detected face

        try:
            # Extract and normalize face
            face_normalized = self.extract_face(frame, face_rect)

            # Recognize using LBPH (may crash if not properly trained)
            label, confidence = self.recognizer.predict(face_normalized)

            # Lower confidence value = better match (LBPH returns distance)
            if confidence < self.confidence_threshold:
                person_id = self.label_to_person_id.get(label)
                if person_id:
                    person = self.person_db.get_person(person_id)
                    if person:
                        # Convert to percentage (invert since lower is better)
                        match_confidence = max(0, 100 - confidence)
                        person['match_confidence'] = match_confidence
                        return person
        except Exception as e:
            print(f"⚠️ Face recognition error: {e}")
            return None

        return None

    def enroll_person(self, frames: List[np.ndarray], name: str,
                     relationship: str = None, **kwargs) -> Optional[int]:
        """
        Enroll a new person by capturing multiple face samples

        Args:
            frames: List of BGR images containing the person's face
            name: Person's name
            relationship: Relationship to patient
            **kwargs: Additional person info

        Returns:
            Person ID if successful, None otherwise
        """
        # Extract faces from all frames
        face_samples = []

        for frame in frames:
            faces = self.detect_faces(frame)
            if len(faces) > 0:
                # Use first/largest face
                face_rect = faces[0]
                face_normalized = self.extract_face(frame, face_rect)
                face_samples.append(face_normalized)

        if len(face_samples) == 0:
            print("❌ No valid faces found in provided frames")
            return None

        # Use the median face as the reference encoding
        median_face = np.median(face_samples, axis=0).astype(np.uint8)

        # Add person to database with face encoding
        person_id = self.person_db.add_person(
            name=name,
            relationship=relationship,
            face_encoding=median_face,  # Store the normalized face image
            **kwargs
        )

        # Retrain recognizer with new person
        self._train_recognizer()

        print(f"✅ Enrolled {name} with {len(face_samples)} face samples (ID: {person_id})")
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
        face_samples = []

        for frame in frames:
            faces = self.detect_faces(frame)
            if len(faces) > 0:
                face_rect = faces[0]
                face_normalized = self.extract_face(frame, face_rect)
                face_samples.append(face_normalized)

        if len(face_samples) == 0:
            return False

        median_face = np.median(face_samples, axis=0).astype(np.uint8)
        self.person_db.add_face_encoding(person_id, median_face)

        # Retrain recognizer
        self._train_recognizer()
        return True

    def get_all_enrolled_people(self) -> List[Dict[str, Any]]:
        """Get all people enrolled in the database"""
        return self.person_db.list_all_people(active_only=True)

    def close(self):
        """Close database connection"""
        self.person_db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()