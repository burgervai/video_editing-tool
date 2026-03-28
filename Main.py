"""
🎬 Seminar Video Cutter Pipeline
================================
Uses Whisper + Qwen2-VL + FFmpeg to automatically cut and edit long seminar videos.

Usage:
    python main.py --video path/to/seminar.mp4

    # With custom prompts:
    python main.py --video seminar.mp4 --prompt "Split by topic, keep only technical content"

    # Skip re-running Whisper (if transcript already exists):
    python main.py --video seminar.mp4 --transcript existing_transcript.json

    # Use faster/smaller Whisper model:
    python main.py --video seminar.mp4 --whisper-model base
"""

import argparse
import json
import os
import sys
from pathlib import Path

from pipeline.transcriber import transcribe_video, save_transcript, format_transcript_for_llm
from pipeline.keyframe_extractor import extract_keyframes
from pipeline.video_analyzer import VideoAnalyzer, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from pipeline.video_cutter import process_all_segments


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automatically cut and edit seminar videos using Whisper + Qwen2-VL"
    )
    parser.add_argument(
        "--video", required=True,
        help="Path to the input video file"
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory for output video clips (default: output)"
    )
    parser.add_argument(
        "--transcript", default=None,
        help="Path to existing transcript JSON (skip Whisper step)"
    )
    parser.add_argument(
        "--whisper-model", default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--keyframe-interval", type=int, default=10,
        help="Extract one keyframe every N seconds (default: 10)"
    )
    parser.add_argument(
        "--prompt", default=None,
        help="Custom editing instruction to append to the default prompt"
    )
    parser.add_argument(
        "--analysis", default=None,
        help="Path to existing analysis JSON (skip Qwen2-VL step)"
    )
    parser.add_argument(
        "--qwen-model", default="Qwen/Qwen2-VL-7B-Instruct",
        help="Qwen2-VL model to use"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Ensure standard directories exist
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    video_path = args.video
    if not os.path.exists(video_path):
        # Try looking in the 'input' folder if the path doesn't exist directly
        input_folder_path = os.path.join("input", video_path)
        if os.path.exists(input_folder_path):
            video_path = input_folder_path
        else:
            print(f"ERROR: Video file not found: {video_path}")
            sys.exit(1)

    video_name = Path(video_path).stem
    work_dir = f"work_{video_name}"
    os.makedirs(work_dir, exist_ok=True)

    print("=" * 60)
    print("🎬 Seminar Video Cutter Pipeline")
    print("=" * 60)
    print(f"Video: {video_path}")
    print(f"Output: {args.output_dir}")
    print()

    # ── Step 1: Transcribe ────────────────────────────────────────────────────
    transcript_path = os.path.join(work_dir, "transcript.json")

    if args.transcript and os.path.exists(args.transcript):
        print("[Step 1] Loading existing transcript...")
        with open(args.transcript) as f:
            transcript_data = json.load(f)
    else:
        print("[Step 1] Transcribing video with Whisper...")
        transcript_data = transcribe_video(video_path, model_size=args.whisper_model)
        save_transcript(transcript_data, transcript_path)

    transcript_text = format_transcript_for_llm(transcript_data)
    print(f"         Duration: {transcript_data['duration_seconds']:.0f}s")
    print(f"         Language: {transcript_data['language']}")
    print()

    # ── Step 2: Extract keyframes ─────────────────────────────────────────────
    keyframes_dir = os.path.join(work_dir, "keyframes")
    print("[Step 2] Extracting keyframes for visual analysis...")
    keyframes = extract_keyframes(
        video_path=video_path,
        output_dir=keyframes_dir,
        interval_seconds=args.keyframe_interval
    )
    print()

    # ── Step 3: Analyze with Qwen2-VL ─────────────────────────────────────────
    analysis_path = os.path.join(work_dir, "analysis.json")

    if args.analysis and os.path.exists(args.analysis):
        print("[Step 3] Loading existing analysis...")
        with open(args.analysis) as f:
            analysis = json.load(f)
    else:
        print("[Step 3] Analyzing with Qwen2-VL...")

        # Build prompt — add custom prompt if given
        user_prompt = DEFAULT_USER_PROMPT
        if args.prompt:
            user_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{args.prompt}"

        analyzer = VideoAnalyzer(model_name=args.qwen_model)
        analysis = analyzer.analyze(
            transcript_text=transcript_text,
            keyframes=keyframes,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )

        # Save analysis
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"         Analysis saved to: {analysis_path}")

    # Print summary
    segments = analysis.get("segments", [])
    keep_segments = [s for s in segments if s.get("keep", True)]
    cuts = analysis.get("cuts_to_remove", [])
    print(f"         Found {len(keep_segments)} segments to keep")
    print(f"         Found {len(cuts)} sections to remove")
    if analysis.get("summary"):
        print(f"\n         📝 Summary: {analysis['summary'][:200]}...")
    print()

    # ── Step 4: Cut video with FFmpeg ─────────────────────────────────────────
    print("[Step 4] Cutting video with FFmpeg...")
    output_files = process_all_segments(
        input_path=video_path,
        output_dir=args.output_dir,
        analysis=analysis
    )

    # ── Done! ─────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("✅ Done!")
    print(f"   Output clips ({len(output_files)}):")
    for f in output_files:
        size_mb = os.path.getsize(f) / (1024 * 1024) if os.path.exists(f) else 0
        print(f"   • {os.path.basename(f)} ({size_mb:.1f} MB)")
    print("=" * 60)


if __name__ == "__main__":
    main()