"""
Step 4: Cut and edit the video using FFmpeg based on LLM decisions.
Takes the JSON from Qwen2-VL and produces final video clips.
"""

import subprocess
import os
import json
from pathlib import Path


def seconds_to_ffmpeg_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format for FFmpeg."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def cut_segment(
    input_path: str,
    output_path: str,
    start_seconds: float,
    end_seconds: float,
    remove_ranges: list[dict] = None
) -> bool:
    """
    Cut a segment from a video, optionally removing internal ranges.

    Args:
        input_path: Source video path
        output_path: Output clip path
        start_seconds: Segment start time
        end_seconds: Segment end time
        remove_ranges: List of {start_seconds, end_seconds} to cut out within this segment

    Returns:
        True if successful
    """
    duration = end_seconds - start_seconds

    if not remove_ranges:
        # Simple cut — fast and lossless-ish
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_seconds),
            "-i", input_path,
            "-t", str(duration),
            "-c", "copy",           # Copy stream (no re-encode, very fast)
            "-avoid_negative_ts", "1",
            output_path
        ]
        return _run_ffmpeg(cmd)

    else:
        # Need to remove internal segments — use complex filter
        # Filter out ranges that fall within this segment
        local_removes = []
        for r in remove_ranges:
            r_start = r["start_seconds"] - start_seconds
            r_end = r["end_seconds"] - start_seconds
            if r_start >= 0 and r_end <= duration:
                local_removes.append((max(0, r_start), min(duration, r_end)))

        if not local_removes:
            return cut_segment(input_path, output_path, start_seconds, end_seconds)

        return _cut_with_removes(input_path, output_path, start_seconds, duration, local_removes)


def _cut_with_removes(
    input_path: str,
    output_path: str,
    global_start: float,
    duration: float,
    remove_ranges: list[tuple]
) -> bool:
    """Cut segment and remove internal ranges using FFmpeg select filter."""

    # Build select filter to keep everything EXCEPT removed ranges
    keep_ranges = _invert_ranges(remove_ranges, duration)

    if not keep_ranges:
        print(f"[FFmpeg] WARNING: Nothing to keep after removing ranges")
        return False

    # Build concat filter
    filter_parts = []
    concat_inputs = []

    for i, (start, end) in enumerate(keep_ranges):
        abs_start = global_start + start
        seg_duration = end - start
        filter_parts.append(
            f"[0:v]trim=start={abs_start}:duration={seg_duration},setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={abs_start}:duration={seg_duration},asetpts=PTS-STARTPTS[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    n = len(keep_ranges)
    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-crf", "18",           # High quality
        output_path
    ]
    return _run_ffmpeg(cmd)


def _invert_ranges(remove_ranges: list[tuple], total_duration: float) -> list[tuple]:
    """Convert remove ranges into keep ranges."""
    sorted_removes = sorted(remove_ranges, key=lambda x: x[0])
    keep = []
    cursor = 0.0

    for start, end in sorted_removes:
        if cursor < start:
            keep.append((cursor, start))
        cursor = max(cursor, end)

    if cursor < total_duration:
        keep.append((cursor, total_duration))

    return keep


def process_all_segments(
    input_path: str,
    output_dir: str,
    analysis: dict
) -> list[str]:
    """
    Process all segments from LLM analysis and produce output clips.

    Args:
        input_path: Source video path
        output_dir: Directory for output clips
        analysis: Parsed JSON from Qwen2-VL

    Returns:
        List of output file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    segments = [s for s in analysis.get("segments", []) if s.get("keep", True)]
    cuts_to_remove = analysis.get("cuts_to_remove", [])

    if not segments:
        print("[FFmpeg] No segments to process!")
        return []

    output_files = []
    print(f"\n[FFmpeg] Processing {len(segments)} segments...")

    for i, seg in enumerate(segments):
        title = seg.get("title", f"segment_{i+1}")
        # Sanitize filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.strip().replace(" ", "_")

        output_filename = f"{i+1:02d}_{safe_title}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        start = seg["start_seconds"]
        end = seg["end_seconds"]

        print(f"\n[FFmpeg] Segment {i+1}/{len(segments)}: '{title}'")
        print(f"         {seconds_to_ffmpeg_time(start)} → {seconds_to_ffmpeg_time(end)}")

        success = cut_segment(
            input_path=input_path,
            output_path=output_path,
            start_seconds=start,
            end_seconds=end,
            remove_ranges=cuts_to_remove
        )

        if success:
            output_files.append(output_path)
            print(f"[FFmpeg] ✓ Saved: {output_filename}")
        else:
            print(f"[FFmpeg] ✗ Failed: {output_filename}")

    return output_files


def _run_ffmpeg(cmd: list[str]) -> bool:
    """Run an FFmpeg command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout per segment
        )
        if result.returncode != 0:
            print(f"[FFmpeg] Error: {result.stderr[-500:]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("[FFmpeg] Timeout!")
        return False
    except FileNotFoundError:
        print("[FFmpeg] ERROR: ffmpeg not found. Please install: https://ffmpeg.org/download.html")
        return False