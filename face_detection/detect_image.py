#!/usr/bin/env python3
"""Detect faces in a single image and save annotated output.

Usage:
    python detect_image.py input.jpg -o out.jpg
"""
import argparse
import sys
import cv2


def main():
    parser = argparse.ArgumentParser(description="Detect faces in an image and save annotated output")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("-o", "--output", default="output.jpg", help="Path to save annotated image")
    parser.add_argument("--scale", type=float, default=1.1, help="Scale factor for detectMultiScale")
    parser.add_argument("--minNeighbors", type=int, default=5, help="minNeighbors for detectMultiScale")
    args = parser.parse_args()

    img = cv2.imread(args.input)
    if img is None:
        print(f"Failed to read input image: {args.input}")
        sys.exit(2)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    faces = cascade.detectMultiScale(gray, scaleFactor=args.scale, minNeighbors=args.minNeighbors)

    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imwrite(args.output, img)
    print(f"Detected {len(faces)} faces. Saved annotated image to: {args.output}")


if __name__ == "__main__":
    main()
