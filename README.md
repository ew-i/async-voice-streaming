# Asynchronous Real-Time Voice Streaming ⚡🎙️

Play ElevenLabs text-to-speech audio while it is still being received.

## Prerequisites
- Python 3.11+
- ElevenLabs API Key
- **System Dependency:** The underlying playback layer relies on `mpv`. Ensure it is installed on your host operating system:
  - *macOS:* `brew install mpv`
  - *Ubuntu/Linux:* `sudo apt install mpv`
  - *Windows:* Install via Chocolatey `choco install mpv` or add the binary to your System PATH.

## Installation & Setup

1. **From the project directory**, install the project dependencies with [uv](https://docs.astral.sh/uv/):
    ```bash
    uv sync
    ```

2. **Configure your environment variables:**
   ```bash
   # Linux/macOS
   export ELEVENLABS_API_KEY="your_actual_api_key_here"

   # Windows (CMD)
   set "ELEVENLABS_API_KEY=your_actual_api_key_here"
   ```

## Usage
Run the script to hear a demo sentence, played back while it is still being received:
```bash
uv run python async_voice_streamer.py
```

## License
This project is open-source software licensed under the MIT License.
