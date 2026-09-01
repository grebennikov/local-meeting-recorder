import os
import requests
import numpy as np
import onnxruntime as ort
from pyannote_onnx import PyannoteONNX

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
AUDIO_FILE = "/tmp/output1_compressed.ogg"
LEMONADE_URL = "http://localhost:13305/api/v1/audio/transcriptions"
MODEL = "whisper-v3-turbo-FLM"
#MODEL = "Whisper-Large-v3-Turbo"

# Path to AMD Vitis AI Provider configuration JSON (provided by Ryzen AI SDK)
VAIP_CONFIG_PATH = os.path.expanduser("/tmp/vaip_config.json")

# ---------------------------------------------------------
# Step 1: Request Speech Transcription from Lemonade Server
# ---------------------------------------------------------
print("1. Requesting transcription from local Lemonade Server...")

with open(AUDIO_FILE, "rb") as f:
    response = requests.post(
        LEMONADE_URL,
        files={"file": f},
        data={
            "model": MODEL,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment"
        }
    )

transcript_data = response.json()
segments = transcript_data.get("segments", [])


with open("/tmp/transcript1.txt", "w") as f:
    print(transcript_data, file=f)

