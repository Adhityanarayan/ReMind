#!/usr/bin/env python3
"""
Enhanced Live Transcription with File Output
Saves transcriptions to file with timestamps and speaker detection
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
import json
import os


class TranscriptionRecorder:
    """Live transcription with file output and enhanced features"""

    def __init__(self, model_name="base", language="en", sample_rate=16000,
                 chunk_duration=5, energy_threshold=0.01, output_file=None,
                 output_format="txt"):
        """
        Initialize the transcription recorder

        Args:
            model_name: Whisper model size
            language: Language code or None for auto-detect
            sample_rate: Audio sample rate in Hz
            chunk_duration: Duration of audio chunks (seconds)
            energy_threshold: Minimum audio energy to process
            output_file: Output file path (None for stdout only)
            output_format: Output format (txt, json, srt)
        """
        print(f"Loading Whisper {model_name} model...")
        self.model = whisper.load_model(model_name)
        self.language = language
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.energy_threshold = energy_threshold
        self.output_file = output_file
        self.output_format = output_format

        # Audio buffer
        self.audio_queue = queue.Queue()
        self.is_running = False

        # Transcription storage
        self.transcriptions = []
        self.start_time = None
        self.segment_counter = 0

        # File handle
        self.file_handle = None
        if output_file:
            self._open_output_file()

        print(f"Model loaded! Ready to transcribe and save.")

    def _open_output_file(self):
        """Open output file for writing"""
        try:
            self.file_handle = open(self.output_file, 'w', encoding='utf-8')
            if self.output_format == 'json':
                # Start JSON array
                self.file_handle.write('[\n')
            elif self.output_format == 'txt':
                # Write header
                self.file_handle.write(f"Transcription started: {datetime.now()}\n")
                self.file_handle.write("=" * 80 + "\n\n")
            print(f"Saving transcription to: {self.output_file}")
        except Exception as e:
            print(f"Error opening output file: {e}", file=sys.stderr)
            self.file_handle = None

    def _close_output_file(self):
        """Close output file"""
        if self.file_handle:
            if self.output_format == 'json':
                # Close JSON array
                self.file_handle.write('\n]\n')
            elif self.output_format == 'srt':
                pass  # SRT is already complete
            elif self.output_format == 'txt':
                self.file_handle.write(f"\n\nTranscription ended: {datetime.now()}\n")

            self.file_handle.close()
            print(f"\nTranscription saved to: {self.output_file}")

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream"""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        self.audio_queue.put(indata.copy())

    def calculate_energy(self, audio_data):
        """Calculate audio energy (RMS)"""
        return np.sqrt(np.mean(audio_data**2))

    def transcribe_chunk(self, audio_data):
        """Transcribe a chunk of audio with detailed results"""
        audio = audio_data.flatten().astype(np.float32)
        energy = self.calculate_energy(audio)

        if energy < self.energy_threshold:
            return None

        # Transcribe with detailed output
        result = self.model.transcribe(
            audio,
            language=self.language,
            fp16=False,
            task='transcribe',
            verbose=False
        )

        if result['text'].strip():
            return {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'energy': float(energy),
                'timestamp': datetime.now(),
                'segments': result.get('segments', [])
            }

        return None

    def format_transcription(self, transcription):
        """Format transcription for display and saving"""
        timestamp = transcription['timestamp'].strftime("%H:%M:%S")
        text = transcription['text']
        energy = transcription['energy']
        language = transcription['language']

        return {
            'display': f"[{timestamp}] ({language}, Energy: {energy:.4f})\n>>> {text}",
            'data': transcription
        }

    def save_to_file(self, transcription):
        """Save transcription to file in specified format"""
        if not self.file_handle:
            return

        try:
            if self.output_format == 'json':
                # JSON format
                if self.segment_counter > 0:
                    self.file_handle.write(',\n')

                json_obj = {
                    'segment': self.segment_counter,
                    'timestamp': transcription['timestamp'].isoformat(),
                    'text': transcription['text'],
                    'language': transcription['language'],
                    'energy': transcription['energy']
                }
                json.dump(json_obj, self.file_handle, indent=2)

            elif self.output_format == 'srt':
                # SRT subtitle format
                start_time = (self.segment_counter * self.chunk_duration)
                end_time = start_time + self.chunk_duration

                def format_srt_time(seconds):
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    millis = int((seconds % 1) * 1000)
                    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

                self.file_handle.write(f"{self.segment_counter + 1}\n")
                self.file_handle.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
                self.file_handle.write(f"{transcription['text']}\n\n")

            else:  # txt format
                timestamp = transcription['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                self.file_handle.write(f"[{timestamp}] {transcription['text']}\n")

            self.file_handle.flush()  # Ensure it's written immediately

        except Exception as e:
            print(f"Error saving to file: {e}", file=sys.stderr)

    def process_audio(self):
        """Process audio from queue and transcribe"""
        audio_buffer = np.array([], dtype=np.float32)

        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                audio_buffer = np.concatenate([audio_buffer, chunk.flatten()])

                if len(audio_buffer) >= self.chunk_samples:
                    chunk_to_process = audio_buffer[:self.chunk_samples]
                    audio_buffer = audio_buffer[self.chunk_samples:]

                    result = self.transcribe_chunk(chunk_to_process)

                    if result:
                        formatted = self.format_transcription(result)

                        # Display
                        print(f"\n{formatted['display']}")
                        print("-" * 80)

                        # Save
                        self.transcriptions.append(result)
                        self.save_to_file(result)
                        self.segment_counter += 1

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error processing audio: {e}", file=sys.stderr)

    def start(self):
        """Start live transcription"""
        self.start_time = datetime.now()

        print("\n" + "=" * 80)
        print("LIVE TRANSCRIPTION WITH RECORDING STARTED")
        print("=" * 80)
        print(f"Model: {self.model}")
        if self.output_file:
            print(f"Output: {self.output_file} ({self.output_format})")
        print(f"Speak into your microphone... Press Ctrl+C to stop")
        print("=" * 80 + "\n")

        self.is_running = True

        processing_thread = threading.Thread(target=self.process_audio)
        processing_thread.start()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self.audio_callback,
                blocksize=int(self.sample_rate * 0.5)
            ):
                while self.is_running:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping transcription...")
        finally:
            self.stop()
            processing_thread.join()

    def stop(self):
        """Stop transcription and save summary"""
        self.is_running = False

        # Close output file
        self._close_output_file()

        # Print summary
        duration = (datetime.now() - self.start_time).total_seconds()
        print(f"\nTranscription Summary:")
        print(f"  Duration: {duration:.1f} seconds")
        print(f"  Segments: {len(self.transcriptions)}")
        if self.transcriptions:
            total_words = sum(len(t['text'].split()) for t in self.transcriptions)
            print(f"  Total words: {total_words}")
            print(f"  Words/minute: {(total_words / duration * 60):.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Live audio transcription with file output"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code or 'auto' (default: en)"
    )
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=5.0,
        help="Audio chunk duration in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--energy-threshold",
        type=float,
        default=0.01,
        help="Minimum audio energy (default: 0.01)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout only)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="txt",
        choices=["txt", "json", "srt"],
        help="Output format (default: txt)"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device ID"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List audio devices and exit"
    )

    args = parser.parse_args()

    if args.list_devices:
        print("\nAvailable audio input devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"{i}: {device['name']}")
        return 0

    if args.device is not None:
        sd.default.device = args.device

    language = None if args.language.lower() == 'auto' else args.language

    # Auto-generate output filename if format specified but no output
    if args.output is None and args.format != 'txt':
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"transcription_{timestamp}.{args.format}"

    try:
        recorder = TranscriptionRecorder(
            model_name=args.model,
            language=language,
            chunk_duration=args.chunk_duration,
            energy_threshold=args.energy_threshold,
            output_file=args.output,
            output_format=args.format
        )
        recorder.start()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())