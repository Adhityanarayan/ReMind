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


def init_system(db_path="remind.db"):
    """Initialize the ReMind system"""
    global face_recognition, person_db, encounter_db
    face_recognition = FaceRecognitionManager(db_path)
    person_db = PersonDatabase(db_path)
    encounter_db = EncounterDatabase(db_path)


def get_camera():
    """Get camera instance (singleton)"""
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera


def generate_frames():
    """Generate video frames with face recognition"""
    global current_person

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


def run_web_app(host='0.0.0.0', port=5001, db_path='remind.db'):
    """Run the web application"""
    init_system(db_path)
    print(f"\n🌐 Starting ReMind Web Interface on http://{host}:{port}")
    print("   Open in browser to view person information")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ReMind Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=5001, help='Port number')
    parser.add_argument('--db', default='remind.db', help='Database path')

    args = parser.parse_args()
    run_web_app(args.host, args.port, args.db)
