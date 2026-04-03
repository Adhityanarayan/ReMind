#!/usr/bin/env python3
"""
Live Transcription using OpenAI Whisper
Real-time audio capture and transcription from microphone
"""

import whisper
import sounddevice as sd
import numpy as np
import queue
import threading
import argparse
from datetime import datetime
import sys
import time


class LiveTranscriber:
    """Real-time audio transcription using Whisper"""

    def __init__(self, model_name="base", language="en", sample_rate=16000,
                 chunk_duration=5, energy_threshold=0.01):
        """
        Initialize the live transcriber

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            language: Language code (en, es, fr, etc.) or None for auto-detect
            sample_rate: Audio sample rate in Hz (16000 is optimal for Whisper)
            chunk_duration: Duration of audio chunks to transcribe (seconds)
            energy_threshold: Minimum audio energy to process (0-1)
        """
        print(f"Loading Whisper {model_name} model...")
        self.model = whisper.load_model(model_name)
        self.language = language
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.energy_threshold = energy_threshold

        # Audio buffer
        self.audio_queue = queue.Queue()
        self.is_running = False

        print(f"Model loaded! Ready to transcribe.")
        print(f"Settings: {model_name} model, {chunk_duration}s chunks, {sample_rate}Hz")

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream"""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)

        # Add audio data to queue
        self.audio_queue.put(indata.copy())

    def calculate_energy(self, audio_data):
        """Calculate audio energy (RMS)"""
        return np.sqrt(np.mean(audio_data**2))

    def transcribe_chunk(self, audio_data):
        """Transcribe a chunk of audio"""
        # Flatten and convert to float32
        audio = audio_data.flatten().astype(np.float32)

        # Check audio energy
        energy = self.calculate_energy(audio)

        if energy < self.energy_threshold:
            return None, energy

        # Transcribe using Whisper
        result = self.model.transcribe(
            audio,
            language=self.language,
            fp16=False,
            task='transcribe'
        )

        return result['text'].strip(), energy

    def process_audio(self):
        """Process audio from queue and transcribe"""
        audio_buffer = np.array([], dtype=np.float32)

        while self.is_running:
            try:
                # Get audio chunk from queue
                chunk = self.audio_queue.get(timeout=0.1)
                audio_buffer = np.concatenate([audio_buffer, chunk.flatten()])

                # When we have enough audio, transcribe it
                if len(audio_buffer) >= self.chunk_samples:
                    # Extract chunk
                    chunk_to_process = audio_buffer[:self.chunk_samples]
                    audio_buffer = audio_buffer[self.chunk_samples:]

                    # Transcribe
                    text, energy = self.transcribe_chunk(chunk_to_process)

                    if text:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[{timestamp}] (Energy: {energy:.4f})")
                        print(f">>> {text}")
                        print("-" * 60)

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error processing audio: {e}", file=sys.stderr)

    def start(self):
        """Start live transcription"""
        print("\n" + "=" * 60)
        print("LIVE TRANSCRIPTION STARTED")
        print("=" * 60)
        print(f"Speak into your microphone...")
        print(f"Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        self.is_running = True

        # Start processing thread
        processing_thread = threading.Thread(target=self.process_audio)
        processing_thread.start()

        # Start audio stream
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self.audio_callback,
                blocksize=int(self.sample_rate * 0.5)  # 0.5 second blocks
            ):
                while self.is_running:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping transcription...")
        finally:
            self.stop()
            processing_thread.join()

    def stop(self):
        """Stop transcription"""
        self.is_running = False
        print("\nTranscription stopped.")


def list_audio_devices():
    """List available audio input devices"""
    print("\nAvailable audio input devices:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"{i}: {device['name']}")
            print(f"   Channels: {device['max_input_channels']}, "
                  f"Sample rate: {device['default_samplerate']} Hz")
    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Live audio transcription using OpenAI Whisper"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base). Larger = more accurate but slower"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code (en, es, fr, etc.) or 'auto' for auto-detection (default: en)"
    )
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=5.0,
        help="Duration of audio chunks to transcribe in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--energy-threshold",
        type=float,
        default=0.01,
        help="Minimum audio energy to process (0-1, default: 0.01)"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device ID (use --list-devices to see options)"
    )

    args = parser.parse_args()

    # List devices if requested
    if args.list_devices:
        list_audio_devices()
        return

    # Set audio device if specified
    if args.device is not None:
        sd.default.device = args.device

    # Convert 'auto' to None for language
    language = None if args.language.lower() == 'auto' else args.language

    # Create and start transcriber
    try:
        transcriber = LiveTranscriber(
            model_name=args.model,
            language=language,
            chunk_duration=args.chunk_duration,
            energy_threshold=args.energy_threshold
        )
        transcriber.start()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())