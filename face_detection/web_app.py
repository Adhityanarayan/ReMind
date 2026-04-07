#!/usr/bin/env python3
"""
ReMind Web Interface
Flask web app for displaying person information and managing the ReMind system
"""

from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
import cv2
import json
import threading
import numpy as np
import queue
import time
from datetime import datetime
from typing import Optional

import sounddevice as sd
import whisper
from database import PersonDatabase, EncounterDatabase, FaceRecognitionManager

app = Flask(__name__)
CORS(app)

# Global state
camera = None
face_recognition = None
person_db = None
encounter_db = None
current_person = None
camera_lock = threading.Lock()

# Audio + transcription state
audio_queue = queue.Queue()
audio_thread = None
audio_stream = None
whisper_model = None
sample_rate = 16000
chunk_duration_sec = 4
chunk_samples = int(sample_rate * chunk_duration_sec)
energy_threshold = 0.01
transcript_lock = threading.Lock()
last_transcription = ""
last_transcription_ts = None

# Encounter state (single active encounter for this web runtime)
encounter_lock = threading.Lock()
current_encounter_id = None

# Enrollment state (server-camera based)
enroll_lock = threading.Lock()
enroll_active = False
enroll_ready = False
enroll_error = None
enroll_target_samples = 15
enroll_samples = []
enroll_every_n_frames = 10
enroll_frame_counter = 0
enroll_metadata = {
    "name": "",
    "relationship": "",
    "important_info": "",
    "phone": "",
    "email": "",
    "notes": "",
}
enroll_started_ts = None


def init_system(db_path="remind.db", whisper_model_name: str = "tiny"):
    """Initialize the ReMind system"""
    global face_recognition, person_db, encounter_db, whisper_model, current_encounter_id
    face_recognition = FaceRecognitionManager(db_path, tolerance=0.6)
    person_db = PersonDatabase(db_path)
    encounter_db = EncounterDatabase(db_path)
    whisper_model = whisper.load_model(whisper_model_name)

    # Start one encounter for this session (we attribute person_id as recognition changes)
    with encounter_lock:
        current_encounter_id = encounter_db.start_encounter()


def get_camera():
    """Get camera instance (singleton)"""
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera


def _audio_callback(indata, frames, time_info, status):
    if status:
        # Avoid noisy printing; just enqueue audio
        pass
    audio_queue.put(indata.copy())


def _process_audio_forever():
    global last_transcription, last_transcription_ts

    audio_buffer = np.array([], dtype=np.float32)
    while True:
        chunk = audio_queue.get()
        if chunk is None:
            break

        try:
            audio_buffer = np.concatenate([audio_buffer, chunk.flatten()])

            while len(audio_buffer) >= chunk_samples:
                chunk_to_process = audio_buffer[:chunk_samples]
                audio_buffer = audio_buffer[chunk_samples:]

                audio_float = chunk_to_process.astype(np.float32)
                energy = float(np.sqrt(np.mean(audio_float ** 2)))
                if energy <= energy_threshold:
                    continue

                result = whisper_model.transcribe(
                    audio_float,
                    language="en",
                    fp16=False,
                    verbose=False,
                )
                text = (result.get("text") or "").strip()
                if not text:
                    continue

                now = datetime.now()
                with transcript_lock:
                    last_transcription = text
                    last_transcription_ts = now.isoformat()

                # Persist transcript chunk into active encounter (if any)
                with encounter_lock:
                    if current_encounter_id:
                        encounter_db.add_transcript_chunk(current_encounter_id, text)
        except Exception:
            # Keep background thread alive even if transcription errors happen
            continue


def start_audio_transcription():
    """Start mic capture + Whisper transcription (singleton)."""
    global audio_thread, audio_stream
    if audio_thread is not None and audio_thread.is_alive():
        return

    audio_thread = threading.Thread(target=_process_audio_forever, daemon=True)
    audio_thread.start()

    audio_stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        callback=_audio_callback,
        blocksize=int(sample_rate * 0.5),
    )
    audio_stream.start()


def _maybe_update_encounter_person(person: Optional[dict]):
    """When recognition finds a known person, associate encounter with person_id."""
    if not person or not person.get("id"):
        return

    with encounter_lock:
        if not current_encounter_id:
            return
        try:
            encounter_db.update_encounter(current_encounter_id, person_id=person["id"])
        except Exception:
            return


def _enroll_reset():
    global enroll_active, enroll_ready, enroll_error, enroll_samples, enroll_frame_counter, enroll_started_ts
    enroll_active = False
    enroll_ready = False
    enroll_error = None
    enroll_samples = []
    enroll_frame_counter = 0
    enroll_started_ts = None


def generate_frames():
    """Generate video frames with face recognition"""
    global current_person, enroll_frame_counter

    camera = get_camera()

    while True:
        with camera_lock:
            success, frame = camera.read()
            if not success:
                break

            # Perform face recognition
            person = face_recognition.recognize_face(frame)

            if person and person.get('id'):
                current_person = person
                _maybe_update_encounter_person(person)

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
                current_person = None
                # Still draw face box for unknown faces
                faces = face_recognition.detect_faces(frame)
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            # Enrollment sampling (capture from the same server camera feed)
            with enroll_lock:
                if enroll_active and not enroll_ready and enroll_error is None:
                    enroll_frame_counter += 1
                    if enroll_frame_counter % enroll_every_n_frames == 0:
                        if len(enroll_samples) < int(enroll_target_samples):
                            if len(face_recognition.detect_faces(frame)) > 0:
                                enroll_samples.append(frame.copy())
                        if len(enroll_samples) >= int(enroll_target_samples):
                            enroll_ready = True

                # Draw enrollment status overlay
                if enroll_active:
                    banner_h = 40
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (frame.shape[1], banner_h), (0, 90, 200), -1)
                    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

                    status = f"ENROLL: {len(enroll_samples)}/{int(enroll_target_samples)}"
                    if enroll_ready:
                        status += " (ready to save)"
                    if enroll_error:
                        status = f"ENROLL ERROR: {enroll_error}"
                    cv2.putText(frame, status, (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


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
    """Add a new person (without face for now)"""
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


@app.route('/api/transcript')
def get_transcript():
    """Get latest transcription text from server mic."""
    with transcript_lock:
        text = last_transcription
        ts = last_transcription_ts
    return jsonify({"text": text, "timestamp": ts})


@app.route('/api/enroll/status')
def enroll_status():
    with enroll_lock:
        return jsonify({
            "active": enroll_active,
            "ready": enroll_ready,
            "error": enroll_error,
            "target_samples": int(enroll_target_samples),
            "samples_captured": len(enroll_samples),
            "metadata": enroll_metadata if enroll_active else None,
            "started_at": enroll_started_ts,
        })


@app.route('/api/enroll/start', methods=['POST'])
def enroll_start():
    """Start server-side enrollment using the live server camera feed."""
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "name is required"}), 400

    with enroll_lock:
        _enroll_reset()
        enroll_metadata.update({
            "name": name,
            "relationship": (data.get("relationship") or "").strip(),
            "important_info": (data.get("important_info") or "").strip(),
            "phone": (data.get("phone") or "").strip(),
            "email": (data.get("email") or "").strip(),
            "notes": (data.get("notes") or "").strip(),
        })
        global enroll_target_samples, enroll_active, enroll_started_ts
        enroll_target_samples = int(data.get("samples") or 15)
        enroll_active = True
        enroll_started_ts = datetime.now().isoformat()

    return jsonify({"success": True})


@app.route('/api/enroll/cancel', methods=['POST'])
def enroll_cancel():
    with enroll_lock:
        _enroll_reset()
    return jsonify({"success": True})


@app.route('/api/enroll/complete', methods=['POST'])
def enroll_complete():
    """Persist captured samples as a new person in the database."""
    global enroll_error
    with enroll_lock:
        if not enroll_active:
            return jsonify({"success": False, "error": "enrollment not active"}), 400
        if enroll_error:
            return jsonify({"success": False, "error": enroll_error}), 400
        if not enroll_ready and len(enroll_samples) < 10:
            return jsonify({"success": False, "error": "need at least 10 samples"}), 400

        frames = list(enroll_samples)
        meta = dict(enroll_metadata)

    try:
        person_id = face_recognition.enroll_person(
            frames=frames,
            name=meta["name"],
            relationship=meta["relationship"] or None,
            phone=meta["phone"] or None,
            email=meta["email"] or None,
            important_info=meta["important_info"] or None,
            notes=meta["notes"] or None,
        )
    except Exception as e:
        with enroll_lock:
            enroll_error = str(e)
        return jsonify({"success": False, "error": str(e)}), 500

    with enroll_lock:
        _enroll_reset()

    return jsonify({"success": True, "person_id": person_id})


def run_web_app(host='0.0.0.0', port=5001, db_path='remind.db', whisper_model_name: str = "tiny"):
    """Run the web application"""
    init_system(db_path, whisper_model_name=whisper_model_name)
    start_audio_transcription()
    print(f"\n🌐 Starting ReMind Web Interface on http://{host}:{port}")
    print("   Open in browser to view person information")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ReMind Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=5001, help='Port number')
    parser.add_argument('--db', default='remind.db', help='Database path')
    parser.add_argument('--model', default='tiny', choices=['tiny', 'base', 'small'], help='Whisper model')

    args = parser.parse_args()
    run_web_app(args.host, args.port, args.db, args.model)
