# Transcription Analysis — commit 5e1f935

**Date:** 2026-03-31
**Script:** `live_transcribe.py` (v4 baseline, CPU-only torch)
**Audio source:** Teams recording played through speakers (`--speakers-only`)
**Duration captured:** ~2 minutes (script crashed due to dependency issues before completing)
**Ground truth:** `test/ground_truth_teams.md` — 4 speakers: Linus, Marius, Sarosh, Srihari

## Speaker Detection

**Expected:** 4 speakers (Linus Armakola, Marius Faust, Sarosh Manzoor, Srihari Kookal)
**Detected:** 5 labels (SPEAKER_00 through SPEAKER_04), of which SPEAKER_01 never appears in output

| Label | Actual Speaker | Notes |
|-------|---------------|-------|
| SPEAKER_00 | Linus | 1 utterance only, then lost |
| SPEAKER_01 | (phantom) | Allocated but never matched to any transcribed text |
| SPEAKER_02 | Linus | 1 utterance only, then lost |
| SPEAKER_03 | Marius | Consistent throughout |
| SPEAKER_04 | Linus | Consistent after first appearance |

**Problems:**
- Linus received 3 different labels. Short utterances at the start of the recording produced embeddings too dissimilar to match later. Once he started his longer monologue, SPEAKER_04 stabilized.
- One phantom speaker was allocated from a brief audio segment that was never matched to transcribed text.
- Sarosh's one line ("It used to be inclusive, I felt") was entirely skipped — likely too quiet or overlapped.
- Srihari never spoke in the captured portion (appears later in the recording).
- A rapid back-and-forth between Linus and Marius (around 1:42-1:49 in ground truth) was merged and misattributed entirely to Marius.

**Root cause:** The `SpeakerTracker` cosine similarity threshold (0.65) is too high for short utterances. Voice embeddings from 1-2 second clips aren't stable enough to match across chunks.

## Content Accuracy

**Good:**
- Core meeting substance captured accurately — technical discussion about signals, tokenized include checks, brand matching all come through clearly
- Long monologues are coherent and largely verbatim
- Zero hallucinations (no "You"/"Thank you" spam that plagued v1)

**Misheard words:**
| Said | Transcribed | Impact |
|------|------------|--------|
| Marius | Mario's | Name — confusing |
| Jacquard | Jakar | Domain term |
| outliers | hot layers | Meaning changed |
| how do we feel about it | how to deal about it | Meaning changed |
| unidirectional includes | unidirectional influence | Minor |

**Dropped content:**
- All short interjections consistently skipped: "Mhm", "Nice", "Yeah", "Uh" — acceptable for meeting notes
- Sarosh's one line entirely missing
- "Claude did it" (Linus's aside) lost in merged text
- "OK, I can start" (Linus) skipped

## Potential Improvements

1. **Lower speaker tracker threshold** — Reduce cosine similarity from 0.65 to ~0.5 to better match short utterances across chunks
2. **Whisper hotwords** — Use the `hotwords` parameter to prime recognition of known domain terms (Marius, Jaccard, GTIN, JSPB, outliers, etc.)
3. **Minimum embedding duration** — Don't register a new speaker from clips shorter than ~3 seconds; instead label as UNKNOWN and retroactively assign once a longer sample matches
4. **Rapid speaker changes** — The Linus/Marius back-and-forth misattribution is a fundamental limitation of diarization on mixed audio. Per-participant audio would fix it, but that's not available with PipeWire capture.
