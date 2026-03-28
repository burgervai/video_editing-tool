"""
Step 1: Transcribe video using OpenAI Whisper
Produces word-level timestamps for precise cuts
"""
"""
Step 1: Transcribe video using OpenAI Whisper
Produces word-level timestamps for precise cuts
"""

import os
os.environ["PATH"] += r";C:\ffmpeg\ffmpeg-8.1-essentials_build\bin"

import whisper
import json
from pathlib import Path
import whisper
import json
from pathlib import Path


def transcribe_video(video_path: str, model_size: str = "base") -> dict:
    """
    Transcribe a video file using Whisper.
    
    Args:
        video_path: Path to the video file
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                    Larger = more accurate but slower
    
    Returns:
        dict with full transcript, segments with timestamps
    """
    print(f"[Whisper] Loading model: {model_size}")
    model = whisper.load_model(model_size)

    print(f"[Whisper] Transcribing: {video_path}")
    result = model.transcribe(
        video_path,
        word_timestamps=True,   # Get word-level timestamps
        verbose=False
    )

    # Structure the output cleanly
    segments = []
    for seg in result["segments"]:
        segments.append({
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
            "words": [
                {
                    "word": w["word"].strip(),
                    "start": round(w["start"], 2),
                    "end": round(w["end"], 2)
                }
                for w in seg.get("words", [])
            ]
        })

    transcript_data = {
        "language": result.get("language", "en"),
        "duration_seconds": segments[-1]["end"] if segments else 0,
        "full_text": result["text"].strip(),
        "segments": segments
    }

    print(f"[Whisper] Done. Detected language: {transcript_data['language']}")
    print(f"[Whisper] Total segments: {len(segments)}")
    return transcript_data


def save_transcript(transcript_data: dict, output_path: str):
    """Save transcript to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    print(f"[Whisper] Transcript saved to: {output_path}")


def format_transcript_for_llm(transcript_data: dict) -> str:
    """
    Format transcript into a clean string for the LLM prompt.
    Includes timestamps in [MM:SS] format.
    """
    lines = []
    for seg in transcript_data["segments"]:
        start = format_time(seg["start"])
        end = format_time(seg["end"])
        lines.append(f"[{start} --> {end}] {seg['text']}")
    return "\n".join(lines)


def format_time(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"