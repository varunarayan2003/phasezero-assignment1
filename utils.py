from pytube import YouTube
from moviepy.editor import VideoFileClip
import tempfile
import os


def download_video_then_extract_audio(source: str, is_local: bool = False) -> str:
    """
    Download or open a video, extract the audio, and return path to temp WAV file.
    """

    if is_local:
        video_path = source
    else:
        try:
            yt = YouTube(source)
            stream = yt.streams.filter(
                progressive=True, file_extension="mp4"
            ).order_by("resolution").desc().first()

            if stream is None:
                stream = yt.streams.filter(file_extension="mp4").first()

            video_path = stream.download()

        except Exception as e:
            raise RuntimeError(f"Failed to download video: {e}")

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    clip = None

    try:
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            raise RuntimeError("No audio stream found.")

        clip.audio.write_audiofile(temp_audio.name, verbose=False, logger=None)

    finally:
        if clip:
            try:
                clip.close()
            except:
                pass

        if not is_local and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

    return temp_audio.name
