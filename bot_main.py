import os
import re
import socket
import subprocess
import time
import queue
import tempfile
import wave
import requests
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from TTS.api import TTS

# ================== CONFIG ==================
KEYWORD = "bot"  # Wake word
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/stt-to-llm"  # <-- Change to your n8n webhook URL
SAMPLERATE = 16000
BLOCK_DURATION = 1.0
MODEL_NAME_STT = "small"  # Faster-Whisper model
MODEL_NAME_TTS = "tts_models/en/ljspeech/overflow"
OUTPUT_DIR = "output_realtime"
DEBUG = True

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================== INTERNET CHECK ==================
def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Check if the device has an active internet connection."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

# ================== AUDIO SYNTHESIS ==================
def get_next_counter():
    """Get the next available counter for audio file naming."""
    existing_files = os.listdir(OUTPUT_DIR)
    counters = []
    for f in existing_files:
        match = re.match(r"voice_(\d+)\.wav", f)
        if match:
            counters.append(int(match.group(1)))
    return max(counters) + 1 if counters else 1

def synthesize_speech(tts, text, counter):
    """Generate speech and save to file."""
    output_file = os.path.join(OUTPUT_DIR, f"voice_{counter}.wav")
    tts.tts_to_file(text=text, file_path=output_file)
    print(f"✅ Audio saved to {output_file}")
    return output_file

# ================== AUDIO PLAYBACK ==================
def play_audio(file_path):
    """Play audio cross-platform."""
    if os.name == "nt":  # Windows
        audio_player = f"powershell -c (New-Object Media.SoundPlayer '{file_path}').PlaySync()"
        subprocess.Popen(audio_player, shell=True)
    else:  # Linux / Mac
        if subprocess.call("which ffplay", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            subprocess.Popen(f"ffplay -nodisp -autoexit {file_path} > /dev/null 2>&1 &", shell=True)
        else:
            subprocess.call(f"aplay {file_path}", shell=True)

# ================== SEND TEXT TO n8n ==================
def send_to_n8n(text):
    """Send recognized text to n8n and get LLM reply."""
    try:
        response = requests.post(N8N_WEBHOOK_URL, json={"text": text})
        if response.status_code == 200:
            reply = response.json().get("reply", "")
            print(f"\n🤖 LLM Reply: {reply}\n")
            return reply
        else:
            print(f"⚠️ n8n returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send to n8n: {e}")
    return None

# ================== MICROPHONE SELECTION ==================
def get_default_input_device():
    """Selects the best available microphone."""
    try:
        devices = sd.query_devices()
        print("\n=== Available Audio Devices ===")
        for i, d in enumerate(devices):
            print(f"[{i}] {d['name']}  ({d['max_input_channels']} ch)")

        for i, d in enumerate(devices):
            if "pulse" in d["name"].lower() and d["max_input_channels"] > 0:
                print(f"\n✅ Using PulseAudio device: {d['name']} (ID {i})")
                return i

        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                print(f"\n✅ Using device: {d['name']} (ID {i})")
                return i

        raise RuntimeError("❌ No valid microphone found!")
    except Exception as e:
        print(f"⚠️ Device detection failed: {e}")
        print("Falling back to system default (-1).")
        return None

# ================== MAIN FUNCTION ==================
def main():
    # Load models
    print("🔄 Loading Faster-Whisper STT model...")
    stt_model = WhisperModel(MODEL_NAME_STT)
    print("✅ STT model loaded successfully!")

    print("🔄 Loading TTS model...")
    tts = TTS(model_name=MODEL_NAME_TTS)
    print("✅ TTS model loaded successfully!")

    counter = get_next_counter()
    input_device = get_default_input_device()
    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time, status):
        if status:
            print(f"[Status] {status}")
        audio_queue.put(indata.copy())

    # Start listening
    print(f"\n🎧 Say '{KEYWORD}' to talk to the LLM. Press Ctrl+C to stop.")
    stream = sd.InputStream(
        device=input_device,
        samplerate=SAMPLERATE,
        channels=1,
        callback=audio_callback,
        blocksize=int(SAMPLERATE * BLOCK_DURATION)
    )

    with stream:
        try:
            while True:
                # Check internet status before processing
                if not check_internet():
                    print("🌐 Internet Status: ❌ No Internet")
                    print("⚠️ Waiting for connection...")
                    while not check_internet():
                        time.sleep(2)
                    print("✅ Connection restored!")

                # Process microphone audio
                audio_block = audio_queue.get()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    with wave.open(tmp_wav, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLERATE)
                        wf.writeframes((audio_block * 32767).astype(np.int16).tobytes())
                    temp_path = tmp_wav.name

                segments, info = stt_model.transcribe(temp_path, beam_size=5)
                os.remove(temp_path)

                for segment in segments:
                    text = segment.text.lower().strip()
                    if DEBUG:
                        print(f"[Debug] Detected: {text}")

                    if KEYWORD in text:
                        print(f"🔔 Wake word detected! Sending to n8n...")
                        reply = send_to_n8n(text)

                        # If we have an LLM reply, speak it
                        if reply:
                            output_file = synthesize_speech(tts, reply, counter)
                            play_audio(output_file)
                            counter += 1

        except KeyboardInterrupt:
            print("\n🛑 Stopped.")

# ================== RUN ==================
if __name__ == "__main__":
    main()
