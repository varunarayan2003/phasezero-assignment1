# utils.py
"""
Utility functions:
1. Download YouTube videos (pytube)
2. Download direct MP4 links
3. Extract audio using ffmpeg (WAV 16kHz mono)
4. Unified download + extract function
"""

import os
import shutil
import tempfile
import subprocess
import requests


def download_file(url, dest_path, timeout=120):
    """Download any direct MP4 link using requests."""
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return dest_path


def download_youtube_video(youtube_url, dest_path):
    """Download YouTube video as MP4 using pytube."""
    from pytube import YouTube

    yt = YouTube(youtube_url)
    stream = (
        yt.streams.filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )

    if not stream:
        raise RuntimeError("No MP4 streams found for this YouTube video.")

    out_dir = os.path.dirname(dest_path)
    stream.download(output_path=out_dir, filename=os.path.basename(dest_path))

    return dest_path


def extract_audio_with_ffmpeg(video_path, out_audio_path):
    """
    Extract audio from video:
    - mono channel
    - 16kHz sampling rate
    - wav format
    Requires ffmpeg installed.
    """

    command = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        "-f", "wav",
        out_audio_path
    ]

    subprocess.check_call(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return out_audio_path


def download_video_then_extract_audio(url_or_path, is_local=False):
    """
    Main function used by app.py.

    If is_local=True:
        - treat url_or_path as a file path from uploaded file

    If is_local=False:
        - treat url_or_path as YouTube link or direct MP4 URL

    Returns:
        path to WAV audio file (16kHz mono)
    """

    tmpdir = tempfile.mkdtemp(prefix="video_")
    video_path = os.path.join(tmpdir, "video.mp4")

    # If file is uploaded locally:
    if is_local:
        shutil.copy(url_or_path, video_path)

    else:
        lower = url_or_path.lower()

        # YouTube link
        if "youtube.com" in lower or "youtu.be" in lower:
            download_youtube_video(url_or_path, video_path)

        # Direct MP4 link
        else:
            download_file(url_or_path, video_path)

    # Extract audio
    audio_path = os.path.join(tmpdir, "audio.wav")
    extract_audio_with_ffmpeg(video_path, audio_path)

    return audio_path
