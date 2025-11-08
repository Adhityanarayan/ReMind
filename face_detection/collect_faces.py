#!/usr/bin/env python3
"""Collect face samples from webcam for a given person label.

Usage:
    python collect_faces.py --name "alice" --samples 40

This will create dataset/alice/ with captured grayscale face images.
"""
import argparse
import os
from pathlib import Path
import cv2


def main(name: str, samples: int, out_dir: str, camera: int):
    out_path = Path(out_dir) / name
    out_path.mkdir(parents=True, exist_ok=True)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        print(f"Cannot open camera index {camera}")
        return

    count = len(list(out_path.glob("*.jpg")))
    print(f"Starting capture for '{name}'. Existing samples: {count}")
    print("Press 'q' to quit early")

    while count < samples:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read from camera")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            face_img = gray[y : y + h, x : x + w]
            face_resized = cv2.resize(face_img, (200, 200))
            filename = out_path / f"{count:04d}.jpg"
            cv2.imwrite(str(filename), face_resized)
            count += 1
            print(f"Saved {filename}")

            # Draw rectangle and show progress
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{count}/{samples}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        cv2.imshow("Collect Faces", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Finished. Collected {count} samples for '{name}' in {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect face samples for a person label")
    parser.add_argument("--name", required=True, help="Label/name for the person (used as folder name)")
    parser.add_argument("--samples", type=int, default=40, help="Number of samples to capture (default 40)")
    parser.add_argument("--out", default="dataset", help="Output dataset directory (default: dataset)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default 0)")
    args = parser.parse_args()
    main(args.name, args.samples, args.out, args.camera)
