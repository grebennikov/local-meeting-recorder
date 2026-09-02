#!/bin/bash

TIMESTAMP=$(date -I minutes)

mkdir -p ~/meetings/$TIMESTAMP
pushd ~/meetings/$TIMESTAMP


echo "=== Audio Recording Setup ==="

~/AI/wired

OUTPUT_FILE="./output_audio.wav"
COMPRESSED_FILE="./output_audio_compressed.ogg"

# 1. Start pw-record in the background using the & operator
# Adjust target, rate, and channels as needed
pw-record --target Whisper_Combo --rate 16000 --channels 1 "$OUTPUT_FILE" &
RECORD_PID=$!

echo "Recording started (PID: $RECORD_PID)..."
echo "Press [Ctrl+C] to stop recording and continue script execution."

# 2. Define a trap function to catch SIGINT (Ctrl+C)
stop_recording() {
    echo -e "\n[Ctrl+C detected] Stopping audio recording gracefully..."

    # Send SIGINT specifically to the pw-record process to flush header and close file
    if kill -0 "$RECORD_PID" 2>/dev/null; then
        kill -SIGINT "$RECORD_PID"
        # Wait for the recording process to finish writing the WAV header
        wait "$RECORD_PID" 2>/dev/null
    fi
    echo "Recording stopped cleanly. Saved to: $OUTPUT_FILE"
}

# 3. Attach the trap function specifically to SIGINT
trap stop_recording SIGINT

# 4. Wait for the background recording process to finish (or be interrupted)
wait "$RECORD_PID" 2>/dev/null

# 5. Reset SIGINT back to default behavior so Ctrl+C works normally again
trap - SIGINT

# --- SCRIPT CONTINUES HERE ---
echo ""
echo "=== Continuing Script Execution ==="

echo "=== Removing pipewire loopback ==="
killall pw-loopback

echo "=== Compressing the audio ==="
ffmpeg -i $OUTPUT_FILE -vn -ac 1 -ar 16000 -c:a libopus -b:a 16k $COMPRESSED_FILE

echo "=== Checking or loading Whisper model ==="
lemonade-server status|grep -i 'whisper.*flm'|| lemonade-server load whisper-v3-turbo-FLM

echo "=== Transcribing audio ==="

python3 ~/AI/stt.py $COMPRESSED_FILE

echo "=== Checking or loading Gemma model ==="
lemonade-server status|grep -i 'gemma.*flm'|| lemonade-server load gemma4-it-e4b-FLM

echo "=== Summarizing the transcript ==="
python3 ~/AI/summary.py < transcript.txt > summary.txt

echo "=== Completed! Directory name $TIMESTAMP ==="

popd
