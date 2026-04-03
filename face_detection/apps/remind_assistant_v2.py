#!/usr/bin/env python3
"""
ReMind V2 - Memory Assistant for Dementia Patients
Enhanced with proper face recognition and enrollment workflow
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import whisper
import sounddevice as sd
import numpy as np
import queue
import threading
import json
import os
import argparse
from datetime import datetime
from typing import Optional, Dict, Any

# Import our database modules
from database import (
    PersonDatabase, EncounterDatabase, ContextExtractor,
    FaceRecognitionManager, suggest_new_person
)


class RemindAssistantV2:
    """Real-time memory assistant with advanced face recognition and enrollment"""

    def __init__(self, whisper_model="tiny", db_path="remind.db",
                 auto_learn=True):
        """
        Initialize ReMind Assistant V2

        Args:
            whisper_model: Whisper model size
            db_path: Database file path
            auto_learn: Automatically learn new people from conversation
        """
        print("🧠 Initializing ReMind Assistant V2...")

        # Database
        self.person_db = PersonDatabase(db_path)
        self.encounter_db = EncounterDatabase(db_path)
        self.context_extractor = ContextExtractor()
        self.face_recognition = FaceRecognitionManager(db_path, tolerance=0.6)
        self.auto_learn = auto_learn

        # Whisper
        print(f"Loading Whisper {whisper_model} model...")
        self.whisper_model = whisper.load_model(whisper_model)

        # Audio setup
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        self.chunk_duration = 4
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.energy_threshold = 0.01

        # State
        self.is_running = False
        self.current_encounter_id = None
        self.current_person_id = None
        self.current_person_name = "Unknown"
        self.current_person_data = None
        self.encounter_transcript = ""
        self.last_transcription = ""

        # Enrollment state
        self.enrollment_mode = False
        self.enrollment_samples = []
        self.enrollment_name = ""
        self.enrollment_relationship = ""
        self.enrollment_info = ""
        self.max_enrollment_samples = 20

        # Display settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.info_display_duration = 300  # frames

        print("✅ ReMind Assistant V2 Ready!")

    def audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback"""
        if status:
            print(f"Audio: {status}")
        self.audio_queue.put(indata.copy())

    def process_audio(self):
        """Background thread for audio processing"""
        audio_buffer = np.array([], dtype=np.float32)

        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                audio_buffer = np.concatenate([audio_buffer, chunk.flatten()])

                if len(audio_buffer) >= self.chunk_samples:
                    chunk_to_process = audio_buffer[:self.chunk_samples]
                    audio_buffer = audio_buffer[self.chunk_samples:]

                    # Transcribe
                    audio_float = chunk_to_process.astype(np.float32)
                    energy = np.sqrt(np.mean(audio_float**2))

                    if energy > self.energy_threshold:
                        result = self.whisper_model.transcribe(
                            audio_float,
                            language='en',
                            fp16=False,
                            verbose=False
                        )

                        text = result['text'].strip()
                        if text:
                            self.last_transcription = text
                            self.encounter_transcript += " " + text

                            # Update encounter in database
                            if self.current_encounter_id:
                                self.encounter_db.add_transcript_chunk(
                                    self.current_encounter_id, text
                                )

                                # Extract context and check for new person info
                                if self.auto_learn and self.current_person_id is None:
                                    self._try_learn_person(text)

                            print(f"[{self.current_person_name}]: {text}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio error: {e}")

    def _try_learn_person(self, transcript: str):
        """Try to learn person information from conversation"""
        suggestion = suggest_new_person(self.encounter_transcript)

        if suggestion and suggestion['confidence'] > 0.6:
            name = suggestion.get('name')
            relationship = suggestion.get('relationship')

            if name:
                # Check if person already exists
                existing = self.person_db.get_person_by_name(name)

                if not existing:
                    print(f"\n🎯 Detected new person: {name} ({relationship or 'unknown'})")
                    print(f"   Confidence: {suggestion['confidence']:.2%}")
                    print(f"   💡 Press 'e' to enroll this person with face recognition")
                else:
                    # Update current encounter with this person
                    if existing['id'] != self.current_person_id:
                        self.current_person_id = existing['id']
                        self.current_person_name = existing['name']
                        self.current_person_data = existing
                        self.encounter_db.update_encounter(
                            self.current_encounter_id,
                            person_id=self.current_person_id
                        )
                        print(f"✅ Matched to existing person: {name}")

    def start_enrollment(self):
        """Start face enrollment process"""
        print("\n" + "="*60)
        print("📸 FACE ENROLLMENT MODE")
        print("="*60)

        # Get person details from console (non-blocking way)
        self.enrollment_mode = True
        self.enrollment_samples = []

        print("Enter person details:")
        # Note: In production, use a GUI or web interface for this
        # For now, we'll use a simpler approach with keyboard shortcuts

    def add_enrollment_sample(self, frame: np.ndarray):
        """Add a frame sample during enrollment"""
        if len(self.enrollment_samples) >= self.max_enrollment_samples:
            return False

        # Check if face is detected
        faces = self.face_recognition.detect_faces(frame)
        if len(faces) > 0:
            self.enrollment_samples.append(frame.copy())
            return True
        return False

    def complete_enrollment(self, name: str, relationship: str = "",
                          important_info: str = ""):
        """Complete the enrollment process"""
        if len(self.enrollment_samples) < 10:
            print(f"❌ Need at least 10 samples, only have {len(self.enrollment_samples)}")
            return False

        print(f"\n📝 Enrolling {name} with {len(self.enrollment_samples)} samples...")

        person_id = self.face_recognition.enroll_person(
            frames=self.enrollment_samples,
            name=name,
            relationship=relationship,
            important_info=important_info
        )

        if person_id:
            self.enrollment_mode = False
            self.enrollment_samples = []
            print(f"✅ Successfully enrolled {name}!")

            # Update current encounter with this person
            self.current_person_id = person_id
            self.current_person_name = name
            self.current_person_data = self.person_db.get_person(person_id)

            if self.current_encounter_id:
                self.encounter_db.update_encounter(
                    self.current_encounter_id,
                    person_id=person_id
                )
            return True

        return False

    def recognize_face(self, frame) -> Optional[Dict[str, Any]]:
        """Recognize face in frame using database"""
        person = self.face_recognition.recognize_face(frame)
        return person

    def draw_person_info(self, frame, person, face_rect=None):
        """Draw comprehensive person information overlay on frame"""
        if person is None:
            if face_rect is not None:
                x, y, w, h = face_rect
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Unknown", (x, y-10),
                           self.font, 0.9, (0, 0, 255), 2)
            return

        # Get face location for drawing
        if face_rect is not None:
            x, y, w, h = face_rect
        else:
            # Use full frame if no specific rect provided
            faces = self.face_recognition.detect_faces(frame)
            if len(faces) > 0:
                x, y, w, h = faces[0]
            else:
                return

        # Draw face rectangle
        confidence = person.get('match_confidence', 0)
        color = (0, 255, 0) if confidence > 70 else (0, 165, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)

        # Display name and relationship (floating near head)
        name = person.get('name', 'Unknown')
        relationship = person.get('relationship', '')

        display_text = name
        if relationship:
            display_text += f" ({relationship})"

        # Name with background for readability
        text_size = cv2.getTextSize(display_text, self.font, 1.0, 2)[0]
        bg_rect = (x, y-40, x+text_size[0]+20, y-5)
        cv2.rectangle(frame, bg_rect[:2], bg_rect[2:], color, -1)
        cv2.putText(frame, display_text, (x+10, y-15),
                   self.font, 1.0, (255, 255, 255), 2)

        # Confidence score
        if confidence:
            conf_text = f"{confidence:.0f}%"
            cv2.putText(frame, conf_text, (x, y+h+25),
                       self.font, 0.6, color, 2)

        # Draw detailed info panel
        self._draw_detailed_info_panel(frame, person)

    def _draw_detailed_info_panel(self, frame, person):
        """Draw detailed information panel with all person data"""
        person_id = person.get('id')
        if not person_id:
            return

        # Panel position (right side)
        panel_x = frame.shape[1] - 450
        panel_y = 10
        panel_w = 440
        panel_h = 500
        line_height = 30

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h),
                     (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Border
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h),
                     (255, 255, 255), 2)

        # Title
        y_pos = panel_y + 35
        cv2.putText(frame, "PERSON INFORMATION", (panel_x + 20, y_pos),
                   self.font, 0.7, (100, 255, 100), 2)
        y_pos += 5
        cv2.line(frame, (panel_x + 10, y_pos), (panel_x + panel_w - 10, y_pos),
                (255, 255, 255), 1)
        y_pos += 25

        # Person details
        name = person.get('name', 'Unknown')
        relationship = person.get('relationship', 'N/A')
        phone = person.get('phone', 'N/A')
        important_info = person.get('important_info', '')

        text_color = (255, 255, 255)
        label_color = (150, 200, 255)
        font_scale = 0.6

        # Name
        cv2.putText(frame, f"Name: {name}", (panel_x + 15, y_pos),
                   self.font, font_scale, label_color, 1)
        y_pos += line_height

        # Relationship
        cv2.putText(frame, f"Relationship: {relationship}", (panel_x + 15, y_pos),
                   self.font, font_scale, text_color, 1)
        y_pos += line_height

        # Phone
        if phone != 'N/A':
            cv2.putText(frame, f"Phone: {phone}", (panel_x + 15, y_pos),
                       self.font, font_scale, text_color, 1)
            y_pos += line_height

        # Important info
        if important_info:
            cv2.putText(frame, "Important Info:", (panel_x + 15, y_pos),
                       self.font, font_scale, (255, 200, 100), 1)
            y_pos += line_height

            # Word wrap for important info
            words = important_info.split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if len(test_line) > 40:
                    cv2.putText(frame, ' '.join(current_line), (panel_x + 20, y_pos),
                               self.font, 0.5, text_color, 1)
                    y_pos += 22
                    current_line = [word]
                else:
                    current_line.append(word)
            if current_line:
                cv2.putText(frame, ' '.join(current_line), (panel_x + 20, y_pos),
                           self.font, 0.5, text_color, 1)
                y_pos += 25

        # Encounter summary
        y_pos += 10
        cv2.line(frame, (panel_x + 10, y_pos), (panel_x + panel_w - 10, y_pos),
                (255, 255, 255), 1)
        y_pos += 25

        summary = self.encounter_db.get_encounter_summary(person_id)

        # Last seen
        last_seen = summary.get('time_since_last_seen')
        if last_seen and last_seen != "0 minutes ago":
            cv2.putText(frame, f"Last seen: {last_seen}", (panel_x + 15, y_pos),
                       self.font, font_scale, text_color, 1)
            y_pos += line_height

        # Visit count
        total_visits = summary.get('total_encounters', 0)
        if total_visits > 1:
            cv2.putText(frame, f"Total visits: {total_visits}", (panel_x + 15, y_pos),
                       self.font, font_scale, text_color, 1)
            y_pos += line_height

        # Common topics
        common_topics = summary.get('common_topics', [])
        if common_topics:
            y_pos += 5
            cv2.putText(frame, "Recent topics:", (panel_x + 15, y_pos),
                       self.font, font_scale, (150, 255, 150), 1)
            y_pos += line_height

            for topic_info in common_topics[:4]:
                topic = topic_info['topic']
                text = f"  • {topic}"
                cv2.putText(frame, text, (panel_x + 20, y_pos),
                           self.font, 0.5, text_color, 1)
                y_pos += 25

    def draw_enrollment_overlay(self, frame):
        """Draw enrollment mode overlay"""
        samples_count = len(self.enrollment_samples)
        progress = (samples_count / self.max_enrollment_samples) * 100

        # Top banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 100, 200), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        text = f"ENROLLMENT MODE: {samples_count}/{self.max_enrollment_samples} samples"
        cv2.putText(frame, text, (20, 40),
                   self.font, 1.0, (255, 255, 255), 2)

        # Progress bar
        bar_x = 20
        bar_y = 55
        bar_w = frame.shape[1] - 40
        bar_h = 15

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                     (255, 255, 255), 2)

        progress_w = int((bar_w - 4) * (samples_count / self.max_enrollment_samples))
        cv2.rectangle(frame, (bar_x + 2, bar_y + 2),
                     (bar_x + 2 + progress_w, bar_y + bar_h - 2),
                     (0, 255, 0), -1)

    def draw_transcription(self, frame):
        """Draw current transcription at bottom"""
        if not self.last_transcription:
            return

        # Bottom panel
        panel_height = 100
        panel_y = frame.shape[0] - panel_height

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, panel_y),
                     (frame.shape[1], frame.shape[0]),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        # Border
        cv2.rectangle(frame, (0, panel_y),
                     (frame.shape[1], frame.shape[0]),
                     (255, 255, 255), 2)

        # Word wrap transcription
        max_width = frame.shape[1] - 40
        words = self.last_transcription.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            (w, h), _ = cv2.getTextSize(test_line, self.font, 0.6, 1)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Draw lines
        y_pos = panel_y + 30
        for line in lines[-3:]:
            cv2.putText(frame, line, (20, y_pos),
                       self.font, 0.6, (255, 255, 255), 1)
            y_pos += 25

    def process_video(self):
        """Main video processing loop"""
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("❌ Error: Cannot open camera")
            return

        print("\n" + "=" * 70)
        print("🧠 ReMind Assistant V2 Running!")
        print("=" * 70)
        print("✓ Advanced face recognition with database")
        print("✓ Real-time person info display")
        print("✓ Face enrollment capability")
        print("✓ Speech transcription")
        print("\nControls:")
        print("  'q' - Quit")
        print("  's' - Save encounter summary")
        print("  'e' - Start enrollment mode")
        print("  'n' - Complete enrollment (after 'e')")
        print("=" * 70 + "\n")

        # Start initial encounter
        self.current_encounter_id = self.encounter_db.start_encounter()
        self.encounter_transcript = ""
        print("📝 Encounter started - ready to record\n")

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break

            # Handle enrollment mode
            if self.enrollment_mode:
                if self.add_enrollment_sample(frame):
                    print(f"✓ Captured sample {len(self.enrollment_samples)}/{self.max_enrollment_samples}")

                self.draw_enrollment_overlay(frame)

                # Auto-complete when enough samples
                if len(self.enrollment_samples) >= self.max_enrollment_samples:
                    print("\n📸 Captured enough samples! Press 'n' to complete enrollment")

            else:
                # Regular recognition mode
                person = self.recognize_face(frame)

                # Update current person if recognized
                if person and person.get('id'):
                    if person['id'] != self.current_person_id:
                        self.current_person_id = person['id']
                        self.current_person_name = person['name']
                        self.current_person_data = person

                        # Update encounter
                        self.encounter_db.update_encounter(
                            self.current_encounter_id,
                            person_id=self.current_person_id
                        )
                        print(f"\n👋 Hello {self.current_person_name}!")

                # Draw person info
                faces = self.face_recognition.detect_faces(frame)
                face_rect = faces[0] if len(faces) > 0 else None
                self.draw_person_info(frame, person, face_rect)

            # Draw transcription
            self.draw_transcription(frame)

            # Status bar
            if not self.enrollment_mode:
                status = f"Current: {self.current_person_name}"
                cv2.putText(frame, status, (10, 30),
                           self.font, 0.8, (0, 255, 255), 2)

            cv2.imshow('ReMind Assistant V2', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self._save_encounter_summary()
            elif key == ord('e') and not self.enrollment_mode:
                self.start_enrollment()
            elif key == ord('n') and self.enrollment_mode:
                # Get enrollment details (simplified - in production use GUI)
                name = input("\nEnter person's name: ")
                relationship = input("Enter relationship (e.g., Daughter, Nurse): ")
                important_info = input("Enter important info: ")
                self.complete_enrollment(name, relationship, important_info)

        cap.release()
        cv2.destroyAllWindows()

    def _save_encounter_summary(self):
        """Save encounter summary"""
        if not self.current_encounter_id:
            print("⚠️  No active encounter to save")
            return

        if not self.encounter_transcript.strip():
            print("⚠️  No conversation recorded yet")
            return

        print(f"\n💾 Saving encounter...")

        # Extract context from transcript
        context = self.context_extractor.extract_all(self.encounter_transcript)

        # Generate summary
        summary = self.context_extractor.generate_encounter_summary(
            self.encounter_transcript
        )

        # Update encounter
        self.encounter_db.update_encounter(
            self.current_encounter_id,
            summary=summary,
            key_topics=json.dumps(context['topics']),
            mentioned_dates=json.dumps(context['mentioned_dates']),
            action_items=json.dumps(context['action_items'])
        )

        print(f"\n✅ Encounter saved!")
        print(f"   Person: {self.current_person_name}")
        print(f"   Summary: {summary}")

    def start(self):
        """Start the assistant"""
        self.is_running = True

        # Start audio processing thread
        audio_thread = threading.Thread(target=self.process_audio)
        audio_thread.daemon = True
        audio_thread.start()

        # Start audio stream
        audio_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=int(self.sample_rate * 0.5)
        )
        audio_stream.start()

        # Process video (main thread)
        try:
            self.process_video()
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            self.stop()
            audio_stream.stop()
            audio_thread.join(timeout=1)

    def stop(self):
        """Stop the assistant"""
        self.is_running = False

        # End current encounter
        if self.current_encounter_id:
            if self.encounter_transcript.strip():
                self._save_encounter_summary()
            self.encounter_db.end_encounter(self.current_encounter_id)

        # Close databases
        self.person_db.close()
        self.encounter_db.close()
        self.face_recognition.close()

        print("\n✅ ReMind Assistant stopped")


def main():
    parser = argparse.ArgumentParser(
        description="ReMind V2 - Memory Assistant with Advanced Face Recognition"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="tiny",
        choices=["tiny", "base", "small"],
        help="Whisper model (default: tiny)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="remind.db",
        help="Database file path"
    )
    parser.add_argument(
        "--no-auto-learn",
        action="store_true",
        help="Disable automatic person learning from conversation"
    )

    args = parser.parse_args()

    assistant = RemindAssistantV2(
        whisper_model=args.model,
        db_path=args.db,
        auto_learn=not args.no_auto_learn
    )
    assistant.start()


if __name__ == "__main__":
    main()
