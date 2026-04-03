#!/usr/bin/env python3
"""Minimal test - video feed only, no audio"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, Response
import cv2
import threading

app = Flask(__name__)
camera = None
camera_lock = threading.Lock()

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        if not camera.isOpened():
            camera = cv2.VideoCapture(0)
    return camera

def generate_frames():
    camera = get_camera()
    print("📹 Starting video stream...")

    while True:
        try:
            with camera_lock:
                success, frame = camera.read()
                if not success:
                    print("Failed to read frame")
                    break

            # Just encode and send - no face detection
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            break

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Starting minimal video test...")
    camera = get_camera()
    if camera.isOpened():
        print("✅ Camera OK")
    else:
        print("❌ Camera failed")

    app.run(host='0.0.0.0', port=5002, debug=False, threaded=False)