#!/usr/bin/env python3
"""Test if dlib/face_recognition works in threaded context"""
import threading
import cv2
import face_recognition

def test_face_recognition():
    """Test face recognition in thread"""
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        ret, frame = cap.read()
        if ret:
            print("Frame captured successfully")
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            print("Converted to RGB")

            # This is likely where it crashes
            face_locations = face_recognition.face_locations(rgb_frame)
            print(f"Found {len(face_locations)} faces")
        cap.release()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

print("Testing face_recognition in main thread...")
test_face_recognition()

print("\nTesting face_recognition in background thread...")
thread = threading.Thread(target=test_face_recognition)
thread.start()
thread.join()

print("Done!")