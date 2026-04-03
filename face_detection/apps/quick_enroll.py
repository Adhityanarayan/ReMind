#!/usr/bin/env python3
"""
Quick Face Enrollment Script
Simple command-line tool to enroll people into ReMind database
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import argparse
from database import FaceRecognitionManager

def capture_samples(num_samples=15, camera_index=1):
    """Capture face samples from camera"""
    print(f"\n📸 Starting camera to capture {num_samples} samples...")
    print("Position your face in the frame and hold still")
    print("The system will automatically capture samples\n")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("❌ Error: Cannot open camera")
        return None

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    samples = []
    frame_skip = 0

    while len(samples) < num_samples:
        ret, frame = cap.read()
        if not ret:
            break

        # Skip some frames for variety
        frame_skip += 1
        if frame_skip < 10:  # Capture every 10th frame
            cv2.imshow("Face Enrollment - Press 'q' to quit", frame)
            cv2.waitKey(1)
            continue

        frame_skip = 0

        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) > 0:
            # Use largest face
            largest = max(faces, key=lambda r: r[2] * r[3])
            x, y, w, h = largest

            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Add sample
            samples.append(frame.copy())
            print(f"✓ Captured sample {len(samples)}/{num_samples}")

            # Show progress
            progress_text = f"{len(samples)}/{num_samples}"
            cv2.putText(frame, progress_text, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        else:
            # No face detected
            cv2.putText(frame, "No face detected - please face camera",
                       (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Face Enrollment - Press 'q' to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n⚠️  Enrollment cancelled by user")
            cap.release()
            cv2.destroyAllWindows()
            return None

    cap.release()
    cv2.destroyAllWindows()

    print(f"\n✅ Successfully captured {len(samples)} samples!")
    return samples


def main():
    parser = argparse.ArgumentParser(
        description='Quick face enrollment for ReMind database'
    )
    parser.add_argument('--name', required=True, help='Person\'s full name')
    parser.add_argument('--relationship', default='', help='Relationship (e.g., Daughter, Nurse)')
    parser.add_argument('--phone', default='', help='Phone number')
    parser.add_argument('--email', default='', help='Email address')
    parser.add_argument('--info', default='', help='Important information')
    parser.add_argument('--notes', default='', help='Additional notes')
    parser.add_argument('--samples', type=int, default=15, help='Number of samples to capture')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    parser.add_argument('--db', default='remind.db', help='Database path')

    args = parser.parse_args()

    print("\n" + "="*60)
    print("🧠 ReMind - Quick Face Enrollment")
    print("="*60)
    print(f"Enrolling: {args.name}")
    if args.relationship:
        print(f"Relationship: {args.relationship}")
    print("="*60)

    # Capture face samples
    samples = capture_samples(args.samples, args.camera)

    if samples is None or len(samples) == 0:
        print("❌ No samples captured. Enrollment failed.")
        return

    if len(samples) < 10:
        print(f"⚠️  Warning: Only captured {len(samples)} samples.")
        print("   Recommended: at least 10 samples for good accuracy")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Enrollment cancelled.")
            return

    # Enroll in database
    print("\n💾 Enrolling in database...")
    face_mgr = FaceRecognitionManager(args.db)

    person_id = face_mgr.enroll_person(
        frames=samples,
        name=args.name,
        relationship=args.relationship if args.relationship else None,
        phone=args.phone if args.phone else None,
        email=args.email if args.email else None,
        important_info=args.info if args.info else None,
        notes=args.notes if args.notes else None
    )

    if person_id:
        print("\n" + "="*60)
        print("✅ ENROLLMENT SUCCESSFUL!")
        print("="*60)
        print(f"Person ID: {person_id}")
        print(f"Name: {args.name}")
        if args.relationship:
            print(f"Relationship: {args.relationship}")
        print("\n💡 This person will now be recognized automatically!")
        print("   Start the ReMind assistant or web app to test recognition.")
        print("="*60 + "\n")
    else:
        print("\n❌ Enrollment failed. Please check the error messages above.")

    face_mgr.close()


if __name__ == '__main__':
    main()
