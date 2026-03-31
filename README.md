# Whisper Test — Meeting Assistant Transcription Experiments

## Tests

### Test 1: Transcription Benchmark (CPU, no diarization)

**Script:** `benchmark.py`
**Purpose:** Measure faster-whisper transcription speed on CPU across model sizes (tiny, base, small).
**How:** Records 10s from mic via `arecord`, transcribes with each model, reports time ratio.
**Output:** Console only (no output file).
**Result:** All models faster than real-time. `small` model: 2.22s for 10s audio (0.22x ratio). Selected `small` as the default — no reason to sacrifice quality.

### Test 2: Diarization Benchmark (CPU, pyannote)

**Script:** `benchmark_diarization.py`
**Purpose:** Measure pyannote speaker-diarization-3.1 speed on CPU.
**How:** Uses `test.wav` from Test 1. Runs pyannote pipeline, reports time and speaker segments.
**Output:** Console only.
**Requires:** `HF_TOKEN` env var.
**Result:** 0.39s for 10s audio (0.04x ratio). Detected 1 speaker correctly (single-speaker recording). Combined pipeline estimate: ~0.26x (well under real-time).

### Test 3: Debug Pipeline Steps

**Script:** `debug_live.py`
**Purpose:** Debug each step of the live pipeline in isolation (model loading, pw-record, transcription, diarization).
**How:** Runs each step sequentially with timing and prints results.
**Output:** Console only.
**Requires:** `HF_TOKEN` env var.
**Result:** All steps work. Model loading: ~22s total (8.7s whisper + 13.8s pyannote). pw-record captures from speaker monitor at low amplitude (~0.0026).

### Test 4: Live Transcription — YouTube Video

**Script:** `live_transcribe.py --speakers`
**Purpose:** First end-to-end live test. Capture mic + system audio, transcribe + diarize in real-time.
**How:** Played a YouTube video with multiple speakers while running the script.
**Output:** `transcript.md`
**Requires:** `HF_TOKEN` env var. Audio playing through speakers.
**Result:** Partially successful. Captured some speech correctly, identified different speakers (SPEAKER_00 vs UNKNOWN). Issues: whisper hallucinations on quiet chunks ("You", "Thank you"), low audio amplitude from PipeWire monitor.

### Test 5: Live Transcription — Teams Recording

**Script:** `live_transcribe.py --speakers-only`
**Purpose:** More realistic test using a real Teams meeting recording played through speakers. Compared output against official Teams transcript.
**How:** Played a Teams recording through speakers. Used `--speakers-only` (no mic).
**Output:** `transcript_teams.md`
**Requires:** `HF_TOKEN` env var. Teams recording playing through speakers.
**Reference transcript (official Teams):**
```
Linus: Maybe the nice thing about the signals that I added is that it's basically a signal factory where you can enter like all kinds of attributes and then it will produce a signal for that attribute.
Linus: Yeah, but it needs a mapping of customers attribute to a internal representation...
Linus: ...on Google, which apparently we don't right now...
Linus: OK, maybe we do a quick quiz. Who listened? Marius listened. That's nice.
```
**Result:** Content capture was decent for clear audio portions — got most of the substance correct. Diarization correctly identified single speaker. Main issues:
- Whisper hallucinations on quiet/silent chunks ("You" repeated, "Thank you" repeated)
- Low amplitude from PipeWire speaker monitor (~0.002-0.008)
- 5-second chunk boundary cuts sentences awkwardly
- Some words lost or misheard ("quick quiz" → "quick question", missed "signal factory")

### Test 6: Live Transcription v2 — Teams Recording (improved)

**Script:** `live_transcribe_v2.py --speakers-only`
**Purpose:** Re-test Teams recording with three fixes: audio normalization, Silero VAD filter, 10s chunks.
**Changes from v1:**
- Audio normalization (boost low PipeWire monitor levels to 0.8 peak, max 50x gain)
- Whisper VAD filter enabled (Silero-based, filters non-speech before transcription)
- RMS-based silence detection instead of peak amplitude
- Chunk size increased from 5s to 10s for better whisper context
**Output:** `transcript_v2.md`
**Requires:** `HF_TOKEN` env var. Teams recording playing through speakers.
**Result (after tuning — run v2c):**
- VAD threshold lowered to 0.3 (from default 0.5), speech_pad raised to 400ms
- RMS silence threshold lowered to 0.0005 (let VAD handle speech detection)
- no_speech_threshold set to 0.5

**Output:** `transcript_v2c.md` (best result)
Also: `transcript_v2.md` (VAD too aggressive, no output), `transcript_v2b.md` (RMS threshold too high, most chunks skipped)

**v2c Results — major improvement over v1:**
- Zero hallucinations (no "You"/"Thank you" spam)
- Continuous speech coverage across chunks
- Two speakers detected (SPEAKER_00 and SPEAKER_01)
- Coherent content: "tokenized include check", "Jaccard distance", "signal that takes the customer's data"
- Remaining issues: some words garbled ("Jakab" for "Jaccard"), chunk boundary cuts, most speech attributed to single speaker

### Test 7: Live Transcription v2 — Unseen Portion of Teams Recording

**Script:** `live_transcribe_v2.py --speakers-only`
**Purpose:** Validate v2 on a longer, unseen portion of the same Teams recording. Compare against official Teams transcript (4 speakers: Linus, Sarosh, Srihari, Marius).
**Output:** `transcript_v2d.md`
**Result:**
- Core content well captured — substance of technical discussion comes through clearly
- Domain-specific terms garbled: JSPB→"GSB view", GTIN→missed, HTTP→"SOTT", ASIN→missed
- Speaker transitions poorly detected — 4 real speakers but only 2 detected (SPEAKER_00/SPEAKER_01)
- Short interjections ("Oh", "Mm", "Yeah") mostly lost (acceptable for meeting notes)
- Some phrases nearly verbatim: "enrich the database with this information, synchronously, asynchronously", "manufacturer product name can also be a very strong indicator", "specialized quantity checker"
- Zero hallucinations maintained

**Conclusion:** v2 is good enough for capturing the gist of a meeting. Main weaknesses are domain jargon and multi-speaker diarization on mixed audio.

### Test 8: Live Transcription v3 — VAD-Based Chunking

**Script:** `live_transcribe_v3.py --speakers-only`
**Purpose:** Replace fixed time windows with voice-activity-based chunking. Split on natural silence gaps instead of arbitrary 10s boundaries.
**Changes from v2:**
- Continuous recording (single pw-record process) instead of start/stop per chunk
- Silero VAD runs on 500ms windows to detect speech vs silence
- Chunks split when silence > 800ms after speech detected
- Max chunk size 30s as safety limit
- No more sentence-cutting at arbitrary boundaries
**Output:** `transcript_v3.md`
**Requires:** `HF_TOKEN` env var. Audio playing through speakers.
**Result:**
- VAD-based chunking works well — variable chunk sizes from 1.5s to 30s matching natural speech
- Long monologues captured as coherent paragraphs (chunk 26: 30s single paragraph, no cuts)
- Better dialogue flow — speaker changes detected within natural conversation chunks
- SPEAKER_01 appears more frequently than v2
- Zero hallucinations maintained
- Some over-splitting on short pauses (0.8s threshold triggers on mid-sentence pauses)
- Potential improvement: increase min_silence to 1.5-2s to avoid fragmenting sentences
- Some misheard words remain (domain terms, low amplitude audio)

## Known Issues (remaining after v2)

1. **Domain-specific terms garbled** — JSPB, GTIN, ASIN not recognized. Whisper has a `hotwords` parameter that could help.
2. **Multi-speaker diarization weak on mixed audio** — 4 real speakers but only 2 detected. PipeWire monitor provides a single mixed stream; per-participant audio would improve this.
3. **Chunk boundary sentence cuts** — 10s is better than 5s but still cuts mid-sentence. Could use voice activity to find natural breaks.
4. **torchcodec warning spam** — harmless but noisy; pyannote needs audio passed as waveform dict instead of file path.

## Resolved Issues (fixed in v2)

1. ~~Low audio amplitude from PipeWire monitor~~ — fixed with audio normalization
2. ~~Whisper hallucinations on silence~~ — fixed with Silero VAD filter + no_speech_threshold
3. ~~5-second chunking too short~~ — increased to 10s
