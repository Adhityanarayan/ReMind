# Live Audio Transcription with Whisper

Real-time speech-to-text transcription using OpenAI's Whisper model.

## Features

- **Real-time transcription** from microphone input
- **Multiple Whisper models** (tiny to large)
- **Multi-language support** with auto-detection
- **File output** in TXT, JSON, or SRT subtitle format
- **Energy-based filtering** to ignore silence
- **Configurable chunk duration** for optimal performance
- **Live statistics** showing words per minute

## Installation

### 1. Install System Dependencies

**macOS:**
```bash
brew install portaudio ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev ffmpeg
```

**Windows:**
- Download and install [FFmpeg](https://ffmpeg.org/download.html)
- PyAudio will install automatically

### 2. Install Python Dependencies

```bash
# Activate your virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

This will install:
- `openai-whisper` - OpenAI's Whisper speech recognition
- `sounddevice` - Audio capture library
- `pyaudio` - Alternative audio library
- `scipy` - Audio processing utilities

### 3. First Run (Model Download)

The first time you run transcription, Whisper will download the model (~150MB for base model):

```bash
python live_transcribe.py --model base
```

## Usage

### Basic Live Transcription

Simple real-time transcription to console:

```bash
python live_transcribe.py
```

### List Available Microphones

```bash
python live_transcribe.py --list-devices
```

Output:
```
Available audio input devices:
------------------------------------------------------------
0: MacBook Pro Microphone
   Channels: 1, Sample rate: 48000.0 Hz
1: External USB Microphone
   Channels: 2, Sample rate: 44100.0 Hz
------------------------------------------------------------
```

### Select Specific Microphone

```bash
python live_transcribe.py --device 1
```

### Choose Whisper Model

Models (accuracy vs speed):
- `tiny` - Fastest, least accurate (~39M params, ~1GB RAM)
- `base` - Good balance (default, ~74M params, ~1GB RAM)
- `small` - Better accuracy (~244M params, ~2GB RAM)
- `medium` - High accuracy (~769M params, ~5GB RAM)
- `large` - Best accuracy (~1550M params, ~10GB RAM)

```bash
# Fast transcription with tiny model
python live_transcribe.py --model tiny

# Accurate transcription with small model
python live_transcribe.py --model small
```

### Multi-language Support

```bash
# Transcribe Spanish
python live_transcribe.py --language es

# Transcribe French
python live_transcribe.py --language fr

# Auto-detect language
python live_transcribe.py --language auto
```

### Adjust Sensitivity

```bash
# More sensitive (transcribe quieter audio)
python live_transcribe.py --energy-threshold 0.005

# Less sensitive (ignore background noise)
python live_transcribe.py --energy-threshold 0.02
```

### Change Chunk Duration

```bash
# Faster updates (2 second chunks)
python live_transcribe.py --chunk-duration 2

# More context (10 second chunks)
python live_transcribe.py --chunk-duration 10
```

## Saving Transcriptions

### Save to Text File

```bash
python save_transcription.py --output transcript.txt
```

Output format:
```
Transcription started: 2025-01-08 10:30:00
================================================================================

[2025-01-08 10:30:05] Hello, this is a test of the transcription system.
[2025-01-08 10:30:10] It works really well for real-time speech to text.

Transcription ended: 2025-01-08 10:31:00
```

### Save as JSON

```bash
python save_transcription.py --output transcript.json --format json
```

Output format:
```json
[
  {
    "segment": 0,
    "timestamp": "2025-01-08T10:30:05.123456",
    "text": "Hello, this is a test of the transcription system.",
    "language": "en",
    "energy": 0.0234
  },
  {
    "segment": 1,
    "timestamp": "2025-01-08T10:30:10.654321",
    "text": "It works really well for real-time speech to text.",
    "language": "en",
    "energy": 0.0189
  }
]
```

### Save as SRT Subtitles

```bash
python save_transcription.py --output transcript.srt --format srt
```

Output format:
```srt
1
00:00:00,000 --> 00:00:05,000
Hello, this is a test of the transcription system.

2
00:00:05,000 --> 00:00:10,000
It works really well for real-time speech to text.
```

### Auto-generated Filenames

If you specify a format without an output file, it auto-generates a timestamped filename:

```bash
python save_transcription.py --format json
# Creates: transcription_20250108_103045.json
```

## Advanced Usage

### High-Quality Multilingual Recording

```bash
python save_transcription.py \
  --model medium \
  --language auto \
  --chunk-duration 3 \
  --energy-threshold 0.01 \
  --output meeting_notes.txt \
  --format txt
```

### Fast Dictation Mode

```bash
python live_transcribe.py \
  --model tiny \
  --chunk-duration 2 \
  --energy-threshold 0.015
```

### Meeting Transcription with Subtitles

```bash
python save_transcription.py \
  --model small \
  --chunk-duration 5 \
  --output meeting.srt \
  --format srt
```

## Tips for Best Results

### Audio Quality
- Use a good quality microphone
- Minimize background noise
- Speak clearly and at moderate pace
- Position microphone 6-12 inches from mouth

### Model Selection
- **For real-time applications**: Use `tiny` or `base`
- **For accuracy**: Use `small` or `medium`
- **For production quality**: Use `medium` or `large`

### Performance Optimization
- Shorter chunks (2-3s) = faster but less context
- Longer chunks (8-10s) = slower but more accurate
- Adjust energy threshold to filter background noise
- Use GPU if available (Whisper automatically uses CUDA)

### Language Detection
- Specify language for better accuracy (`--language en`)
- Use `auto` only when language might change
- Auto-detection adds slight latency

## Troubleshooting

### "No module named whisper"
```bash
pip install openai-whisper
```

### "PortAudio library not found"
**macOS:**
```bash
brew install portaudio
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev
```

### "No audio detected"
1. Check microphone is connected and working
2. List devices: `python live_transcribe.py --list-devices`
3. Select correct device: `--device X`
4. Lower energy threshold: `--energy-threshold 0.005`
5. Test microphone in system settings

### "Transcription is slow"
1. Use smaller model: `--model tiny` or `--model base`
2. Reduce chunk duration: `--chunk-duration 3`
3. Close other applications
4. Check CPU/RAM usage

### "Inaccurate transcriptions"
1. Use larger model: `--model small` or `--model medium`
2. Improve audio quality (better mic, less noise)
3. Increase chunk duration: `--chunk-duration 8`
4. Specify language: `--language en` instead of auto

### "Permission denied" for microphone
**macOS:**
- Go to System Preferences → Security & Privacy → Microphone
- Enable Terminal (or your IDE)

**Linux:**
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
```

## Integration Ideas

### With Face Recognition
Combine transcription with face recognition for:
- Meeting notes with speaker identification
- Voice-activated photo search
- Accessibility features (audio descriptions)

Example integration:
```python
# Pseudo-code
from live_transcribe import LiveTranscriber
from recognize import FaceRecognizer

# Simultaneous transcription and face recognition
# "John said: 'Hello everyone' at 10:30 AM"
```

### Voice Commands
Use transcription for voice control:
```python
if "take photo" in transcription_text:
    capture_face_sample()
```

### Real-time Subtitles
Add subtitles to video recordings:
```python
# Use SRT output with video editing tools
python save_transcription.py --format srt --output video_subs.srt
```

## Performance Benchmarks

Approximate real-time factors (RTF) on M1 MacBook Pro:
- **tiny**: 0.1x (10x faster than real-time)
- **base**: 0.2x (5x faster)
- **small**: 0.5x (2x faster)
- **medium**: 1.0x (real-time)
- **large**: 2.0x (2x slower)

RTF < 1.0 = can process faster than real-time
RTF > 1.0 = lags behind real-time

## API Reference

### LiveTranscriber Class

```python
from live_transcribe import LiveTranscriber

transcriber = LiveTranscriber(
    model_name="base",           # Whisper model
    language="en",               # Language code
    sample_rate=16000,           # Audio sample rate
    chunk_duration=5,            # Seconds per chunk
    energy_threshold=0.01        # Silence threshold
)

transcriber.start()  # Start transcription
transcriber.stop()   # Stop transcription
```

### TranscriptionRecorder Class

```python
from save_transcription import TranscriptionRecorder

recorder = TranscriptionRecorder(
    model_name="base",
    language="en",
    output_file="transcript.txt",
    output_format="txt"          # txt, json, or srt
)

recorder.start()
```

## License

Same as main ReMind project (MIT License).

## Credits

- OpenAI Whisper: https://github.com/openai/whisper
- Sound device library: https://python-sounddevice.readthedocs.io/