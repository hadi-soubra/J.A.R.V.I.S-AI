# J.A.R.V.I.S

**Just A Rather Very Intelligent System**

A fully local, Iron Man–inspired AI desktop assistant built with PyQt6. Supports local LLMs via Ollama, cloud models via the Anthropic API, voice synthesis via Kokoro-ONNX (GPU-accelerated), and speech-to-text via faster-whisper — all in a sleek dark terminal UI with a cinematic boot sequence.

![AI view](assets/view.png)

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
  - [1. Python](#1-python)
  - [2. Python Packages](#2-python-packages)
  - [3. Ollama (Local LLM)](#3-ollama-local-llm)
  - [4. Ollama Models](#4-ollama-models)
  - [5. Kokoro TTS Voices](#5-kokoro-tts-voices)
  - [6. STT Model (Whisper)](#6-stt-model-whisper)
  - [7. Anthropic API Key (Optional)](#7-anthropic-api-key-optional)
- [Configuration](#configuration)
- [Running JARVIS](#running-jarvis)
- [Auto-Launch on Login (Windows Task Scheduler)](#auto-launch-on-login-windows-task-scheduler)
- [Usage Guide](#usage-guide)
  - [Sending Messages](#sending-messages)
  - [Switching Models](#switching-models)
  - [Voice (TTS)](#voice-tts)
  - [Speech-to-Text (STT)](#speech-to-text-stt)
  - [Attaching Files](#attaching-files)
  - [Memory](#memory)
  - [Conversation History](#conversation-history)
  - [Think Mode](#think-mode)
  - [Stopping a Response](#stopping-a-response)
  - [PC Control](#pc-control)
- [Customisation](#customisation)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Cinematic boot sequence** — matrix static animation plays while TTS pre-synthesizes all boot lines. Once ready, typewriter animation and voice start simultaneously, perfectly in sync
- **"Clearing Throat" response animation** — when TTS is enabled, JARVIS shows a pulsing `CLEARING THROAT ●○○` animation (with a cough sound effect) while pre-synthesizing the first sentence. Text and voice then unleash together at the same moment
- **Dual provider support** — run models locally via Ollama or use Anthropic cloud models (Claude Haiku, Sonnet, Opus)
- **Fully local option** — works 100% offline with Ollama + Kokoro TTS + Whisper STT
- **GPU-accelerated TTS** via Kokoro-ONNX — near-instant synthesis on NVIDIA GPUs, runs in a separate subprocess to avoid DLL conflicts with Qt
- **Pipelined TTS playback** — while sentence N is playing, sentence N+1 is already being synthesized, eliminating gaps between sentences
- **Speech-to-text** via faster-whisper, running in a separate process to avoid DLL conflicts
- **File attachments** — send images (PNG, JPG, WEBP, GIF), PDFs, and plain text/code files
- **Persistent memory** — JARVIS remembers facts about you across conversations
- **Conversation history** — all conversations saved locally and accessible from the history panel
- **Think mode** — enables chain-of-thought reasoning (supported by Ollama qwen models only)
- **TTS toggle locked during boot/greeting/response** — prevents accidental toggling while audio is in progress
- **Input locking** — input is disabled during boot and greeting animations
- **ESC to stop** — press ESC at any time to instantly stop TTS playback and clear the queue
- **Auto-scroll** toggle, always-on-top toggle, stay-on-top window mode
- **PC control** — launch apps, open websites, check system stats, control power settings, open files and folders — all by just asking
- **API key file** — Anthropic API key stored in `jarvis_data/api_key.txt`, never hardcoded in source

---

## Project Structure

```
J.A.R.V.I.S-AI/
├── jarvis.pyw              # Main application (run with pythonw, no console)
├── start_jarvis.vbs        # Silent launcher script for Task Scheduler
├── README.md
├── jarvis_tts/             # Kokoro TTS model, voice files and worker (download separately)
│   ├── jarvis_tts_worker.py        # TTS subprocess worker (do not run directly)
│   ├── kokoro-v1.0.fp16-gpu.onnx  # Kokoro model (GPU, recommended)
│   ├── voices-v1.0.bin            # Kokoro voice pack
│   └── cough.wav                  # Cough sound effect for throat-clearing animation
├── jarvis_stt/             # Whisper STT model files and worker (download separately)
│   ├── jarvis_stt_worker.py        # STT subprocess worker (do not run directly)
│   ├── config.json
│   ├── model.bin
│   ├── tokenizer.json
│   └── vocabulary.txt
├── jarvis_data/            # Auto-created at runtime
│   ├── settings.json       # Saved settings
│   ├── memory.json         # Persistent memory facts
│   ├── api_key.txt         # Your Anthropic API key (create this manually)
│   └── conversations/      # Saved conversation JSON files
└── assets/
```

---

## Requirements

Personally running on Windows 11 with 16 GB DDR4 3200MHz and an RTX 3050 6GB (laptop). Getting 25 tok/sec for the 4b and 15 tok/sec for the 9b. TTS synthesis with the GPU model is near-instant but does come at a cost if tok/sec.

---

## Installation

### 1. Python

Download and install Python 3.11 from [python.org](https://www.python.org/downloads/).

During installation, make sure to check **"Add Python to PATH"**.

Verify installation:
```bash
python --version
```

---

### 2. Python Packages

Open a terminal (Command Prompt or PowerShell) and run:

```bash
pip install PyQt6 faster-whisper pyaudio kokoro-onnx onnxruntime-gpu sounddevice keyboard numpy psutil
```

> **Note:** `onnxruntime-gpu` is a large download (~207 MB). If it times out, use:
> ```bash
> pip install onnxruntime-gpu --timeout 300
> ```

**What each package does:**

| Package | Purpose |
|---|---|
| `PyQt6` | GUI framework — the entire window and UI |
| `faster-whisper` | Speech-to-text transcription (Whisper model) |
| `pyaudio` | Microphone audio capture |
| `kokoro-onnx` | Text-to-speech voice synthesis (Kokoro model) |
| `onnxruntime-gpu` | GPU-accelerated ONNX runtime for Kokoro TTS |
| `sounddevice` | Zero-latency audio playback |
| `keyboard` | Global hotkey listener (Right Alt for STT) |
| `numpy` | Audio buffer manipulation |
| `psutil` | Live system stats — CPU, RAM, battery, disk |

> **Note for pyaudio on Windows:** If `pip install pyaudio` fails, download the prebuilt wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install it with `pip install <downloaded_file>.whl`.

---

### 3. Ollama (Local LLM)

Ollama lets you run large language models completely locally on your machine.

1. Download Ollama from [ollama.com](https://ollama.com/)
2. Run the installer
3. Verify it works:
```bash
ollama --version
```

JARVIS will automatically start `ollama serve` when it launches via the VBS script, so you do not need to start it manually.

---

### 4. Ollama Models

JARVIS is preconfigured for **Qwen 3.5** models. Pull them with:

```bash
# Smaller, faster (recommended for most PCs)
ollama pull qwen3.5:4b

# Larger, smarter (requires ~16 GB RAM)
ollama pull qwen3.5:9b
```

To use a different model, edit the `PROVIDERS` dictionary at the top of `jarvis.pyw`:

```python
PROVIDERS = {
    "LOCAL 4b":  {"type": "ollama", "model": "qwen3.5:4b"},
    "LOCAL 9b":  {"type": "ollama", "model": "qwen3.5:9b"},
    # Add your own:
    "LLAMA":     {"type": "ollama", "model": "llama3.2:3b"},
}
```

You can browse all available models at [ollama.com/library](https://ollama.com/library).

---

### 5. Kokoro TTS Voices

JARVIS uses [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx) for voice synthesis. The model files are **not included in the repo** and must be downloaded manually.

#### Step 1 — Create the voices folder

Inside your Jarvis project folder, create a folder called `jarvis_tts/` if it doesn't already exist.

#### Step 2 — Download the model files

Download both files and place them in `jarvis_tts/`:

| File | Download |
|---|---|
| `kokoro-v1.0.fp16-gpu.onnx` | [GitHub Releases](https://github.com/thewh1teagle/kokoro-onnx/releases) |
| `voices-v1.0.bin` | [GitHub Releases](https://github.com/thewh1teagle/kokoro-onnx/releases) |

> **GPU vs CPU model:** `fp16-gpu.onnx` requires an NVIDIA GPU with CUDA. If you don't have one, download `kokoro-v1.0.int8.onnx` instead and update `MODEL_FILE` in `TTSEngine` inside `jarvis.pyw`. The GPU model synthesizes audio near-instantly; the CPU model takes 2–3 seconds per sentence.

#### Step 3 — (Optional) Add a cough sound

Download any short cough `.wav` file (e.g. from [freesound.org](https://freesound.org) — filter by CC0 license) and place it in `jarvis_tts/` as `cough.wav`. JARVIS will play it automatically when the throat-clearing animation starts.

After setup, your `jarvis_tts/` folder should look like this:

```
jarvis_tts/
├── jarvis_tts_worker.py
├── kokoro-v1.0.fp16-gpu.onnx
├── voices-v1.0.bin
└── cough.wav          (optional)
```

#### Available voices

The two built-in voices are:

| Key | Voice ID | Style |
|---|---|---|
| `MALE` | `bm_george` | British male |
| `FEMALE` | `af_heart` | American female |

To add more voices, browse the [Kokoro voice list](https://github.com/thewh1teagle/kokoro-onnx) and add entries to the `VOICES` dictionary in `jarvis.pyw`:

```python
VOICES = {
    "MALE":   {"id": "bm_george"},
    "FEMALE": {"id": "af_heart"},
    # Add your own:
    "BELLA":  {"id": "af_bella"},
}
```

---

### 6. STT Model (Whisper)

JARVIS uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for speech recognition. The model files are **not included in the repo** and must be downloaded manually.

#### Step 1 — Create the STT folder

Inside your Jarvis project folder, create a folder called `jarvis_stt/`.

#### Step 2 — Download the model files

JARVIS uses the `base` Whisper model by default. Download all of the following files and place them inside `jarvis_stt/`:

| File | Download Link |
|---|---|
| `config.json` | [Download](https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json) |
| `model.bin` | [Download](https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin) |
| `tokenizer.json` | [Download](https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json) |
| `vocabulary.txt` | [Download](https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.txt) |
| `preprocessor_config.json` | [Download](https://huggingface.co/Systran/faster-whisper-base/resolve/main/preprocessor_config.json) |

Or visit the [faster-whisper-base model page](https://huggingface.co/Systran/faster-whisper-base) on Hugging Face → **"Files and versions"** tab → download each file.

After downloading, your `jarvis_stt/` folder should look like this:

```
jarvis_stt/
├── jarvis_stt_worker.py
├── config.json
├── model.bin
├── tokenizer.json
├── vocabulary.txt
└── preprocessor_config.json
```

#### Step 3 — No path configuration needed

`STT_MODEL_DIR` is automatically set to the `jarvis_stt/` folder inside your project directory. As long as you place the model files there, no changes to `jarvis.pyw` are required.

#### Available model sizes

| Model | Size | Speed | Accuracy | Hugging Face Link |
|---|---|---|---|---|
| `base` | ~150 MB | Fast | Good | [faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base) |
| `small` | ~500 MB | Medium | Better | [faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small) |
| `medium` | ~1.5 GB | Slow | Great | [faster-whisper-medium](https://huggingface.co/Systran/faster-whisper-medium) |
| `large-v3` | ~3 GB | Slowest | Best | [faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) |

---

### 7. Anthropic API Key (Optional)

If you want to use Claude cloud models (Haiku, Sonnet, Opus), you need an Anthropic API key.

1. Sign up at [console.anthropic.com](https://console.anthropic.com/)
2. Go to **API Keys** and create a new key
3. Create a file called `api_key.txt` inside your `jarvis_data/` folder
4. Paste your key into the file and save — nothing else, just the key:
```
sk-ant-api03-...
```

> The key is never hardcoded in the source.

> **Pricing:** Anthropic charges per token. Haiku is the cheapest, Opus is the most expensive. Check [anthropic.com/pricing](https://www.anthropic.com/pricing) for current rates. You do NOT need an API key to use local Ollama models.

---

## Configuration

All tuneable settings are at the top of `jarvis.pyw`:

```python
# Window size
WIN_W, WIN_H = 460, 780

# Max conversation history sent to the model (older messages are trimmed)
MAX_HISTORY = 40

# JARVIS system personality prompt
JARVIS_SYSTEM = "You are J.A.R.V.I.S ..."

# Greeting shown and spoken on startup and new chat
GREETING_TEXT = "Hello, sir.\n\n..."

# Boot animation lines (edit freely — any line starting with > is spoken by TTS)
LINES = [
    ("◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈", ACCENT),
    ("  J.A.R.V.I.S  v4.1  //  STARK INDUSTRIES", TEXT),
    ("  > INITIALIZING NEURAL MATRIX........", OK_COL),
    ...
]
```

Settings that are saved automatically between sessions (via `jarvis_data/settings.json`):
- Selected provider/model
- TTS on/off and selected voice
- Think mode on/off
- Auto-scroll on/off
- Always-on-top on/off

---

## Running JARVIS

### Option A — Direct (with console window, good for debugging)

```bash
python jarvis.pyw
```

### Option B — Silent (no console window, recommended for daily use)

```bash
pythonw jarvis.pyw
```

### Option C — Via VBS launcher (recommended for auto-launch)

Double-click `start_jarvis.vbs`. This silently starts Ollama and then launches JARVIS with no console window.

---

## Auto-Launch on Login (Windows Task Scheduler)

This sets up JARVIS to launch automatically every time you log into Windows (after typing your password), not at system boot.

### Step 1 — Create the VBS launcher

Make sure `start_jarvis.vbs` is in the same folder as `jarvis.pyw`. It should contain:

```vbscript
Dim shell
Set shell = CreateObject("WScript.Shell")

' Start Ollama silently
shell.Run "ollama serve", 0, False

' Wait for Ollama to initialize
WScript.Sleep 1500

' Launch JARVIS with no console window
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
shell.Run "pythonw """ & scriptDir & "jarvis.pyw""", 0, False
```

### Step 2 — Open Task Scheduler

Press `Win + R`, type `taskschd.msc`, press Enter.

### Step 3 — Create a new task

In the right panel, click **"Create Task"** (not "Create Basic Task").

### Step 4 — General tab

- **Name:** `JARVIS`
- Select **"Run only when user is logged on"**
- Tick **"Run with highest privileges"**

### Step 5 — Triggers tab

- Click **"New"**
- **Begin the task:** `On workstation unlock`
- Make sure your user account is selected
- Click **OK**

> Using "On workstation unlock" instead of "At log on" ensures JARVIS only launches after you type your password, not during the boot process before login.

### Step 6 — Actions tab

- Click **"New"**
- **Action:** `Start a program`
- **Program/script:** Full path to your VBS file, e.g.:
  ```
  C:\Users\YourName\Desktop\Jarvis\start_jarvis.vbs
  ```
- Leave **"Add arguments"** empty
- Click **OK**

### Step 7 — Conditions tab

- Uncheck **"Start the task only if the computer is on AC power"**

### Step 8 — Settings tab

- Make sure **"Allow task to be run on demand"** is checked
- Set **"If the task is already running"** to **"Do not start a new instance"**

### Step 9 — Save and test

Click **OK**. Test it by locking your PC with `Win + L` and then typing your password — JARVIS should launch automatically.

---

## Usage Guide

### Sending Messages

Type your message in the green input box at the bottom and press **Enter** to send. Press **Shift + Enter** for a new line without sending.

**Global hotkey:** Press `Ctrl + Alt + J` from anywhere on your PC to instantly show or hide the JARVIS window — no need to click the taskbar.

---

### Switching Models

Use the **model dropdown** at the top of the window to switch between:

| Label | Type | Model |
|---|---|---|
| LOCAL 4b | Ollama (local) | qwen3.5:4b |
| LOCAL 9b | Ollama (local) | qwen3.5:9b |
| HAIKU | Anthropic (cloud) | claude-haiku-4-5 |
| SONNET | Anthropic (cloud) | claude-sonnet-4-5 |
| OPUS | Anthropic (cloud) | claude-opus-4-5 |

> LOCAL models require Ollama to be running and the model to be pulled. HAIKU/SONNET/OPUS require a valid Anthropic API key in `jarvis_data/api_key.txt`.

---

### Voice (TTS)

- TTS is controlled via the **settings gear (⚙)** in the top-right corner
- Toggle TTS on/off and switch voices (MALE/FEMALE) from the settings menu
- **TTS and voice cannot be toggled during boot, greeting, or while a response is playing** — changes take effect after the current audio finishes
- Press **ESC** at any time to immediately stop TTS playback and clear the entire queue
- **Boot sequence:** Matrix animation plays while all boot lines are pre-synthesized. Once ready, typewriter and voice start simultaneously for each line
- **Greeting:** Blinking cursor shows while greeting audio is pre-synthesized. Text and voice then start together
- **Responses:** `CLEARING THROAT ●○○` animation (with cough sound) shows while the first sentence is being synthesized. The moment it's ready, text floods in and voice starts at the same time. Subsequent sentences follow at their own pace

---

### Speech-to-Text (STT)

- **Hold Right Alt** to record your voice; release to transcribe
- Or click the **🎤 microphone button**
- Transcription is done locally using faster-whisper — no audio is sent to any server
- STT runs in a separate process to avoid conflicts with the GUI

---

### Attaching Files

Click the **[ + ]** button to attach files to your message. Supported types:

| Type | Extensions |
|---|---|
| Images | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` |
| PDFs | `.pdf` |
| Text / Code | `.txt`, `.py`, `.js`, `.ts`, `.html`, `.css`, `.md`, `.json`, `.csv`, `.xml`, `.yaml`, `.yml`, `.sh`, `.bat`, `.c`, `.cpp`, `.h`, `.java`, `.rs`, `.go`, `.rb`, `.php` |

---

### Memory

JARVIS has a persistent memory system. You can store facts that will be included in every conversation.

- Click **[ MEM ]** in the top bar to open and view memory
- Add facts using the `/remember` command before your message, e.g.: `/remember My name is Hadi`
- Memory is saved to `jarvis_data/memory.json` and persists between sessions
- Memory is automatically included in every message sent to the model

---

### Conversation History

- All conversations are automatically saved to `jarvis_data/conversations/`
- Click **[ HIST ]** in the top bar to browse and load previous conversations

---

### Think Mode

Think mode enables extended chain-of-thought reasoning — the model thinks through problems step by step before responding. The thinking process is shown in a dimmed block above the final answer.

- Toggle think mode via the **settings gear (⚙)** menu
- Supported by: Ollama qwen3.5 models only

---

### Stopping a Response

- Click **[ ABORT ]** to stop the current AI response mid-stream
- Press **ESC** to stop TTS playback immediately and clear all queued sentences

---

### PC Control

JARVIS can control your PC directly. Just ask naturally and it will execute the right command.

**Launching apps** — say the app name and JARVIS opens it:
> *"Open Spotify"*, *"Launch VS Code"*, *"Open Steam"*, *"Start Blender"*

**Launching games:**
> *"Launch Rocket League"*, *"Open RDR2"*, *"Start Sekiro"*, *"Open Minecraft"*

**Web search / open URL:**
> *"Search YouTube for lo-fi beats"*, *"Open github.com"*, *"Google how to reverse a linked list"*

**System info** — JARVIS reads your live stats and reports them:
> *"How's my RAM?"*, *"What's my CPU usage?"*, *"Check my battery"*

**Power management:**
> *"Switch to high performance mode"* — best for gaming
> *"Switch to balanced mode"* — normal use

**System commands:**
> *"Lock the screen"*, *"Put the PC to sleep"*, *"Shut down"*, *"Restart"*
> Shutdown and restart require a confirmation click before executing.

**File & folder operations:**
> *"Open my Downloads folder"*, *"Open my Documents"*, *"Find report.pdf and open it"*

---

## Customisation

**Change the greeting:**
```python
GREETING_TEXT = (
    "Hello, sir.\n\n"
    "JARVIS online and fully operational. "
    "All systems running within normal parameters.\n\n"
    "How may I assist you today?"
)
```

**Change the boot animation lines:**
Edit the `LINES` list inside the `BootWidget` class. Any line starting with `>` will be pre-synthesized and spoken in sync with the typewriter. Non-`>` lines type at default speed silently.

**Change the AI personality:**
```python
JARVIS_SYSTEM = (
    "You are J.A.R.V.I.S (Just A Rather Very Intelligent System), "
    "the personal AI assistant. Be concise, direct, and highly capable. "
    "Address the user as 'sir' occasionally. No unnecessary preamble."
)
```

**Change window size:**
```python
WIN_W, WIN_H = 460, 780
```

**Change colors:**
All colors are defined in the color palette section near the top of `jarvis.pyw`:
```python
BG     = "#030a10"   # Main background
ACCENT = "#00d4ff"   # Cyan accent color
OK_COL = "#00ffaa"   # Green (user messages, status OK)
WARN   = "#ffaa00"   # Orange warnings
ERR    = "#ff4444"   # Red errors
```

**Switch TTS model (CPU vs GPU):**
```python
# In TTSEngine class inside jarvis.pyw:
MODEL_FILE = "kokoro-v1.0.fp16-gpu.onnx"   # GPU (recommended, NVIDIA only)
MODEL_FILE = "kokoro-v1.0.int8.onnx"        # CPU fallback
```

---

**Add or remove apps from the launcher:**

Find the `APPS` dictionary near the top of `jarvis.pyw`. Add a new entry with the name you want to say as the key and the full path or URI as the value:

```python
APPS = {
    "zen":        r"C:\Program Files\Zen Browser\zen.exe",
    "spotify":    r"C:\Users\YourName\AppData\Roaming\Spotify\Spotify.exe",
    # Add your own:
    "notepad":    "notepad.exe",
    "discord":    r"C:\Users\YourName\AppData\Local\Discord\Update.exe",
    "mygame":     "steam://rungameid/YOUR_GAME_ID",
}
```

To find a Steam game's ID, right-click it in your Steam library → **Properties** → the number in the URL is the game ID.

You can add as many aliases as you want for the same app:
```python
"vscode":  r"C:\...\Code.exe",
"code":    r"C:\...\Code.exe",
"editor":  r"C:\...\Code.exe",
```

After adding a new app, also update the app list in `JARVIS_SYSTEM` so the model knows about it.

---

**Add folders JARVIS can search for files in:**

Find the `ALLOWED_DIRS` list near the top of `jarvis.pyw`:
```python
ALLOWED_DIRS = [
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Downloads"),
    # Add your own:
    r"C:\Users\YourName\Projects",
]
```

---

## Troubleshooting

**JARVIS won't start / Python not found**
- Make sure Python is installed and added to PATH
- Try running `python --version` in a terminal to confirm

**"Ollama not found" error**
- Install Ollama from [ollama.com](https://ollama.com/)
- Make sure `ollama` is accessible from the terminal: `ollama --version`

**Model not responding / "OFFLINE" status**
- Open a terminal and run `ollama serve` manually to see error output
- Make sure you have pulled the model: `ollama pull qwen3.5:4b`

**TTS not working / "TTS FAILED" in status bar**
- Check that `kokoro-v1.0.fp16-gpu.onnx` and `voices-v1.0.bin` are in `jarvis_tts/`
- Make sure `kokoro-onnx` and `onnxruntime-gpu` are installed
- If you don't have an NVIDIA GPU, switch to the CPU model (`kokoro-v1.0.int8.onnx`) and install `onnxruntime` instead of `onnxruntime-gpu`
- Check the console for `[TTS] Worker failed:` errors

**TTS is slow / long pause before voice starts**
- Make sure you're using the GPU model (`fp16-gpu.onnx`) and `onnxruntime-gpu`
- Verify your GPU is being used: run `nvidia-smi` and check GPU memory usage increases when JARVIS speaks
- If VRAM is full (running a large LLM), the TTS worker may fall back to CPU automatically

**No cough sound**
- Make sure `cough.wav` is in `jarvis_tts/`
- The file must be a valid WAV file (not MP3 renamed to .wav)

**Anthropic API errors**
- Make sure `jarvis_data/api_key.txt` exists and contains only your API key with no extra spaces or newlines
- Make sure your Anthropic account has credits — check [console.anthropic.com](https://console.anthropic.com/)

**STT not working / microphone not detected**
- Make sure `pyaudio` is installed correctly
- Check your microphone is set as the default recording device in Windows Sound settings

**pyaudio install fails on Windows**
- Download the prebuilt wheel from [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)
- Install it: `pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl`

**App won't launch / "App not found"**
- Check the path in the `APPS` dictionary exactly matches the `.exe` location on your PC
- For Steam games use `steam://rungameid/GAME_ID`
- For Epic games right-click the desktop shortcut → Properties → copy the full Target URI

**Task Scheduler launches JARVIS at boot, not after login**
- Make sure the trigger is set to **"On workstation unlock"**

---

## License

This project is for personal use. J.A.R.V.I.S is a fictional character from Marvel's Iron Man. This project is not affiliated with Marvel, Disney, or Anthropic.

---

*"Sometimes you gotta run before you can walk." — Tony Stark*
