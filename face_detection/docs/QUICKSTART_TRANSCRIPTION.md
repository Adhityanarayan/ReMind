# Quick Start: Live Transcription

## What's Been Set Up

You now have **OpenAI Whisper live transcription** integrated into your ReMind project!

## Available Scripts

1. **[live_transcribe.py](live_transcribe.py)** - Basic real-time transcription to console
2. **[save_transcription.py](save_transcription.py)** - Enhanced version with file output (TXT/JSON/SRT)

## Your Audio Devices

```
0: Adhi's iPhone Microphone (48000 Hz)
1: MacBook Air Microphone (48000 Hz)
```

## Try It Now!

### 1. Basic Transcription (Console Only)

```bash
# Activate virtual environment
source ../.venv/bin/activate

# Start transcription with default settings
python live_transcribe.py
```

**What happens:**
- Loads Whisper "base" model (first run downloads ~150MB)
- Starts listening to your default microphone
- Transcribes speech every 5 seconds
- Displays results in real-time
- Press `Ctrl+C` to stop

### 2. Fast Transcription (Tiny Model)

For quicker, more responsive transcription:

```bash
python live_transcribe.py --model tiny --chunk-duration 2
```

### 3. Accurate Transcription (Small Model)

For better accuracy:

```bash
python live_transcribe.py --model small
```

### 4. Save to File

```bash
# Save as text file
python save_transcription.py --output my_notes.txt

# Save as JSON (structured data)
python save_transcription.py --output transcript.json --format json

# Save as SRT subtitles
python save_transcription.py --output video_subs.srt --format srt
```

### 5. Use Specific Microphone

```bash
# Use iPhone microphone
python live_transcribe.py --device 0

# Use MacBook microphone
python live_transcribe.py --device 1
```

## Example Output

When you speak, you'll see:

```
============================================================
LIVE TRANSCRIPTION STARTED
============================================================
Speak into your microphone...
Press Ctrl+C to stop
============================================================

[10:45:32] (en, Energy: 0.0234)
>>> Hello, this is a test of the Whisper transcription system.
------------------------------------------------------------

[10:45:37] (en, Energy: 0.0189)
>>> It works really well for converting speech to text in real time.
------------------------------------------------------------
```

## Common Use Cases

### Meeting Notes
```bash
python save_transcription.py \
  --model small \
  --output meeting_$(date +%Y%m%d).txt
```

### Quick Dictation
```bash
python live_transcribe.py --model tiny --chunk-duration 2
```

### Video Subtitles
```bash
python save_transcription.py \
  --format srt \
  --output video.srt
```

### Multilingual Support
```bash
# Spanish
python live_transcribe.py --language es

# Auto-detect language
python live_transcribe.py --language auto
```

## Model Comparison

| Model  | Speed      | Accuracy | RAM   | Best For                |
|--------|------------|----------|-------|-------------------------|
| tiny   | 10x faster | Good     | ~1GB  | Real-time, quick notes  |
| base   | 5x faster  | Better   | ~1GB  | Default, balanced       |
| small  | 2x faster  | High     | ~2GB  | Accurate transcription  |
| medium | 1x (RT)    | Higher   | ~5GB  | Professional use        |
| large  | 0.5x       | Best     | ~10GB | Maximum accuracy        |

## Tips

**For best results:**
- Speak clearly and at moderate pace
- Use a good quality microphone
- Minimize background noise
- Adjust `--energy-threshold` if picking up too much/little

**Performance:**
- Shorter `--chunk-duration` = faster updates, less context
- Longer `--chunk-duration` = more accurate, more latency

**Languages supported:**
English (en), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt),
Dutch (nl), Russian (ru), Chinese (zh), Japanese (ja), Korean (ko), and 90+ more!

## Integration with Face Recognition

You can combine transcription with face recognition for powerful applications:

```python
# Example: Voice-activated face detection
if "recognize face" in transcription_text:
    run_face_recognition()

# Example: Meeting notes with speaker ID
transcript = f"{recognized_face_name}: {transcription_text}"
```

## Troubleshooting

**No audio detected:**
```bash
# Lower the threshold
python live_transcribe.py --energy-threshold 0.005
```

**Too slow:**
```bash
# Use faster model
python live_transcribe.py --model tiny
```

**Inaccurate:**
```bash
# Use better model
python live_transcribe.py --model small
```

**Wrong microphone:**
```bash
# List devices first
python live_transcribe.py --list-devices

# Then select
python live_transcribe.py --device 1
```

## Full Documentation

See [TRANSCRIPTION_README.md](TRANSCRIPTION_README.md) for complete documentation.

## What's Next?

Now that you have transcription working, you could:

1. **Combine with face recognition** - Identify who's speaking
2. **Add voice commands** - Control your app with voice
3. **Create a web interface** - Browser-based transcription
4. **Build a meeting assistant** - Auto-summarize discussions
5. **Add translation** - Real-time language translation

Let me know what you'd like to build next!