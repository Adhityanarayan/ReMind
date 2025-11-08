# ReMind - Face Recognition & Live Transcription

A complete AI-powered toolkit for face recognition and speech transcription using OpenCV and Whisper.

## Features

### Face Detection & Recognition
- Face detection in images and real-time video
- Train custom face recognition models
- Identify people from webcam or photos
- LBPH-based recognition with confidence scoring

### Live Audio Transcription (NEW!)
- Real-time speech-to-text using OpenAI Whisper
- Multiple language support (90+ languages)
- Save transcriptions to TXT, JSON, or SRT subtitle format
- Configurable models (tiny to large) for speed vs accuracy
- Energy-based filtering to ignore silence

## Quick Links

- **Face Detection:** [detect_image.py](detect_image.py), [detect_camera.py](detect_camera.py)
- **Face Recognition:** [recognize.py](recognize.py)
- **Live Transcription:** [live_transcribe.py](live_transcribe.py), [save_transcription.py](save_transcription.py)
- **Documentation:** [Transcription Guide](QUICKSTART_TRANSCRIPTION.md), [Full Transcription Docs](TRANSCRIPTION_README.md)

Requirements
- Python 3.8+ (3.11 recommended)
- See `requirements.txt` for Python packages.

Quick start (recommended inside a virtualenv)

```bash
# from the repo root
cd face_detection
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# detect faces in an image
python detect_image.py /path/to/photo.jpg -o annotated.jpg

# or run live detection from your webcam (press 'q' to quit)
python detect_camera.py

# NEW: Live transcription from microphone
python live_transcribe.py

# Save transcription to file
python save_transcription.py --output notes.txt
```

## Usage Examples

### Face Recognition
```bash
# Collect face samples for training
python collect_faces.py

# Train the recognition model
python train_recognizer.py

# Recognize faces from webcam
python recognize.py
```

### Live Transcription
```bash
# Basic transcription (console output)
python live_transcribe.py

# Save to text file
python save_transcription.py --output meeting_notes.txt

# Fast transcription with tiny model
python live_transcribe.py --model tiny --chunk-duration 2

# High accuracy with small model
python live_transcribe.py --model small

# Multilingual (Spanish)
python live_transcribe.py --language es

# Save as JSON or SRT subtitles
python save_transcription.py --format json --output transcript.json
python save_transcription.py --format srt --output video.srt
```

See [QUICKSTART_TRANSCRIPTION.md](QUICKSTART_TRANSCRIPTION.md) for detailed transcription guide.
```

Notes
- The scripts use OpenCV's bundled Haar cascade at `cv2.data.haarcascades` so you don't need to download XML files manually.
- If your webcam index is not `0`, pass a different index by editing `detect_camera.py` or set `cv2.VideoCapture(1)` etc.

Troubleshooting
- If camera window doesn't open on macOS, ensure your terminal app has Camera permission in System Settings → Privacy & Security.
- If `import cv2` fails, ensure you're in the virtualenv and `pip install -r requirements.txt` completed without errors.
