#!/usr/bin/env bash
# Run a transcription test on Linux (requires PipeWire: pw-play, pw-record).
# Plays a WAV through system speakers and transcribes via loopback capture.
# Stops when playback ends or after max_duration seconds.
#
# Verifies the transcription keeps up with real-time audio by measuring
# the processing overhead after playback ends. If the script falls behind,
# audio buffers in the pw-record pipe and takes a long time to drain.
#
# Usage: ./test/run_test_linux.sh [max_duration_secs]
#   max_duration_secs — stop after this many seconds (default: 300)
#
# Place WAV files in test/input/ (gitignored). Uses the first .wav found.
#
# TODO: Add run_test_macos.sh (playback via afplay + BlackHole loopback)
# TODO: Add run_test_windows.sh (playback via PowerShell + WASAPI loopback)

set -euo pipefail
cd "$(dirname "$0")/.."

MAX_DURATION="${1:-300}"
INPUT_DIR="test/input"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="outputs/test_${TIMESTAMP}.md"
LOG_FILE="outputs/test_${TIMESTAMP}.log"

# Max acceptable overhead in seconds — one chunk processing time.
# If overhead exceeds this, the script is falling behind real-time.
MAX_OVERHEAD=30

# Find input WAV
WAV_FILE=$(find "$INPUT_DIR" -maxdepth 1 -name '*.wav' -print -quit 2>/dev/null)
if [[ -z "$WAV_FILE" ]]; then
    echo "ERROR: No .wav file found in $INPUT_DIR/"
    echo "Place a test WAV file there and try again."
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "ERROR: .env file not found (need HF_TOKEN)"
    exit 1
fi

export $(cat .env | xargs)
mkdir -p outputs

WAV_DURATION=$(uv run python3 -c "
import wave
with wave.open('$WAV_FILE', 'rb') as wf:
    print(f'{wf.getnframes() / wf.getframerate():.1f}')
")

echo "=== Test Configuration ==="
echo "Input:        $WAV_FILE (${WAV_DURATION}s)"
echo "Max duration: ${MAX_DURATION}s"
echo "Output:       $OUTPUT_FILE"
echo "Log:          $LOG_FILE"
echo ""

# Start transcription in background, capture stdout+stderr to log
echo "Starting transcription..."
uv run ./live_transcribe.py --speakers-only --output "$OUTPUT_FILE" > "$LOG_FILE" 2>&1 &
TRANSCRIBE_PID=$!

# Wait for models to load
echo "Waiting for models to load..."
while ! grep -q "Recording started" "$LOG_FILE" 2>/dev/null; do
    if ! kill -0 "$TRANSCRIBE_PID" 2>/dev/null; then
        echo "ERROR: Transcription script died during startup. Log:"
        cat "$LOG_FILE"
        exit 1
    fi
    sleep 1
done
echo "Models loaded."
echo ""

# Start playback with timeout
echo "Playing audio (max ${MAX_DURATION}s)..."
START_TIME=$(date +%s.%N)
timeout "$MAX_DURATION" pw-play "$WAV_FILE" &
PLAYBACK_PID=$!

# Wait for playback to finish or timeout
wait "$PLAYBACK_PID" 2>/dev/null || true
END_PLAYBACK=$(date +%s.%N)
PLAYBACK_ELAPSED=$(echo "$END_PLAYBACK - $START_TIME" | bc)

if (( $(echo "$PLAYBACK_ELAPSED >= $MAX_DURATION" | bc -l) )); then
    echo "Playback stopped at ${MAX_DURATION}s timeout."
else
    echo "Playback finished naturally (${PLAYBACK_ELAPSED}s)."
fi

# Wait for transcription to finish its current chunk, then stop.
# Poll until no new output for 3 seconds (means current chunk is done).
echo "Waiting for in-flight chunk to finish..."
LAST_SIZE=0
STABLE_COUNT=0
while (( STABLE_COUNT < 3 )); do
    sleep 1
    CURRENT_SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo "0")
    if (( CURRENT_SIZE == LAST_SIZE )); then
        (( STABLE_COUNT++ )) || true
    else
        STABLE_COUNT=0
        LAST_SIZE=$CURRENT_SIZE
    fi
    # Safety: don't wait more than 60s
    WAITED=$(echo "$(date +%s.%N) - $END_PLAYBACK" | bc)
    if (( $(echo "$WAITED > 60" | bc -l) )); then
        echo "WARNING: Transcription still processing after 60s — likely falling behind."
        break
    fi
done

kill -INT "$TRANSCRIBE_PID" 2>/dev/null || true
wait "$TRANSCRIBE_PID" 2>/dev/null || true
END_TRANSCRIBE=$(date +%s.%N)

# Calculate timing
TOTAL_ELAPSED=$(echo "$END_TRANSCRIBE - $START_TIME" | bc)
OVERHEAD=$(echo "$TOTAL_ELAPSED - $PLAYBACK_ELAPSED" | bc)
OVERHEAD_INT=$(echo "$OVERHEAD" | cut -d. -f1)

# Parse results from log
CHUNKS=$(grep -c "Chunk [0-9]" "$LOG_FILE" 2>/dev/null || echo "0")
SPEAKERS=$(grep -oP 'SPEAKER_\d+' "$LOG_FILE" 2>/dev/null | sort -u | wc -l)
LAST_TIMESTAMP=$(grep -oP '\[\d{2}:\d{2}:\d{2}\]' "$LOG_FILE" 2>/dev/null | tail -1 || echo "N/A")

# Real-time check
if (( OVERHEAD_INT > MAX_OVERHEAD )); then
    RT_STATUS="FAIL — overhead ${OVERHEAD_INT}s exceeds ${MAX_OVERHEAD}s limit"
else
    RT_STATUS="PASS — overhead ${OVERHEAD_INT}s within ${MAX_OVERHEAD}s limit"
fi

echo ""
echo "=== Test Results ==="
echo "Playback duration:   ${PLAYBACK_ELAPSED}s"
echo "Total elapsed:       ${TOTAL_ELAPSED}s"
echo "Processing overhead: ${OVERHEAD}s"
echo "Chunks processed:    $CHUNKS"
echo "Speakers detected:   $SPEAKERS"
echo "Last timestamp:      $LAST_TIMESTAMP"
echo ""
echo "Real-time check:     $RT_STATUS"
echo ""
echo "Transcript: $OUTPUT_FILE"
echo "Log:        $LOG_FILE"
