# CLAUDE.md

## Project Overview

Real-time meeting transcription with speaker diarization. Runs on CPU using faster-whisper, pyannote-audio, and Silero VAD. Cross-platform audio capture via `audio.py` (Linux: pw-record, macOS: BlackHole/sounddevice, Windows: WASAPI/sounddevice).

## Environment

- **Package manager:** uv
- **Dependencies:** Defined in `pyproject.toml` with pinned versions (torch cu128 build for performance)
- **HuggingFace token:** Stored in `.env` (git-ignored), required for pyannote model access
- **Setup:** `uv sync` to install everything

## Running the Script

```bash
export $(cat .env | xargs)
./live_transcribe.py --speakers-only --output outputs/my_meeting.md
```

## Testing and Analysis

- Place test WAV files in `test/input/` (git-ignored) alongside ground truth VTT files (committed)
- Run `./test/run_test_linux.sh [max_duration_secs]` to play audio and transcribe simultaneously (Linux only, uses pw-play)
- The test verifies real-time performance: PASS if processing overhead < 30s after playback ends
- After a test run, write an analysis file as `test/analysis_<commit-hash>.md` documenting speaker detection accuracy, misheard words, and content quality compared to ground truth
- Transcript outputs go in `outputs/` (git-ignored, regenerable)

## What Not to Commit

- Audio files (`.wav`, `.mp3`, etc.) — git-ignored
- `.env` — contains HF_TOKEN
- `outputs/` — regenerable transcript files
- `.venv/` — managed by uv

## Code Style

- Scripts use `#!/usr/bin/env -S uv run` shebang for direct execution
- Benchmark and debug scripts live in `benchmarks/` — don't mix with main scripts
- Keep dependency versions pinned in `pyproject.toml`
