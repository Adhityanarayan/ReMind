#!/usr/bin/env python3
"""
ReMind - Memory Assistant for Dementia Patients
Combines face recognition, speech transcription, and contextual memory
"""

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
from pathlib import Path

# Import our database modules
from database import (
    PersonDatabase, EncounterDatabase, ContextExtractor,
    suggest_new_person
)


class RemindAssistant:
    """Real-time memory assistant with face + voice recognition"""

    def __init__(self, whisper_model="tiny", db_path="remind.db",
                 auto_learn=True):
        """
        Initialize ReMind Assistant

        Args:
            whisper_model: Whisper model size
            db_path: Database file path
            auto_learn: Automatically learn new people from conversation
        """
        print("🧠 Initializing ReMind Assistant...")

        # Database
        self.person_db = PersonDatabase(db_path)
        self.encounter_db = EncounterDatabase(db_path)
        self.context_extractor = ContextExtractor()
        self.auto_learn = auto_learn

        # Face recognition
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.face_recognizer = self._load_face_recognizer()

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
        self.encounter_transcript = ""
        self.last_transcription = ""

        # Display settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.info_display_duration = 300  # frames

        print("✅ ReMind Assistant Ready!")

    def _load_face_recognizer(self):
        """Load existing face recognizer or create new one"""
        recognizer_path = "face_recognizer.yml"

        if os.path.exists(recognizer_path):
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(recognizer_path)
            print(f"✅ Loaded face recognizer from {recognizer_path}")
            return recognizer
        else:
            print("⚠️  No face recognizer found. Train faces first or continue without.")
            return None

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

                    # For now, just log it - caregiver can confirm later
                    # In production, you'd want caregiver confirmation
                else:
                    # Update current encounter with this person
                    if existing['id'] != self.current_person_id:
                        self.current_person_id = existing['id']
                        self.current_person_name = existing['name']
                        self.encounter_db.update_encounter(
                            self.current_encounter_id,
                            person_id=self.current_person_id
                        )
                        print(f"✅ Matched to existing person: {name}")

    def recognize_face(self, frame, gray):
        """Recognize face in frame"""
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            return None, None, None

        # Use largest face
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face

        if self.face_recognizer is None:
            return None, largest_face, None

        # Recognize
        roi_gray = gray[y:y+h, x:x+w]
        label, confidence = self.face_recognizer.predict(roi_gray)

        # Get person from database using face encoding
        # For now, using LBPH label as person ID
        # TODO: Implement proper face encoding matching

        if confidence < 70:  # Good match
            # Load labels.json to map label to name
            if os.path.exists('labels.json'):
                with open('labels.json', 'r') as f:
                    labels = json.load(f)
                    name = {v: k for k, v in labels.items()}.get(label, "Unknown")

                    # Get person from database
                    person = self.person_db.get_person_by_name(name)
                    if person:
                        return person, largest_face, 100 - confidence
                    else:
                        # Person recognized but not in database yet
                        return {'name': name, 'id': None}, largest_face, 100 - confidence

        return None, largest_face, None

    def draw_person_info(self, frame, person, face_rect, confidence):
        """Draw person information overlay on frame"""
        if face_rect is None:
            return

        x, y, w, h = face_rect

        # Draw face rectangle
        color = (0, 255, 0) if confidence and confidence > 50 else (0, 165, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        if person is None:
            cv2.putText(frame, "Unknown", (x, y-10),
                       self.font, 0.9, (0, 0, 255), 2)
            return

        # Get person info from database
        person_id = person.get('id')
        name = person.get('name', 'Unknown')
        relationship = person.get('relationship', '')

        # Display name and relationship
        display_text = name
        if relationship:
            display_text += f" ({relationship})"

        cv2.putText(frame, display_text, (x, y-10),
                   self.font, 0.9, color, 2)

        if confidence:
            conf_text = f"{confidence:.0f}%"
            cv2.putText(frame, conf_text, (x, y+h+25),
                       self.font, 0.6, color, 1)

        # If we have database info, show additional context
        if person_id:
            self._draw_context_panel(frame, person_id)

    def _draw_context_panel(self, frame, person_id):
        """Draw context information panel"""
        # Get encounter summary
        summary = self.encounter_db.get_encounter_summary(person_id)

        # Panel position (right side)
        panel_x = frame.shape[1] - 400
        panel_y = 10
        panel_w = 390
        line_height = 30

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + 300),
                     (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Draw border
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + 300),
                     (255, 255, 255), 2)

        # Display info
        y_pos = panel_y + 30
        text_color = (255, 255, 255)
        font_scale = 0.6

        # Last seen
        last_seen = summary.get('time_since_last_seen')
        if last_seen and last_seen != "0 minutes ago":
            cv2.putText(frame, f"Last seen: {last_seen}", (panel_x + 10, y_pos),
                       self.font, font_scale, text_color, 1)
            y_pos += line_height

        # Visit count
        total_visits = summary.get('total_encounters', 0)
        if total_visits > 1:
            cv2.putText(frame, f"Visits: {total_visits} times", (panel_x + 10, y_pos),
                       self.font, font_scale, text_color, 1)
            y_pos += line_height

        # Common topics
        common_topics = summary.get('common_topics', [])
        if common_topics:
            cv2.putText(frame, "Recent topics:", (panel_x + 10, y_pos),
                       self.font, font_scale, (150, 255, 150), 1)
            y_pos += line_height

            for topic_info in common_topics[:3]:  # Show top 3
                topic = topic_info['topic']
                freq = topic_info['frequency']
                text = f"  • {topic}"
                cv2.putText(frame, text, (panel_x + 10, y_pos),
                           self.font, 0.5, text_color, 1)
                y_pos += 25

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
        for line in lines[-3:]:  # Last 3 lines
            cv2.putText(frame, line, (20, y_pos),
                       self.font, 0.6, (255, 255, 255), 1)
            y_pos += 25

    def process_video(self):
        """Main video processing loop"""
        cap = cv2.VideoCapture(1)

        if not cap.isOpened():
            print("❌ Error: Cannot open camera")
            return

        print("\n" + "=" * 70)
        print("🧠 ReMind Assistant Running!")
        print("=" * 70)
        print("✓ Face recognition with memory")
        print("✓ Real-time speech transcription")
        print("✓ Automatic context learning")
        print("\nControls:")
        print("  'q' - Quit")
        print("  's' - Save encounter summary")
        print("=" * 70 + "\n")

        # Start initial encounter for any audio/video that comes in
        self.current_encounter_id = self.encounter_db.start_encounter()
        self.encounter_transcript = ""
        print("📝 Encounter started - ready to record\n")

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Recognize face
            person, face_rect, confidence = self.recognize_face(frame, gray)

            # Update current person if recognized
            if person and person.get('id'):
                if person['id'] != self.current_person_id:
                    # New person detected - update encounter with person info
                    self.current_person_id = person['id']
                    self.current_person_name = person['name']

                    # Update the current encounter with person ID
                    self.encounter_db.update_encounter(
                        self.current_encounter_id,
                        person_id=self.current_person_id
                    )
                    print(f"\n👋 Hello {self.current_person_name}!")

            elif person and not person.get('id'):
                # Face detected but not in database (has name but no ID)
                if self.current_person_name == "Unknown":
                    self.current_person_name = person.get('name', 'Unknown')
                    print(f"\n👤 Face detected: {self.current_person_name} (not in database)")

            else:
                # No face detected - keep current encounter running
                if self.current_person_name != "Unknown" and not person:
                    # Person left frame
                    pass  # Keep same encounter, they might come back

            # Draw person info
            self.draw_person_info(frame, person, face_rect, confidence)

            # Draw transcription
            self.draw_transcription(frame)

            # Status bar
            status = f"Speaker: {self.current_person_name}"
            cv2.putText(frame, status, (10, 30),
                       self.font, 0.8, (0, 255, 255), 2)

            cv2.imshow('ReMind Assistant', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self._save_encounter_summary()

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

        # Show what was saved
        print(f"\n✅ Encounter saved!")
        print(f"   Person: {self.current_person_name}")
        print(f"   Encounter ID: {self.current_encounter_id}")
        print(f"   Transcript length: {len(self.encounter_transcript)} characters")
        print(f"   Summary: {summary}")

        if context['topics']:
            topics_str = ', '.join([f"{cat}: {', '.join(kw)}" for cat, kw in context['topics'].items()])
            print(f"   Topics: {topics_str}")

        if context['action_items']:
            print(f"   Action items: {len(context['action_items'])}")
            for item in context['action_items'][:3]:
                print(f"      • {item['action']}")

        if context['mentioned_dates']:
            print(f"   Dates mentioned: {', '.join(context['mentioned_dates'][:3])}")

        print(f"\n💡 Tip: Press 's' anytime to save, or quit to auto-save")

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
            self._save_encounter_summary()
            self.encounter_db.end_encounter(self.current_encounter_id)

        # Close databases
        self.person_db.close()
        self.encounter_db.close()

        print("\n✅ ReMind Assistant stopped")


def main():
    parser = argparse.ArgumentParser(
        description="ReMind - Memory Assistant for Dementia Patients"
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

    assistant = RemindAssistant(
        whisper_model=args.model,
        db_path=args.db,
        auto_learn=not args.no_auto_learn
    )
    assistant.start()


if __name__ == "__main__":
    main()