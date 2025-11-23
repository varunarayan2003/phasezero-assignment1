# utils.py
from pytube import YouTube
from moviepy.editor import VideoFileClip
import tempfile
import os

def download_video_then_extract_audio(source, is_local=False):
    """
    Downloads a YouTube video or uses a local file,
    then extracts audio using moviepy (no ffmpeg binary needed).
    """
    if is_local:
        video_path = source
    else:
        yt = YouTube(source)
        stream = yt.streams.filter(file_extension="mp4").first()
        video_path = stream.download()

    # Extract audio using MoviePy (uses built-in ffmpeg)
    video = VideoFileClip(video_path)

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    audio_path = temp_audio.name

    video.audio.write_audiofile(audio_path)

    video.close()
    return audio_path
