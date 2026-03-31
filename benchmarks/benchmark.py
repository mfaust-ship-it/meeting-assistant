#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["faster-whisper"]
# ///
"""
Quick benchmark: record 10 seconds from mic, then transcribe with faster-whisper on CPU.
Measures transcription time vs audio duration to see if real-time is feasible.
"""

import subprocess
import time
import sys
import os

AUDIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.wav")
DURATION = 10  # seconds

# Step 1: Record audio
print(f"Recording {DURATION} seconds from microphone...")
print("Speak now!")
result = subprocess.run(
    ["arecord", "-d", str(DURATION), "-f", "S16_LE", "-r", "16000", "-c", "1", AUDIO_FILE],
    capture_output=True,
)
if result.returncode != 0:
    print(f"Recording failed: {result.stderr.decode()}")
    sys.exit(1)
print(f"Recording saved to {AUDIO_FILE}")

# Step 2: Transcribe with faster-whisper
from faster_whisper import WhisperModel

for model_size in ["tiny", "base", "small"]:
    print(f"\n--- Model: {model_size} ---")
    print(f"Loading model '{model_size}' (CPU, int8)...")
    t0 = time.time()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    load_time = time.time() - t0
    print(f"Model loaded in {load_time:.1f}s")

    print("Transcribing...")
    t0 = time.time()
    segments, info = model.transcribe(AUDIO_FILE, beam_size=5)
    segments = list(segments)  # force evaluation
    transcribe_time = time.time() - t0

    ratio = transcribe_time / DURATION
    print(f"Language: {info.language} (prob {info.language_probability:.2f})")
    print(f"Transcription time: {transcribe_time:.2f}s for {DURATION}s audio (ratio: {ratio:.2f}x)")
    if ratio < 1.0:
        print(f"  -> FASTER than real-time!")
    else:
        print(f"  -> SLOWER than real-time")

    print("Text:")
    for seg in segments:
        print(f"  [{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
