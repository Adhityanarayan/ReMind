#!/usr/bin/env python3
"""Recognize faces from webcam or an input image using a trained LBPH model.

Usage:
    python recognize.py --model face_recognizer.yml --labels labels.json
    python recognize.py --image test.jpg --model face_recognizer.yml --labels labels.json

If no image is passed, uses webcam (camera index 0).
"""
import argparse
import json
from pathlib import Path
import cv2
import sys


def load_recognizer(model_path: Path):
    if not model_path.exists():
        print(f"Model file not found: {model_path}")
        return None
    if not hasattr(cv2, "face"):
        print("cv2.face is not available. Install 'opencv-contrib-python'.")
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(model_path))
    return recognizer


def main(model: str, labels: str, image: str, camera: int):
    model_path = Path(model)
    labels_path = Path(labels)

    recognizer = load_recognizer(model_path)
    if recognizer is None:
        return

    if not labels_path.exists():
        print(f"Labels file not found: {labels_path}")
        return
    with open(labels_path, "r") as f:
        label_map = json.load(f)
    inv_map = {int(v): k for k, v in label_map.items()}

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    def process_frame(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi_resized = cv2.resize(roi, (200, 200))
            try:
                label_id, confidence = recognizer.predict(roi_resized)
            except Exception as e:
                print("Prediction error:", e)
                continue
            name = inv_map.get(int(label_id), str(label_id))
            text = f"{name} ({confidence:.1f})"
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
            cv2.putText(frame, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        return frame

    if image:
        img_path = Path(image)
        if not img_path.exists():
            print(f"Image not found: {img_path}")
            return
        frame = cv2.imread(str(img_path))
        out = process_frame(frame)
        cv2.imshow("Recognition", out)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        cap = cv2.VideoCapture(camera)
        if not cap.isOpened():
            print(f"Cannot open camera index {camera}")
            return
        print("Press 'q' to quit")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out = process_frame(frame)
            cv2.imshow("Recognition", out)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recognize faces using LBPH model")
    parser.add_argument("--model", default="face_recognizer.yml", help="Path to trained model file")
    parser.add_argument("--labels", default="labels.json", help="Path to labels mapping JSON")
    parser.add_argument("--image", default=None, help="Optional image path to run recognition on (if omitted, uses webcam)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index for live recognition")
    args = parser.parse_args()
    main(args.model, args.labels, args.image, args.camera)
