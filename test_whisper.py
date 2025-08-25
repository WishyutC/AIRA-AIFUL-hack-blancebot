import sounddevice as sd
import numpy as np
import wave
import queue
import tempfile
import os
import requests
from faster_whisper import WhisperModel

# === Configuration ===
MODEL_NAME = "small"
KEYWORD = "bot"
SAMPLERATE = 16000
BLOCK_DURATION = 1.0
DEBUG = True
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/stt-to-llm"  # Change to ours n8n webhook URL

# === Load Whisper Model ===
print("Loading Whisper model...")
model = WhisperModel(MODEL_NAME)
print("Model loaded ✅")

# === Auto-select Microphone ===
def get_default_input_device():
    """Selects the best available microphone"""
    try:
        devices = sd.query_devices()
        print("\n=== Available Audio Devices ===")
        for i, d in enumerate(devices):
            print(f"[{i}] {d['name']}  ({d['max_input_channels']} ch)")

        # Prefer PulseAudio if available
        for i, d in enumerate(devices):
            if "pulse" in d["name"].lower() and d["max_input_channels"] > 0:
                print(f"\n✅ Using PulseAudio device: {d['name']} (ID {i})")
                return i

        # Otherwise pick first valid input device
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                print(f"\n✅ Using device: {d['name']} (ID {i})")
                return i

        raise RuntimeError("❌ No valid microphone found!")
    except Exception as e:
        print(f"⚠️ Device detection failed: {e}")
        print("Falling back to system default (-1).")
        return None

input_device = get_default_input_device()

# === Send Text to n8n ===
def send_to_n8n(text):
    """Send recognized text to n8n and get LLM reply"""
    try:
        response = requests.post(N8N_WEBHOOK_URL, json={"text": text})
        if response.status_code == 200:
            reply = response.json().get("reply", "")
            print(f"🤖 LLM Reply: {reply}")
            return reply
        else:
            print(f"⚠️ n8n returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send to n8n: {e}")
    return None

# === Audio Queue ===
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Callback to collect microphone data"""
    if status:
        print(f"[Status] {status}")
    audio_queue.put(indata.copy())

# === Start Microphone Stream ===
print(f"\n🎧 Listening for wake word '{KEYWORD}'... Press Ctrl+C to stop.")
stream = sd.InputStream(
    device=input_device,
    samplerate=SAMPLERATE,
    channels=1,
    callback=audio_callback,
    blocksize=int(SAMPLERATE * BLOCK_DURATION)
)

# === Main Loop ===
with stream:
    try:
        while True:
            audio_block = audio_queue.get()

            # Save block to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                with wave.open(tmp_wav, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLERATE)
                    wf.writeframes((audio_block * 32767).astype(np.int16).tobytes())
                temp_path = tmp_wav.name

            # Transcribe using faster-whisper
            segments, info = model.transcribe(temp_path, beam_size=5)
            os.remove(temp_path)

            # Process transcription results
            for segment in segments:
                text = segment.text.lower().strip()
                if DEBUG:
                    print(f"[Debug] Detected: {text}")

                # If wake word detected → send to n8n
                if KEYWORD in text:
                    print(f"🔔 Wake word detected! Sending text to n8n...")
                    reply = send_to_n8n(text)

                    # Optional: Future TTS integration
                    if reply:
                        print(f"🎤 LLM says: {reply}")

    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
