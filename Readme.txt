TTS and STT Setup
=================

1️⃣ Python Virtual Environment
-----------------------------
Purpose: Isolate dependencies

Commands:
    sudo apt install python3-venv python3-pip
    python3 -m venv .venv
    source .venv/bin/activate

2️⃣ Coqui TTS
-------------
Purpose: Real-time text-to-speech

Python package:
    pip install TTS

List available models:
    tts --list_models

Model to download:
    tts_models/en/ljspeech/overflow (LJSpeech Overflow model)
    - Automatically downloaded by the TTS API

Optional TTS Server:
    tts-server --model_name tts_models/en/ljspeech/overflow

3️⃣ Audio Playback Tools
-----------------------
Linux:
    aplay (default ALSA tool)
    ffplay (from FFmpeg) for non-blocking playback
    sudo apt install ffmpeg alsa-utils

Windows:
    PowerShell media player (built-in) — commented out for now

4️⃣ Whisper STT
---------------
Purpose: Convert microphone audio to text

Python package:
    pip install openai-whisper
    Optional
    pip install faster-whisper (recomend this)
    pip install faster-whisper[cuda]




Model files:
    Automatically downloaded when you run:
        import whisper
        model = whisper.load_model("tiny")  # options: tiny, base, small, medium, large

Required system dependency:
    FFmpeg for audio processing
    sudo apt install ffmpeg
    sudo apt install portaudio19-dev python3-pyaudio
    sudo apt install alsa-utils pulseaudio pavucontrol
    sudo apt install espeak-ng -y



5️⃣ Microphone Audio Capture
---------------------------
Python packages:
    pip install sounddevice numpy

Purpose:
    Record live audio from microphone for real-time transcription

6️⃣ Optional Tools
-----------------
Raspberry Pi OS:
    Make sure alsa-utils and ffmpeg are installed

Windows:
    PowerShell media player works natively

Linux / Pi OS:
    aplay or ffplay

7️⃣ Folder Structure
-------------------
project_root/
│
├─ .venv/                    # Python virtual environment
├─ output_realtime/          # Where generated WAV files will be saved
├─ tts_realtime_linux.py     # Your TTS script
├─ stt_whisper.py            # Whisper STT script (optional)
