#!/usr/bin/env python3
"""Test camera access to debug segfault issues"""
import cv2
import sys

print("Testing camera access...")
print(f"OpenCV version: {cv2.__version__}")

# Try different camera indices
for idx in range(3):
    print(f"\nTrying camera index {idx}...")
    try:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ Camera {idx} works! Frame shape: {frame.shape}")
                cap.release()
            else:
                print(f"❌ Camera {idx} opened but couldn't read frame")
                cap.release()
        else:
            print(f"❌ Camera {idx} could not be opened")
    except Exception as e:
        print(f"❌ Camera {idx} error: {e}")

print("\n" + "="*50)
print("Testing with AVFoundation backend (macOS)...")
try:
    cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ AVFoundation backend works! Frame shape: {frame.shape}")
        else:
            print("❌ AVFoundation opened but couldn't read frame")
        cap.release()
    else:
        print("❌ AVFoundation backend could not open camera")
except Exception as e:
    print(f"❌ AVFoundation backend error: {e}")

print("\nDone!")