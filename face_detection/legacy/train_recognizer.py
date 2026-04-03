#!/usr/bin/env python3
"""Train an LBPH face recognizer from images saved in `dataset/<label>/*.jpg`.

Usage:
    python train_recognizer.py --data dataset --model face_recognizer.yml

Outputs:
- Trained LBPH model file (YAML)
- labels.json mapping label->id
"""
import argparse
import json
from pathlib import Path
import cv2
import sys
import numpy as np


def load_dataset(data_dir: Path):
    images = []
    labels = []
    label_map = {}
    next_id = 0

    for label_dir in sorted([p for p in data_dir.iterdir() if p.is_dir()]):
        label = label_dir.name
        if label not in label_map:
            label_map[label] = next_id
            next_id += 1
        lid = label_map[label]

        for img_path in sorted(label_dir.glob("*.jpg")):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"Warning: failed to read {img_path}")
                continue
            images.append(img)
            labels.append(lid)

    return images, labels, label_map


def main(data_dir: str, model_path: str, labels_path: str):
    data_dir = Path(data_dir)
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    images, labels, label_map = load_dataset(data_dir)
    if not images:
        print("No training images found. Run collect_faces.py first to gather samples.")
        return

    # ensure cv2.face exists
    if not hasattr(cv2, "face"):
        print("cv2.face is not available. Make sure you installed 'opencv-contrib-python', not 'opencv-python'.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    print(f"Training on {len(images)} images across {len(label_map)} labels")
    labels_array = np.array(labels, dtype=np.int32)
    recognizer.train(images, labels_array)

    recognizer.write(str(model_path))
    with open(labels_path, "w") as f:
        json.dump(label_map, f)

    print(f"Training complete. Model saved to {model_path}")
    print(f"Label map saved to {labels_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LBPH face recognizer from a dataset folder")
    parser.add_argument("--data", default="dataset", help="Dataset folder with subfolders per label (default: dataset)")
    parser.add_argument("--model", default="face_recognizer.yml", help="Output model file path")
    parser.add_argument("--labels", default="labels.json", help="Output labels mapping JSON")
    args = parser.parse_args()
    main(args.data, args.model, args.labels)
