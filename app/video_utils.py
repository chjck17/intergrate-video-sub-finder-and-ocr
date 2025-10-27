"""Helpers for working with video files."""

import datetime

import cv2


def get_video_duration_opencv(video_path: str) -> str | None:
    """Return the duration of a video using OpenCV."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if fps == 0:
            return None

        duration_seconds = total_frames / fps
        timedelta_obj = datetime.timedelta(seconds=duration_seconds)
        hours, remainder = divmod(int(timedelta_obj.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception:
        return None
