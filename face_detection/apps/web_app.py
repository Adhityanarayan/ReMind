#!/usr/bin/env python3
"""
ReMind Web Interface V2
Flask web app with speech recognition, auto-learning, and real-time transcription
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
import cv2
import json
import threading
import numpy as np
import whisper
import sounddevice as sd
import queue
from datetime import datetime
from database import (
    PersonDatabase, EncounterDatabase, OpenCVFaceRecognizer,
    ContextExtractor, suggest_new_person
)

# Set template folder to web/templates
app = Flask(__name__, template_folder='../web/templates')
CORS(app)

# Global state
camera = None
face_recognition = None
person_db = None
encounter_db = None
context_extractor = None
whisper_model = None

# Real-time state
current_person = None
current_unknown_face = None  # Store unknown face for learning
unknown_face_samples = []  # Collect samples for unknown face
current_encounter_id = None
transcript_buffer = []  # Recent transcriptions
full_transcript = ""  # Full conversation
learning_candidate = None  # Detected person info from speech

# Threading locks
camera_lock = threading.Lock()
transcript_lock = threading.Lock()
face_samples_lock = threading.Lock()

# Audio setup
audio_queue = queue.Queue()
sample_rate = 16000
chunk_duration = 4
energy_threshold = 0.01
is_audio_running = False


def init_system(db_path="remind.db", whisper_size="tiny"):
    """Initialize the ReMind system with speech recognition"""
    global face_recognition, person_db, encounter_db, context_extractor
    global whisper_model, current_encounter_id, camera

    print("🧠 Initializing ReMind Web Interface...")

    # Database - Using OpenCV-based face recognition (thread-safe, no dlib)
    face_recognition = OpenCVFaceRecognizer(db_path)
    person_db = PersonDatabase(db_path)
    encounter_db = EncounterDatabase(db_path)
    context_extractor = ContextExtractor()

    # Initialize camera BEFORE starting threads (critical for macOS)
    print("📷 Initializing camera...")
    camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    if not camera.isOpened():
        print("⚠️ AVFoundation failed, trying default backend...")
        camera = cv2.VideoCapture(0)

    if camera.isOpened():
        print("✅ Camera initialized successfully")
    else:
        print("❌ WARNING: Could not initialize camera!")

    # Whisper
    print(f"Loading Whisper {whisper_size} model...")
    whisper_model = whisper.load_model(whisper_size)

    # Start encounter
    current_encounter_id = encounter_db.start_encounter()
    print(f"✅ Encounter started (ID: {current_encounter_id})")

    # Start audio processing (TEMPORARILY DISABLED - sounddevice/whisper causes crashes)
    # start_audio_processing()
    print("⚠️  Audio/transcription temporarily disabled due to macOS compatibility issues")

    print("✅ ReMind system initialized!")


def get_camera():
    """Get camera instance (singleton)"""
    global camera
    if camera is None or not camera.isOpened():
        # Use AVFoundation backend on macOS to avoid threading issues
        camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        if not camera.isOpened():
            # Fallback to default backend
            camera = cv2.VideoCapture(0)
    return camera


def audio_callback(indata, frames, time_info, status):
    """Audio stream callback"""
    if status:
        print(f"Audio status: {status}")
    audio_queue.put(indata.copy())


def process_audio():
    """Background thread for audio processing with speech recognition"""
    global full_transcript, transcript_buffer, learning_candidate, current_person
    global current_encounter_id

    audio_buffer = np.array([], dtype=np.float32)
    chunk_samples = int(sample_rate * chunk_duration)

    while is_audio_running:
        try:
            chunk = audio_queue.get(timeout=0.1)
            audio_buffer = np.concatenate([audio_buffer, chunk.flatten()])

            if len(audio_buffer) >= chunk_samples:
                chunk_to_process = audio_buffer[:chunk_samples]
                audio_buffer = audio_buffer[chunk_samples:]

                # Calculate energy
                audio_float = chunk_to_process.astype(np.float32)
                energy = np.sqrt(np.mean(audio_float**2))

                if energy > energy_threshold:
                    # Transcribe with Whisper
                    result = whisper_model.transcribe(
                        audio_float,
                        language='en',
                        fp16=False,
                        verbose=False
                    )

                    text = result['text'].strip()
                    if text:
                        timestamp = datetime.now().strftime("%H:%M:%S")

                        with transcript_lock:
                            # Add to buffers
                            transcript_entry = {
                                'time': timestamp,
                                'text': text,
                                'speaker': current_person['name'] if current_person else 'Unknown'
                            }
                            transcript_buffer.append(transcript_entry)

                            # Keep last 10 entries
                            if len(transcript_buffer) > 10:
                                transcript_buffer.pop(0)

                            full_transcript += f" {text}"

                            # Save to database
                            if current_encounter_id:
                                encounter_db.add_transcript_chunk(
                                    current_encounter_id, text
                                )

                        print(f"[{timestamp}] {text}")

                        # Try to learn person info from speech
                        if current_person is None and len(full_transcript) > 50:
                            try_extract_person_info()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Audio processing error: {e}")


def try_extract_person_info():
    """Try to extract person information from conversation"""
    global learning_candidate, full_transcript

    # Use context extractor to find person info
    suggestion = suggest_new_person(full_transcript)

    if suggestion and suggestion.get('confidence', 0) > 0.6:
        name = suggestion.get('name')
        relationship = suggestion.get('relationship')

        if name:
            # Check if already exists
            existing = person_db.get_person_by_name(name)

            if not existing:
                with transcript_lock:
                    learning_candidate = {
                        'name': name,
                        'relationship': relationship,
                        'confidence': suggestion['confidence'],
                        'context': suggestion.get('context', '')
                    }
                    print(f"🎯 Detected: {name} ({relationship}) - Confidence: {suggestion['confidence']:.0%}")


def collect_face_sample():
    """Collect face sample from unknown person for learning"""
    global unknown_face_samples, current_unknown_face

    if current_unknown_face is None:
        return

    camera = get_camera()
    with camera_lock:
        ret, frame = camera.read()
        if ret:
            faces = face_recognition.detect_faces(frame)
            if len(faces) > 0:
                with face_samples_lock:
                    unknown_face_samples.append(frame.copy())
                    # Keep last 20 samples
                    if len(unknown_face_samples) > 20:
                        unknown_face_samples.pop(0)


def auto_enroll_person():
    """Automatically enroll person if we have name from speech and face samples"""
    global learning_candidate, unknown_face_samples, current_person, current_encounter_id

    if learning_candidate is None:
        return {'success': False, 'message': 'No person info detected from speech'}

    with face_samples_lock:
        if len(unknown_face_samples) < 10:
            return {'success': False, 'message': f'Need more face samples ({len(unknown_face_samples)}/10)'}

        samples_copy = unknown_face_samples.copy()

    # Enroll the person
    name = learning_candidate['name']
    relationship = learning_candidate.get('relationship', 'Unknown')

    person_id = face_recognition.enroll_person(
        frames=samples_copy,
        name=name,
        relationship=relationship,
        important_info=f"Auto-learned from conversation. Context: {learning_candidate.get('context', '')}"
    )

    if person_id:
        # Update current state
        current_person = person_db.get_person(person_id)

        # Update encounter
        if current_encounter_id:
            encounter_db.update_encounter(
                current_encounter_id,
                person_id=person_id
            )

        # Clear learning state
        with face_samples_lock:
            unknown_face_samples.clear()
        learning_candidate = None

        print(f"✅ Auto-enrolled: {name} (ID: {person_id})")

        return {
            'success': True,
            'person_id': person_id,
            'name': name,
            'message': f'Successfully enrolled {name}!'
        }

    return {'success': False, 'message': 'Enrollment failed'}


def start_audio_processing():
    """Start audio capture and processing threads"""
    global is_audio_running

    is_audio_running = True

    # Start audio processing thread
    audio_thread = threading.Thread(target=process_audio, daemon=True)
    audio_thread.start()

    # Start audio stream
    audio_stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        callback=audio_callback,
        blocksize=int(sample_rate * 0.5)
    )
    audio_stream.start()

    print("🎤 Audio processing started")


def generate_frames():
    """Generate video frames with face recognition"""
    global current_person, current_unknown_face

    camera = get_camera()
    if not camera.isOpened():
        print("❌ ERROR: Could not open camera")
        return

    while True:
        try:
            with camera_lock:
                success, frame = camera.read()
                if not success:
                    print("⚠️ Failed to read frame from camera")
                    break

                # Perform face recognition
                person = face_recognition.recognize_face(frame)

            if person and person.get('id'):
                current_person = person
                current_unknown_face = None

                # Draw face rectangle and name
                faces = face_recognition.detect_faces(frame)
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    confidence = person.get('match_confidence', 0)
                    color = (0, 255, 0) if confidence > 70 else (0, 165, 255)

                    # Rectangle
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)

                    # Name label with background
                    name = person.get('name', 'Unknown')
                    relationship = person.get('relationship', '')
                    label = f"{name}"
                    if relationship:
                        label += f" ({relationship})"

                    # Background for text
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text_size = cv2.getTextSize(label, font, 1.0, 2)[0]
                    cv2.rectangle(frame, (x, y-40), (x+text_size[0]+20, y-5), color, -1)
                    cv2.putText(frame, label, (x+10, y-15), font, 1.0, (255, 255, 255), 2)

                    # Confidence
                    conf_text = f"{confidence:.0f}%"
                    cv2.putText(frame, conf_text, (x, y+h+25), font, 0.6, color, 2)
            else:
                # Unknown face detected
                faces = face_recognition.detect_faces(frame)
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    current_unknown_face = (x, y, w, h)

                    # Collect face sample for learning
                    collect_face_sample()

                    # Red box for unknown
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 3)

                    # Show "Learning..." if we have info from speech
                    if learning_candidate:
                        label = f"Learning: {learning_candidate['name']}"
                        sample_count = len(unknown_face_samples)
                        status = f"{sample_count}/10 samples"
                    else:
                        label = "Unknown - Listening..."
                        status = "Say your name"

                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(frame, label, (x, y-10), font, 0.9, (0, 0, 255), 2)
                    cv2.putText(frame, status, (x, y+h+25), font, 0.6, (0, 0, 255), 2)
                else:
                    current_person = None
                    current_unknown_face = None

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"❌ Error in generate_frames: {e}")
            import traceback
            traceback.print_exc()
            break


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/current_person')
def get_current_person():
    """Get current recognized person info"""
    if current_person is None:
        # Check if we're learning someone
        if learning_candidate:
            return jsonify({
                'status': 'learning',
                'candidate': learning_candidate,
                'samples_collected': len(unknown_face_samples),
                'samples_needed': 10
            })
        return jsonify({'status': 'no_person'})

    person_id = current_person.get('id')
    if not person_id:
        return jsonify({'status': 'unknown'})

    # Get full person details
    person_data = person_db.get_person(person_id)

    # Get encounter summary
    encounter_summary = encounter_db.get_encounter_summary(person_id)

    # Combine data
    result = {
        'status': 'recognized',
        'person': {
            'id': person_data['id'],
            'name': person_data['name'],
            'relationship': person_data.get('relationship'),
            'phone': person_data.get('phone'),
            'email': person_data.get('email'),
            'important_info': person_data.get('important_info'),
            'notes': person_data.get('notes'),
            'match_confidence': current_person.get('match_confidence')
        },
        'encounters': {
            'total_visits': encounter_summary.get('total_encounters', 0),
            'last_seen': encounter_summary.get('time_since_last_seen'),
            'common_topics': encounter_summary.get('common_topics', [])[:5]
        }
    }

    return jsonify(result)


@app.route('/api/transcript')
def get_transcript():
    """Get recent transcription"""
    with transcript_lock:
        return jsonify({
            'transcript': transcript_buffer[-10:],  # Last 10 entries
            'full_length': len(full_transcript)
        })


@app.route('/api/auto_enroll', methods=['POST'])
def trigger_auto_enroll():
    """Trigger automatic enrollment of unknown person"""
    result = auto_enroll_person()
    return jsonify(result)


@app.route('/api/people')
def list_people():
    """List all enrolled people"""
    people = person_db.list_all_people(active_only=True)

    # Convert to JSON-safe format
    people_list = []
    for person in people:
        people_list.append({
            'id': person['id'],
            'name': person['name'],
            'relationship': person.get('relationship'),
            'phone': person.get('phone'),
            'first_seen': person.get('first_seen')
        })

    return jsonify({'people': people_list})


@app.route('/api/person/<int:person_id>')
def get_person_details(person_id):
    """Get detailed information for a specific person"""
    person = person_db.get_person(person_id)
    if not person:
        return jsonify({'error': 'Person not found'}), 404

    # Get encounters
    recent_encounters = encounter_db.get_recent_encounters(person_id, limit=10)
    encounter_summary = encounter_db.get_encounter_summary(person_id)

    result = {
        'person': {
            'id': person['id'],
            'name': person['name'],
            'relationship': person.get('relationship'),
            'phone': person.get('phone'),
            'email': person.get('email'),
            'important_info': person.get('important_info'),
            'notes': person.get('notes'),
            'first_seen': person.get('first_seen'),
            'last_updated': person.get('last_updated')
        },
        'statistics': {
            'total_visits': encounter_summary.get('total_encounters', 0),
            'last_seen': encounter_summary.get('time_since_last_seen'),
            'avg_duration': encounter_summary.get('avg_duration'),
            'common_topics': encounter_summary.get('common_topics', [])
        },
        'recent_encounters': recent_encounters
    }

    return jsonify(result)


@app.route('/api/add_person', methods=['POST'])
def add_person():
    """Manually add a new person"""
    data = request.json

    person_id = person_db.add_person(
        name=data['name'],
        relationship=data.get('relationship'),
        phone=data.get('phone'),
        email=data.get('email'),
        important_info=data.get('important_info'),
        notes=data.get('notes')
    )

    return jsonify({'success': True, 'person_id': person_id})


@app.route('/api/update_person/<int:person_id>', methods=['PUT'])
def update_person(person_id):
    """Update person information"""
    data = request.json

    person_db.update_person(person_id, **data)

    return jsonify({'success': True})


@app.route('/api/encounters/today')
def todays_encounters():
    """Get today's encounters"""
    encounters = encounter_db.get_todays_encounters()
    return jsonify({'encounters': encounters})


@app.route('/api/learning_status')
def learning_status():
    """Get current learning status"""
    return jsonify({
        'is_learning': learning_candidate is not None,
        'candidate': learning_candidate,
        'samples_collected': len(unknown_face_samples),
        'samples_needed': 10,
        'ready_to_enroll': learning_candidate is not None and len(unknown_face_samples) >= 10
    })


def run_web_app(host='0.0.0.0', port=5001, db_path='remind.db', whisper_size='tiny'):
    """Run the web application"""
    init_system(db_path, whisper_size)
    print(f"\n🌐 Starting ReMind Web Interface on http://{host}:{port}")
    print("   Features:")
    print("   • Face recognition with auto-learning")
    print("   • Real-time speech transcription")
    print("   • Automatic person enrollment from conversation")
    print(f"   • Whisper model: {whisper_size}")
    # Use threaded=False to avoid dlib threading issues on macOS
    app.run(host=host, port=port, debug=False, threaded=False, processes=1)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ReMind Web Interface with Speech Recognition')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=5001, help='Port number')
    parser.add_argument('--db', default='remind.db', help='Database path')
    parser.add_argument('--whisper', default='tiny', choices=['tiny', 'base', 'small'],
                       help='Whisper model size')

    args = parser.parse_args()
    run_web_app(args.host, args.port, args.db, args.whisper)