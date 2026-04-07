#!/usr/bin/env python3
"""
Combined Face Recognition + Transcription Demo
Demonstrates integration between face recognition and speech transcription
"""

import cv2
import whisper
import sounddevice as sd
import numpy as np
import queue
import threading
import json
import os
from datetime import datetime
import argparse


class CombinedSystem:
    """Integrated face recognition and transcription system"""

    def __init__(self, whisper_model="tiny", face_recognizer_path="face_recognizer.yml",
                 labels_path="labels.json"):
        """
        Initialize combined system

        Args:
            whisper_model: Whisper model size
            face_recognizer_path: Path to trained face recognizer
            labels_path: Path to labels JSON
        """
        print("Initializing Combined Face Recognition + Transcription System...")

        # Load face recognition
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        if os.path.exists(face_recognizer_path) and os.path.exists(labels_path):
            self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.face_recognizer.read(face_recognizer_path)

            with open(labels_path, 'r') as f:
                self.labels = {v: k for k, v in json.load(f).items()}

            print("✓ Face recognition loaded")
            self.face_recognition_enabled = True
        else:
            print("⚠ Face recognition not available (train model first)")
            self.face_recognition_enabled = False

        # Load Whisper
        print(f"Loading Whisper {whisper_model} model...")
        self.whisper_model = whisper.load_model(whisper_model)
        print("✓ Whisper loaded")

        # Audio setup
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        self.chunk_duration = 3  # 3 seconds for faster response
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.energy_threshold = 0.01

        # State
        self.is_running = False
        self.current_person = "Unknown"
        self.last_transcription = ""
        self.conversation_log = []

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

                            # Log conversation
                            entry = {
                                'timestamp': datetime.now().isoformat(),
                                'person': self.current_person,
                                'text': text,
                                'energy': float(energy)
                            }
                            self.conversation_log.append(entry)

                            print(f"\n[{self.current_person}]: {text}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio error: {e}")

    def recognize_face(self, frame):
        """Recognize faces in frame"""
        if not self.face_recognition_enabled:
            return "Unknown"

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            return "Unknown"

        # Use largest face
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face

        # Recognize
        roi_gray = gray[y:y+h, x:x+w]
        label, confidence = self.face_recognizer.predict(roi_gray)

        if confidence < 70:  # Good match
            return self.labels.get(label, "Unknown")
        else:
            return "Unknown"

    def process_video(self):
        """Video processing loop"""
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Cannot open camera")
            return

        print("\n" + "=" * 70)
        print("Combined System Running!")
        print("=" * 70)
        print("Video: Shows face recognition")
        print("Audio: Transcribes speech and attributes to recognized person")
        print("Press 'q' to quit, 's' to save conversation log")
        print("=" * 70 + "\n")

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break

            # Detect and recognize faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            person_detected = None

            for (x, y, w, h) in faces:
                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                if self.face_recognition_enabled:
                    roi_gray = gray[y:y+h, x:x+w]
                    label, confidence = self.face_recognizer.predict(roi_gray)

                    if confidence < 70:
                        name = self.labels.get(label, "Unknown")
                        person_detected = name
                        text = f"{name} ({100-confidence:.1f}%)"
                        color = (0, 255, 0)
                    else:
                        text = "Unknown"
                        color = (0, 0, 255)

                    cv2.putText(frame, text, (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            # Update current person
            if person_detected:
                self.current_person = person_detected
            elif len(faces) == 0:
                self.current_person = "Unknown"

            # Display transcription
            if self.last_transcription:
                # Word wrap long transcriptions
                max_width = frame.shape[1] - 20
                words = self.last_transcription.split()
                lines = []
                current_line = []

                for word in words:
                    test_line = ' '.join(current_line + [word])
                    (w, h), _ = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    if w <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]

                if current_line:
                    lines.append(' '.join(current_line))

                # Draw transcription box
                y_start = frame.shape[0] - 100
                cv2.rectangle(frame, (0, y_start), (frame.shape[1], frame.shape[0]),
                             (0, 0, 0), -1)
                cv2.rectangle(frame, (0, y_start), (frame.shape[1], frame.shape[0]),
                             (255, 255, 255), 2)

                # Draw text
                y_pos = y_start + 20
                for line in lines[:3]:  # Max 3 lines
                    cv2.putText(frame, line, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += 20

            # Display current speaker
            cv2.putText(frame, f"Speaker: {self.current_person}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            cv2.imshow('ReMind - Face + Voice Recognition', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_conversation_log()

        cap.release()
        cv2.destroyAllWindows()

    def save_conversation_log(self):
        """Save conversation log to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_log_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(self.conversation_log, f, indent=2)

        print(f"\n✓ Conversation log saved to {filename}")

    def start(self):
        """Start combined system"""
        self.is_running = True

        # Start audio processing thread
        audio_thread = threading.Thread(target=self.process_audio)
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
            print("\nStopping...")
        finally:
            self.is_running = False
            audio_stream.stop()
            audio_thread.join()

            # Save log on exit
            if self.conversation_log:
                self.save_conversation_log()
                print(f"\nTotal utterances recorded: {len(self.conversation_log)}")


def main():
    parser = argparse.ArgumentParser(
        description="Combined face recognition and speech transcription demo"
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="tiny",
        choices=["tiny", "base", "small"],
        help="Whisper model (default: tiny for real-time)"
    )
    parser.add_argument(
        "--face-model",
        type=str,
        default="face_recognizer.yml",
        help="Path to face recognizer model"
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="labels.json",
        help="Path to labels JSON"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device ID (use --list-devices to see options)"
    )

    args = parser.parse_args()

    # Set audio device if specified
    if args.device is not None:
        sd.default.device = args.device

    system = CombinedSystem(
        whisper_model=args.whisper_model,
        face_recognizer_path=args.face_model,
        labels_path=args.labels
    )
    system.start()


if __name__ == "__main__":
    main()