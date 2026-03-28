"""
Step 2: Extract keyframes from video for Qwen2-VL to analyze visually.
Samples frames at regular intervals to capture visual context (slide changes, etc.)
"""

import cv2
import base64
import os
from pathlib import Path


def extract_keyframes(
    video_path: str,
    output_dir: str,
    interval_seconds: int = 10,
    max_frames: int = 60
) -> list[dict]:
    """
    Extract frames from video at regular intervals.

    Args:
        video_path: Path to the video file
        output_dir: Directory to save extracted frames
        interval_seconds: Extract one frame every N seconds
        max_frames: Maximum number of frames to extract

    Returns:
        List of dicts with frame info: {timestamp, path, base64}
    """
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    print(f"[Keyframes] Video: {duration:.1f}s, FPS: {fps:.1f}, Total frames: {total_frames}")

    frame_interval = int(fps * interval_seconds)
    keyframes = []
    frame_count = 0

    while cap.isOpened() and len(keyframes) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            frame_filename = f"frame_{len(keyframes):04d}_{timestamp:.1f}s.jpg"
            frame_path = os.path.join(output_dir, frame_filename)

            # Resize to reduce memory/token usage (720p max)
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))

            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Encode to base64 for API
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            keyframes.append({
                "timestamp": round(timestamp, 2),
                "timestamp_fmt": format_time(timestamp),
                "path": frame_path,
                "base64": b64
            })

            print(f"[Keyframes] Extracted frame at {format_time(timestamp)}")

        frame_count += 1

    cap.release()
    print(f"[Keyframes] Extracted {len(keyframes)} frames total")
    return keyframes


def format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"