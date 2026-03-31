#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["pyannote.audio", "torch", "soundfile"]
# ///
"""
Benchmark pyannote-audio speaker diarization on CPU using the test.wav from the transcription benchmark.
"""

import time
import os

AUDIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.wav")

if not os.path.exists(AUDIO_FILE):
    print(f"Error: {AUDIO_FILE} not found. Run benchmark.py first to record audio.")
    exit(1)

# Get audio duration
import soundfile as sf
data, sample_rate = sf.read(AUDIO_FILE)
duration = len(data) / sample_rate
print(f"Audio file: {AUDIO_FILE} ({duration:.1f}s)")

# Load pyannote pipeline
from pyannote.audio import Pipeline
import torch

print("\nLoading pyannote diarization pipeline (CPU)...")
t0 = time.time()
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=os.environ.get("HF_TOKEN"),
)
pipeline.to(torch.device("cpu"))
load_time = time.time() - t0
print(f"Pipeline loaded in {load_time:.1f}s")

print("\nRunning diarization...")
# Preload audio as waveform dict since torchcodec/ffmpeg is not available
import torch
import numpy as np
waveform_np = data if len(data.shape) == 1 else data[:, 0]
waveform_tensor = torch.from_numpy(waveform_np.astype(np.float32)).unsqueeze(0)
audio_input = {"waveform": waveform_tensor, "sample_rate": sample_rate}

t0 = time.time()
diarization = pipeline(audio_input)
diarize_time = time.time() - t0

ratio = diarize_time / duration
print(f"Diarization time: {diarize_time:.2f}s for {duration:.1f}s audio (ratio: {ratio:.2f}x)")
if ratio < 1.0:
    print(f"  -> FASTER than real-time!")
else:
    print(f"  -> SLOWER than real-time")

print("\nSpeaker segments:")
annotation = diarization.speaker_diarization
for turn, _, speaker in annotation.itertracks(yield_label=True):
    print(f"  [{turn.start:.1f}s - {turn.end:.1f}s] {speaker}")
