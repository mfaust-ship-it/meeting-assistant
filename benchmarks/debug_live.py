#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "faster-whisper",
#     "pyannote.audio",
#     "soundfile",
#     "numpy",
#     "torch",
# ]
# ///
"""Debug: test each step of the live transcription pipeline."""

import warnings
warnings.filterwarnings("ignore", message=".*torchcodec.*")

import sys
import os
import time
import subprocess
import wave
import tempfile
import numpy as np

print("Step 1: Loading whisper model...", flush=True)
t0 = time.time()
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
print(f"  Done in {time.time()-t0:.1f}s", flush=True)

print("Step 2: Loading pyannote...", flush=True)
t0 = time.time()
import torch
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=os.environ.get("HF_TOKEN"),
)
pipeline.to(torch.device("cpu"))
print(f"  Done in {time.time()-t0:.1f}s", flush=True)

print("Step 3: Testing pw-record (5 seconds from speakers monitor)...", flush=True)
wav_path = os.path.join(tempfile.gettempdir(), "debug_test.wav")
proc = subprocess.Popen(
    ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16",
     "--target", "alsa_output.pci-0000_c1_00.6.analog-stereo.monitor",
     wav_path],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
time.sleep(5)
import signal
proc.send_signal(signal.SIGINT)
stdout, stderr = proc.communicate(timeout=5)
print(f"  pw-record exit code: {proc.returncode}", flush=True)
if stderr:
    print(f"  stderr: {stderr.decode()[:200]}", flush=True)

time.sleep(0.2)
try:
    with wave.open(wav_path, "rb") as wf:
        n_frames = wf.getnframes()
        sr = wf.getframerate()
        dur = n_frames / sr if sr > 0 else 0
        print(f"  Recorded: {n_frames} frames, {sr}Hz, {dur:.1f}s", flush=True)
        raw = wf.readframes(n_frames)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        print(f"  Audio max amplitude: {np.max(np.abs(data)):.4f}", flush=True)
except Exception as e:
    print(f"  Error reading wav: {e}", flush=True)
    sys.exit(1)

if np.max(np.abs(data)) < 0.001:
    print("  WARNING: Audio is silent!", flush=True)
else:
    print("Step 4: Transcribing...", flush=True)
    t0 = time.time()
    segments, info = model.transcribe(wav_path, beam_size=5)
    segs = list(segments)
    print(f"  Done in {time.time()-t0:.1f}s", flush=True)
    for s in segs:
        print(f"  [{s.start:.1f}-{s.end:.1f}] {s.text}", flush=True)

    print("Step 5: Diarizing...", flush=True)
    t0 = time.time()
    waveform = torch.from_numpy(data).unsqueeze(0)
    result = pipeline({"waveform": waveform, "sample_rate": 16000})
    annotation = result.speaker_diarization
    print(f"  Done in {time.time()-t0:.1f}s", flush=True)
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        print(f"  [{turn.start:.1f}-{turn.end:.1f}] {speaker}", flush=True)

os.unlink(wav_path)
print("\nAll steps OK!", flush=True)
