# Meeting Assistant

Real-time meeting transcription with speaker diarization. Captures audio from your machine (microphone and/or system speakers via PipeWire), transcribes speech using faster-whisper, and labels speakers using pyannote.

Runs entirely on CPU — no GPU required.

## Features

- **Real-time transcription** — processes audio ~4x faster than real-time on a modern CPU
- **Speaker diarization** — identifies and labels different speakers
- **Cross-chunk speaker tracking** — maintains consistent speaker labels using voice embeddings
- **VAD-based chunking** — splits on natural silence gaps instead of fixed time windows
- **Audio normalization** — handles low-amplitude PipeWire monitor sources
- **Zero hallucinations** — Silero VAD filters non-speech before transcription

## Requirements

- Linux with PipeWire (for `pw-record`)
- [uv](https://github.com/astral-sh/uv) package manager
- A [HuggingFace token](https://huggingface.co/settings/tokens) (for pyannote model access)

## Setup

```bash
# Clone the repo
git clone git@github.com:mfaust-ship-it/meeting-assistant.git
cd meeting-assistant

# Install dependencies
uv sync

# Add your HuggingFace token
echo "HF_TOKEN=hf_your_token_here" > .env
```

## Usage

```bash
# Transcribe system audio (e.g. Teams/Zoom playing through speakers)
./live_transcribe.py --speakers-only

# Transcribe from microphone
./live_transcribe.py

# Transcribe both mic and system audio
./live_transcribe.py --speakers

# Custom output file
./live_transcribe.py --speakers-only --output outputs/my_meeting.md
```

Press `Ctrl+C` to stop. The transcript is written to a markdown file as the meeting progresses.

### Options

| Flag | Description | Default |
|------|------------|---------|
| `--speakers-only` | Capture system audio only (no mic) | off |
| `--speakers` | Capture both mic and system audio | off |
| `--output` | Output file path | `transcript_v4.md` |
| `--model` | Whisper model size | `small` |
| `--max-chunk` | Max chunk duration (seconds) | `30` |
| `--min-silence` | Silence duration to trigger chunk split (seconds) | `1.5` |

## Stack

| Component | Purpose |
|-----------|---------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text (CTranslate2, int8 quantization) |
| [pyannote-audio](https://github.com/pyannote/pyannote-audio) | Speaker diarization (speaker-diarization-3.1) |
| [Silero VAD](https://github.com/snakers4/silero-vad) | Voice activity detection for chunking |
| PipeWire (`pw-record`) | Audio capture from mic and system speakers |

## Project Structure

```
meeting-assistant/
├── live_transcribe.py          # Main transcription script
├── pyproject.toml              # Dependencies (pinned, CPU-only torch)
├── benchmarks/                 # Performance benchmarks
│   ├── benchmark.py            # Transcription speed (faster-whisper)
│   ├── benchmark_diarization.py # Diarization speed (pyannote)
│   └── debug_live.py           # Pipeline step-by-step debugger
├── test/                       # Test data and analysis
│   ├── ground_truth_teams.md   # Reference transcript from Teams
│   ├── test.wav                # Test audio (not committed)
│   └── analysis_*.md           # Accuracy analyses per commit
└── outputs/                    # Transcript outputs (not committed)
```

## Known Limitations

- **Domain-specific terms** — names and jargon get misheard (e.g. "Marius" → "Mario's", "Jaccard" → "Jakar"). Whisper's `hotwords` parameter could help.
- **Speaker diarization on mixed audio** — works best when speakers take turns. Rapid back-and-forth or overlapping speech may get misattributed. Per-participant audio would improve this but isn't available with PipeWire capture.
- **Short utterances** — brief interjections ("Mhm", "Yeah") are often dropped. Acceptable for meeting notes.
- **Speaker label instability at start** — the first few short utterances may get different labels until the speaker tracker has enough audio to build stable embeddings.
