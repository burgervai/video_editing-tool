# 🎬 Seminar Video Cutter
### Automated long-video editing using Whisper + Qwen2-VL + FFmpeg

---

## 📖 Table of Contents

- [What This Tool Does](#what-this-tool-does)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
  - [Windows](#windows-installation)
  - [macOS](#macos-installation)
  - [Linux](#linux-installation)
- [FFmpeg Setup (Windows)](#ffmpeg-setup-windows)
- [Running the Tool](#running-the-tool)
- [All Command Options](#all-command-options)
- [Customizing the Editing Prompts](#customizing-the-editing-prompts)
- [Output Files](#output-files)
- [Troubleshooting](#troubleshooting)
- [Hardware Guide](#hardware-guide)
- [FAQ](#faq)

---

## What This Tool Does

This tool takes a **long seminar, lecture, or meeting video** and automatically:

1. **Transcribes** the entire video with accurate word-level timestamps
2. **Analyzes** both the speech content and visual frames (slides, speaker changes)
3. **Decides** where to cut based on your editing instructions
4. **Produces** clean, trimmed video clips — one per topic/segment

You give it instructions in plain English like:
> *"Split by topic, remove all Q&A sections, keep clips under 10 minutes"*

And it handles the rest.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT VIDEO                            │
│                  (seminar.mp4, 1-3 hrs)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼                           ▼
┌──────────────────┐        ┌──────────────────────┐
│  WHISPER (STT)   │        │  KEYFRAME EXTRACTOR  │
│                  │        │                      │
│ • Transcribes    │        │ • Grabs 1 frame per  │
│   all speech     │        │   10 seconds         │
│ • Word-level     │        │ • Captures slide      │
│   timestamps     │        │   changes visually   │
└────────┬─────────┘        └──────────┬───────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
           ┌────────────────────────┐
           │       QWEN2-VL         │
           │  (Vision + Language)   │
           │                        │
           │ • Reads transcript     │
           │ • Sees keyframes       │
           │ • Follows your prompts │
           │ • Outputs cut decisions│
           └────────────┬───────────┘
                        │
                        ▼
           ┌────────────────────────┐
           │        FFMPEG          │
           │                        │
           │ • Cuts at exact times  │
           │ • Removes bad sections │
           │ • Saves output clips   │
           └────────────┬───────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     OUTPUT CLIPS                            │
│   01_Introduction.mp4                                       │
│   02_Core_Concepts.mp4                                      │
│   03_Live_Demo.mp4  ...                                     │
└─────────────────────────────────────────────────────────────┘
```

### Why two AI models?

| Model | What it contributes |
|-------|-------------------|
| **Whisper** | Exact word-level timestamps — knows precisely when each word was spoken, enabling frame-accurate cuts |
| **Qwen2-VL** | Sees both the visuals AND the transcript — can detect slide changes, topic shifts, awkward pauses, and off-topic sections |

Using only a text LLM would miss visual cues. Using only a vision model would miss precise timestamps. Together they give you both.

---

## Project Structure

```
video editing tool/
│
├── Main.py                        ← Entry point — run this
├── requirements.txt               ← Python dependencies
├── README.md                      ← This file
│
├── pipeline/
│   ├── __init__.py                ← Package marker (keep empty)
│   ├── transcriber.py             ← Whisper transcription step
│   ├── keyframe_extractor.py      ← Frame extraction step
│   ├── video_analyzer.py          ← Qwen2-VL analysis step
│   └── video_cutter.py            ← FFmpeg cutting step
│
├── input/                         ← Put your video files here
├── output/                        ← Finished clips appear here
│
└── work_<videoname>/              ← Auto-created per video
    ├── transcript.json            ← Whisper output (reusable)
    ├── analysis.json              ← Qwen2-VL decisions (reusable)
    └── keyframes/                 ← Extracted frame images
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |
| Python | 3.10 | 3.11 or 3.12 |
| RAM | 16 GB | 32 GB |
| GPU VRAM | 8 GB (for Qwen2-VL 7B) | 16 GB+ |
| Storage | 20 GB free | 50 GB free |
| FFmpeg | Required | Required |

> **No GPU?** You can use the smaller `Qwen/Qwen2-VL-2B-Instruct` model. It's less accurate but runs on CPU. Transcription with Whisper will also be slower on CPU — use `--whisper-model tiny` for speed.

---

## Installation Guide

### Windows Installation

**Step 1: Make sure Python 3.10+ is installed**
```powershell
python --version
```
If not installed, download from https://python.org

**Step 2: Create a virtual environment**
```powershell
cd "C:\Users\YourName\Desktop\video editing tool"
python -m venv venv
venv\Scripts\activate
```

**Step 3: Install Python dependencies**
```powershell
pip install -r requirements.txt
```

**Step 4: Install FFmpeg** — see [FFmpeg Setup (Windows)](#ffmpeg-setup-windows) below.

---

### macOS Installation

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg
brew install ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Linux Installation

```bash
# Install FFmpeg
sudo apt update
sudo apt install ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## FFmpeg Setup (Windows)

FFmpeg is a separate program that handles video reading and cutting. It must be installed independently.

**Step 1: Download FFmpeg**
```powershell
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "C:\Users\$env:USERNAME\Downloads\ffmpeg.zip"
```

**Step 2: Extract it**
```powershell
Expand-Archive -Path "C:\Users\$env:USERNAME\Downloads\ffmpeg.zip" -DestinationPath "C:\ffmpeg"
```

**Step 3: Find the exact path**
```powershell
dir C:\ffmpeg\ -Recurse -Filter ffmpeg.exe | Select-Object FullName
```
Note the path shown — it will look like `C:\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe`

**Step 4: Add to system PATH permanently (run as Administrator)**
```powershell
# Replace the path below with what Step 3 showed you
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\ffmpeg\ffmpeg-8.1-essentials_build\bin", "Machine")
```

**Step 5: Close and reopen PowerShell, then verify**
```powershell
ffmpeg -version
```

**If PATH isn't working in your current session**, add this line at the top of `pipeline\transcriber.py`:
```python
import os
os.environ["PATH"] += r";C:\ffmpeg\ffmpeg-8.1-essentials_build\bin"
```

---

## Running the Tool

### Basic — just give it a video
```powershell
python Main.py --video testing-1.mp4
```
> Make sure your video is inside the `input\` folder, or provide the full path.

### With custom editing instructions
```powershell
python Main.py --video testing-1.mp4 --prompt "Split into 10-minute segments. Remove all Q&A."
```

### Use a more accurate Whisper model
```powershell
python Main.py --video testing-1.mp4 --whisper-model medium
```

### Reuse existing transcript (skip re-transcribing)
```powershell
python Main.py --video testing-1.mp4 --transcript work_testing-1\transcript.json
```

### Reuse existing analysis (skip re-running Qwen2-VL)
```powershell
python Main.py --video testing-1.mp4 --analysis work_testing-1\analysis.json
```

### Use smaller model (no GPU / low VRAM)
```powershell
python Main.py --video testing-1.mp4 --qwen-model Qwen/Qwen2-VL-2B-Instruct
```

---

## All Command Options

| Flag | Default | Description |
|------|---------|-------------|
| `--video` | **required** | Path to input video file |
| `--output-dir` | `output` | Folder where output clips are saved |
| `--whisper-model` | `base` | Whisper size: `tiny` / `base` / `small` / `medium` / `large` |
| `--keyframe-interval` | `10` | Seconds between extracted keyframes |
| `--prompt` | none | Extra editing instructions appended to the default prompt |
| `--transcript` | none | Path to existing transcript JSON — skips Whisper step |
| `--analysis` | none | Path to existing analysis JSON — skips Qwen2-VL step |
| `--qwen-model` | `Qwen/Qwen2-VL-7B-Instruct` | Which Qwen2-VL variant to use |

### Whisper model comparison

| Model | Speed (CPU) | Accuracy | VRAM needed |
|-------|-------------|----------|-------------|
| `tiny` | Very fast | Low | ~1 GB |
| `base` | Fast | Good | ~1 GB |
| `small` | Medium | Better | ~2 GB |
| `medium` | Slow | Great | ~5 GB |
| `large` | Very slow | Best | ~10 GB |

Start with `base` — it works well for clear seminar audio.

---

## Customizing the Editing Prompts

Open `pipeline\video_analyzer.py` and edit these two variables:

### `DEFAULT_SYSTEM_PROMPT`
Controls the model's role and output format. Don't change this unless you know what you're doing — it defines the JSON structure the rest of the pipeline depends on.

### `DEFAULT_USER_PROMPT`
This is your **editing rulebook**. Change this freely. Examples:

**Split into YouTube-friendly clips:**
```
Split into segments of exactly 8-12 minutes.
Give each segment an engaging, clickable title.
Each segment must start and end at a natural sentence boundary.
Remove any filler or dead air longer than 3 seconds.
```

**Technical content only:**
```
Keep ONLY technical explanations and code demonstrations.
Remove all greetings, housekeeping announcements, and social discussion.
Remove Q&A unless the question is directly technical.
Segments should be 5-15 minutes long.
```

**Lecture-style chapters:**
```
Split the video at every topic change, like chapters in a textbook.
Name each segment with the topic being discussed.
Do not remove any content — just identify natural chapter boundaries.
Include Q&A as a final segment if present.
```

**Or pass instructions at runtime with `--prompt`:**
```powershell
python Main.py --video lecture.mp4 --prompt "Keep segments under 5 minutes. Focus on slides content only."
```

---

## Output Files

After running, you'll find:

### `output/` folder — your final clips
```
output/
├── 01_Introduction_and_Agenda.mp4
├── 02_Background_and_Motivation.mp4
├── 03_Core_Algorithm_Explained.mp4
├── 04_Live_Coding_Demo.mp4
└── 05_Results_and_Discussion.mp4
```

Each file is named with a number prefix (for ordering) and a descriptive title generated by the AI.

### `work_<videoname>/` folder — intermediate files
```
work_testing-1/
├── transcript.json       ← Full Whisper transcript with timestamps
├── analysis.json         ← Qwen2-VL cut decisions (human-readable)
└── keyframes/
    ├── frame_0000_0.0s.jpg
    ├── frame_0001_10.0s.jpg
    └── ...
```

The `analysis.json` is especially useful — open it to see exactly what the AI decided and why:
```json
{
  "segments": [
    {
      "title": "Introduction and Agenda",
      "start_seconds": 0.0,
      "end_seconds": 187.5,
      "keep": true,
      "reason": "Speaker introduces themselves and outlines the session topics"
    }
  ],
  "cuts_to_remove": [
    {
      "start_seconds": 45.2,
      "end_seconds": 78.0,
      "reason": "Long silence while speaker sets up screen share"
    }
  ],
  "summary": "A 90-minute seminar on machine learning fundamentals..."
}
```

You can edit this JSON manually and re-run with `--analysis` to adjust cuts without re-running the AI.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'pipeline'`
You're running from the wrong directory. Make sure you're inside the project folder:
```powershell
cd "C:\Users\YourName\Desktop\video editing tool"
python Main.py --video testing-1.mp4
```

### `FileNotFoundError: ffmpeg not found`
FFmpeg isn't in PATH. Either:
- Follow the [FFmpeg Setup](#ffmpeg-setup-windows) steps again
- Or add this to the top of `pipeline\transcriber.py`:
```python
import os
os.environ["PATH"] += r";C:\ffmpeg\ffmpeg-8.1-essentials_build\bin"
```

### `FP16 is not supported on CPU; using FP32 instead`
This is just a warning, not an error. It means you're running on CPU — everything will still work, just slower.

### `CUDA out of memory`
Your GPU doesn't have enough VRAM for the 7B model. Use the smaller one:
```powershell
python Main.py --video testing-1.mp4 --qwen-model Qwen/Qwen2-VL-2B-Instruct
```

### `video file not found`
Put your video inside the `input\` folder, or use the full path:
```powershell
python Main.py --video "C:\Users\Niloy\Videos\seminar.mp4"
```

### Analysis JSON has no segments
The AI couldn't parse the video properly. Try:
- Using a more accurate Whisper model: `--whisper-model small`
- Reducing the keyframe interval: `--keyframe-interval 5`
- Simplifying your custom prompt

### Output clips are empty or 0 bytes
FFmpeg ran but failed silently. Check that:
- The `output\` folder exists and is writable
- FFmpeg version is 4.0 or later: `ffmpeg -version`

---

## Hardware Guide

### Running on CPU only (no GPU)
Totally possible, but slow. For a 1-hour video expect:

| Step | Time on CPU |
|------|------------|
| Whisper `tiny` model | ~5 minutes |
| Whisper `base` model | ~15 minutes |
| Keyframe extraction | ~2 minutes |
| Qwen2-VL 2B (CPU) | ~30-60 minutes |
| FFmpeg cutting | ~2 minutes |

Use these flags for CPU mode:
```powershell
python Main.py --video seminar.mp4 --whisper-model tiny --qwen-model Qwen/Qwen2-VL-2B-Instruct
```

### Running with GPU (recommended)
For a 1-hour video with a mid-range GPU (RTX 3080):

| Step | Time with GPU |
|------|--------------|
| Whisper `base` | ~3 minutes |
| Keyframe extraction | ~1 minute |
| Qwen2-VL 7B | ~8 minutes |
| FFmpeg cutting | ~1 minute |
| **Total** | **~13 minutes** |

---

## FAQ

**Q: What video formats are supported?**
Any format FFmpeg supports — MP4, MKV, AVI, MOV, WEBM, and more.

**Q: How long can the input video be?**
No hard limit. Videos up to 3 hours work well. Beyond that, consider splitting the input manually first.

**Q: Will it re-download the AI models every time?**
No. After the first run, Whisper and Qwen2-VL models are cached locally. Whisper caches in `~/.cache/whisper/`, Qwen2-VL in `~/.cache/huggingface/`.

**Q: Can I reuse the transcript without re-running Whisper?**
Yes — use `--transcript work_videoname/transcript.json`. This is great for iterating on your editing prompt.

**Q: Can I edit the `analysis.json` manually?**
Yes! Open it, adjust the timestamps or remove segments you don't want, save it, then run:
```powershell
python Main.py --video testing-1.mp4 --analysis work_testing-1\analysis.json
```

**Q: The AI made bad cut decisions — how do I improve it?**
Edit `DEFAULT_USER_PROMPT` in `pipeline\video_analyzer.py` to be more specific. The more detail you give, the better the cuts. You can also manually edit `analysis.json` after the fact.

**Q: Can I use this for languages other than English?**
Yes — Whisper supports 99 languages and auto-detects the language. Qwen2-VL also supports multilingual input, though English prompts work best for instructions.

---

*Built with [OpenAI Whisper](https://github.com/openai/whisper) · [Qwen2-VL](https://github.com/QwenLM/Qwen2-VL) · [FFmpeg](https://ffmpeg.org)*