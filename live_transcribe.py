#!/usr/bin/env -S uv run
"""
Live Meeting Transcription

Real-time meeting transcription with speaker diarization.
Captures audio from microphone and/or system speakers via sounddevice
(cross-platform). Transcribes with faster-whisper and labels speakers
using pyannote.

Features:
- VAD-based chunking (splits on natural silence gaps)
- Consistent speaker labels across chunks using voice embeddings
- Audio normalization for low-amplitude PipeWire monitor sources

Usage:
    ./live_transcribe.py --speakers-only
    ./live_transcribe.py --speakers
    ./live_transcribe.py

Press Ctrl+C to stop.
"""

import argparse
import os
import signal
import sys
import tempfile
import tomllib
import wave
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import numpy as np

import warnings
warnings.filterwarnings("ignore", message=".*torchcodec.*")

from audio import AudioStream


def load_config():
    """Load tuning parameters from config.toml."""
    config_path = Path(__file__).parent / "config.toml"
    if not config_path.exists():
        print(f"WARNING: {config_path} not found, using defaults")
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


CONFIG = load_config()

# Audio
SAMPLE_RATE = CONFIG.get("audio", {}).get("sample_rate", 16000)
CHANNELS = CONFIG.get("audio", {}).get("channels", 1)
RECORD_CHUNK_MS = CONFIG.get("audio", {}).get("record_chunk_ms", 500)

# Normalization
NORMALIZE_TARGET_PEAK = CONFIG.get("normalization", {}).get("target_peak", 0.8)
NORMALIZE_MAX_GAIN = CONFIG.get("normalization", {}).get("max_gain", 50.0)

# Whisper
WHISPER_BEAM_SIZE = CONFIG.get("whisper", {}).get("beam_size", 5)
WHISPER_NO_SPEECH_THRESHOLD = CONFIG.get("whisper", {}).get("no_speech_threshold", 0.5)

# VAD
VAD_SPEECH_THRESHOLD = CONFIG.get("vad", {}).get("speech_threshold", 0.3)
VAD_RMS_SILENCE_THRESHOLD = CONFIG.get("vad", {}).get("rms_silence_threshold", 0.0005)

# Speaker tracking
SPEAKER_SIMILARITY_THRESHOLD = CONFIG.get("speaker_tracking", {}).get("similarity_threshold", 0.65)
SPEAKER_EMBEDDING_UPDATE_WEIGHT = CONFIG.get("speaker_tracking", {}).get("embedding_update_weight", 0.3)


def parse_args():
    parser = argparse.ArgumentParser(description="Live meeting transcription")
    parser.add_argument("--speakers", action="store_true")
    parser.add_argument("--speakers-only", action="store_true")
    parser.add_argument("--output", default="transcript.md")
    parser.add_argument("--model", default="small")
    parser.add_argument("--max-chunk", type=float, default=30.0,
                        help="Max chunk duration in seconds (default: 30)")
    parser.add_argument("--min-silence", type=float, default=1.5,
                        help="Min silence duration to split on, in seconds (default: 1.5)")
    return parser.parse_args()



def normalize_audio(audio_data):
    peak = np.max(np.abs(audio_data))
    if peak < 1e-6:
        return audio_data
    gain = min(NORMALIZE_TARGET_PEAK / peak, NORMALIZE_MAX_GAIN)
    return (audio_data * gain).astype(np.float32)


def load_models(model_size, hf_token):
    import torch

    print(f"Loading whisper model '{model_size}'...")
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print("Loading pyannote diarization pipeline...")
    from pyannote.audio import Pipeline
    diarize_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )
    diarize_pipeline.to(torch.device("cpu"))

    print("Loading Silero VAD...")
    vad_model, _ = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        trust_repo=True,
    )

    return whisper_model, diarize_pipeline, vad_model


def check_speech(vad_model, audio_chunk_np):
    """Check if audio chunk contains speech. Returns max VAD confidence."""
    import torch
    window_size = 512
    max_conf = 0.0
    for i in range(0, len(audio_chunk_np) - window_size + 1, window_size):
        tensor = torch.from_numpy(audio_chunk_np[i:i+window_size])
        conf = vad_model(tensor, SAMPLE_RATE).item()
        if conf > max_conf:
            max_conf = conf
    return max_conf


def transcribe_chunk(whisper_model, audio_data):
    if len(audio_data) < SAMPLE_RATE * 0.3:
        return []

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio_data * 32768).astype(np.int16).tobytes())

        segments, info = whisper_model.transcribe(
            tmp.name,
            beam_size=WHISPER_BEAM_SIZE,
            no_speech_threshold=WHISPER_NO_SPEECH_THRESHOLD,
        )
        return [(s.start, s.end, s.text.strip()) for s in segments if s.text.strip()]
    finally:
        os.unlink(tmp.name)


class SpeakerTracker:
    """Maintains consistent speaker labels across chunks using embeddings."""

    def __init__(self):
        self.known_speakers = {}  # global_label -> embedding
        self.next_id = 0
        self.similarity_threshold = SPEAKER_SIMILARITY_THRESHOLD

    def _cosine_similarity(self, a, b):
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm < 1e-8:
            return 0.0
        return dot / norm

    def resolve_speakers(self, diarize_result):
        """Take diarization result, return segments with globally consistent labels."""
        annotation = diarize_result.speaker_diarization
        embeddings = diarize_result.speaker_embeddings  # shape: (n_speakers, embedding_dim)

        # Get unique local labels in order
        local_labels = []
        seen = set()
        for _, _, label in annotation.itertracks(yield_label=True):
            if label not in seen:
                local_labels.append(label)
                seen.add(label)

        # Map local labels to indices (SPEAKER_00 -> 0, SPEAKER_01 -> 1, etc.)
        local_to_idx = {}
        for label in local_labels:
            idx = int(label.split("_")[-1])
            if idx < len(embeddings):
                local_to_idx[label] = idx

        # Map local labels to global labels using embedding similarity
        local_to_global = {}
        for local_label, idx in local_to_idx.items():
            embedding = embeddings[idx]

            # Find best matching known speaker
            best_match = None
            best_sim = -1
            for global_label, known_emb in self.known_speakers.items():
                sim = self._cosine_similarity(embedding, known_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_match = global_label

            if best_match is not None and best_sim >= self.similarity_threshold:
                local_to_global[local_label] = best_match
                # Update embedding with running average
                self.known_speakers[best_match] = (
                    (1 - SPEAKER_EMBEDDING_UPDATE_WEIGHT) * self.known_speakers[best_match]
                    + SPEAKER_EMBEDDING_UPDATE_WEIGHT * embedding
                )
            else:
                # New speaker
                global_label = f"SPEAKER_{self.next_id:02d}"
                self.next_id += 1
                self.known_speakers[global_label] = embedding.copy()
                local_to_global[local_label] = global_label

        # Build segments with global labels
        segments = []
        for turn, _, local_label in annotation.itertracks(yield_label=True):
            global_label = local_to_global.get(local_label, "UNKNOWN")
            segments.append((turn.start, turn.end, global_label))

        return segments


def diarize_chunk(diarize_pipeline, audio_data, speaker_tracker):
    """Run diarization with consistent speaker tracking."""
    if len(audio_data) < SAMPLE_RATE * 0.5:
        return []

    import torch
    waveform = torch.from_numpy(audio_data).unsqueeze(0)
    audio_input = {"waveform": waveform, "sample_rate": SAMPLE_RATE}

    result = diarize_pipeline(audio_input)
    return speaker_tracker.resolve_speakers(result)


def merge_transcript_and_speakers(transcript_segments, speaker_segments, time_offset):
    merged = []
    for t_start, t_end, text in transcript_segments:
        best_speaker = "UNKNOWN"
        best_overlap = 0
        for s_start, s_end, speaker in speaker_segments:
            overlap_start = max(t_start, s_start)
            overlap_end = min(t_end, s_end)
            overlap = max(0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
        abs_start = time_offset + t_start
        merged.append((abs_start, best_speaker, text))
    return merged


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    args = parse_args()
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("ERROR: Set HF_TOKEN environment variable")
        sys.exit(1)

    output_path = Path(args.output)
    max_chunk_samples = int(args.max_chunk * SAMPLE_RATE)
    min_silence_samples = int(args.min_silence * SAMPLE_RATE)
    chunk_read_samples = int(RECORD_CHUNK_MS / 1000 * SAMPLE_RATE)

    whisper_model, diarize_pipeline, vad_model = load_models(args.model, hf_token)
    speaker_tracker = SpeakerTracker()

    # Open audio stream
    if args.speakers_only or args.speakers:
        audio_stream = AudioStream.open_loopback(
            sample_rate=SAMPLE_RATE, channels=CHANNELS, chunk_ms=RECORD_CHUNK_MS
        )
        source_name = "speakers"
    else:
        audio_stream = AudioStream.open_microphone(
            sample_rate=SAMPLE_RATE, channels=CHANNELS, chunk_ms=RECORD_CHUNK_MS
        )
        source_name = "mic"

    print(f"\nAudio source: {source_name}")
    print(f"Output: {output_path}")
    print(f"Max chunk: {args.max_chunk}s, split on silence > {args.min_silence}s")
    print(f"VAD-based chunking: enabled")
    print(f"Audio normalization: enabled")
    print(f"Speaker tracking: enabled (cross-chunk embedding matching)")

    audio_stream.start()

    # Write header
    start_time = datetime.now()
    with open(output_path, "w") as f:
        f.write(f"# Meeting Transcript\n\n")
        f.write(f"**Date:** {start_time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"---\n\n")

    print("\n--- Recording started. Press Ctrl+C to stop. ---\n")

    running = True
    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print("\n\n--- Stopping... ---")
    signal.signal(signal.SIGINT, signal_handler)

    audio_buffer = np.array([], dtype=np.float32)
    silence_counter = 0
    is_speaking = False
    total_time_offset = 0.0
    chunk_count = 0

    while running:
        new_samples = audio_stream.read(timeout=1.0)
        if new_samples is None:
            continue

        window_size = chunk_read_samples
        i = 0
        while i + window_size <= len(new_samples):
            window = new_samples[i:i+window_size]
            speech_prob = check_speech(vad_model, window)

            audio_buffer = np.concatenate([audio_buffer, window])

            if speech_prob > VAD_SPEECH_THRESHOLD:
                is_speaking = True
                silence_counter = 0
            else:
                silence_counter += window_size

            buffer_duration = len(audio_buffer) / SAMPLE_RATE
            should_process = False

            if is_speaking and silence_counter >= min_silence_samples and buffer_duration > 1.0:
                should_process = True
                reason = f"silence gap ({silence_counter/SAMPLE_RATE:.1f}s)"
            elif buffer_duration >= args.max_chunk:
                should_process = True
                reason = f"max chunk ({args.max_chunk}s)"

            if should_process:
                chunk_count += 1
                chunk_duration = len(audio_buffer) / SAMPLE_RATE
                max_amp = np.max(np.abs(audio_buffer))
                rms = float(np.sqrt(np.mean(audio_buffer ** 2)))

                print(f"  Chunk {chunk_count}: {chunk_duration:.1f}s, peak: {max_amp:.4f}, RMS: {rms:.5f}, trigger: {reason}")

                if rms > VAD_RMS_SILENCE_THRESHOLD:
                    normalized = normalize_audio(audio_buffer)

                    transcript_segs = transcribe_chunk(whisper_model, normalized)
                    if transcript_segs:
                        speaker_segs = diarize_chunk(diarize_pipeline, normalized, speaker_tracker)
                        merged = merge_transcript_and_speakers(
                            transcript_segs, speaker_segs, total_time_offset
                        )
                        with open(output_path, "a") as out_f:
                            for abs_start, speaker, text in merged:
                                ts = format_timestamp(abs_start)
                                line = f"**[{ts}] {speaker}:** {text}\n\n"
                                out_f.write(line)
                                print(f"[{ts}] {speaker}: {text}")
                        print(f"  (speakers known: {list(speaker_tracker.known_speakers.keys())})")
                    else:
                        print("  (no speech detected)")
                else:
                    print("  (below RMS threshold)")

                total_time_offset += chunk_duration
                audio_buffer = np.array([], dtype=np.float32)
                silence_counter = 0
                is_speaking = False

            i += window_size

        if i < len(new_samples):
            audio_buffer = np.concatenate([audio_buffer, new_samples[i:]])

    # Process remaining audio
    if len(audio_buffer) > SAMPLE_RATE * 0.5:
        chunk_count += 1
        chunk_duration = len(audio_buffer) / SAMPLE_RATE
        rms = float(np.sqrt(np.mean(audio_buffer ** 2)))
        print(f"  Final chunk {chunk_count}: {chunk_duration:.1f}s, RMS: {rms:.5f}")
        if rms > VAD_RMS_SILENCE_THRESHOLD:
            normalized = normalize_audio(audio_buffer)
            transcript_segs = transcribe_chunk(whisper_model, normalized)
            if transcript_segs:
                speaker_segs = diarize_chunk(diarize_pipeline, normalized, speaker_tracker)
                merged = merge_transcript_and_speakers(
                    transcript_segs, speaker_segs, total_time_offset
                )
                with open(output_path, "a") as out_f:
                    for abs_start, speaker, text in merged:
                        ts = format_timestamp(abs_start)
                        line = f"**[{ts}] {speaker}:** {text}\n\n"
                        out_f.write(line)
                        print(f"[{ts}] {speaker}: {text}")

    # Stop recording
    audio_stream.stop()

    # Footer
    end_time = datetime.now()
    duration = end_time - start_time
    with open(output_path, "a") as f:
        f.write(f"---\n\n")
        f.write(f"**Duration:** {str(duration).split('.')[0]}\n")
        f.write(f"**Chunks processed:** {chunk_count}\n")
        f.write(f"**Speakers detected:** {list(speaker_tracker.known_speakers.keys())}\n")

    print(f"\nTranscript saved to: {output_path}")
    print(f"Speakers detected: {list(speaker_tracker.known_speakers.keys())}")


if __name__ == "__main__":
    main()
