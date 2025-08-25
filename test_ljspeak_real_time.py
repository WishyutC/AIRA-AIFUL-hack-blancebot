import os
import re
import socket
import subprocess
import time
from TTS.api import TTS

# ========== CONFIG ==========
OUTPUT_DIR = "output_realtime"
MODEL_NAME = "tts_models/en/ljspeech/overflow"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== INTERNET CHECK ==========
def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Check if the device has an active internet connection."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

# ========== AUDIO SYNTHESIS ==========
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

# ========== AUDIO PLAYBACK ==========
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

# ========== MAIN FUNCTION ==========
def main():
    print("🔄 Loading TTS model...")
    tts = TTS(model_name=MODEL_NAME)
    print("✅ Model loaded successfully!")

    counter = get_next_counter()

    while True:
        # Check Wi-Fi status
        if check_internet():
            print("🌐 Internet Status: ✅ Connected")
        else:
            print("🌐 Internet Status: ❌ No Internet")
            print("⚠️ Waiting for connection...")
            while not check_internet():
                time.sleep(2)
            print("✅ Connection restored!")

        # Get user input
        text = input("Enter text to synthesize (or 'exit_func' to quit): ")
        if text.lower() == "exit_func":
            print("👋 Exiting...")
            break

        # Synthesize and play audio
        output_file = synthesize_speech(tts, text, counter)
        play_audio(output_file)

        counter += 1

# ========== RUN ==========
if __name__ == "__main__":
    main()
