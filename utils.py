from pytube import YouTube
from moviepy.editor import VideoFileClip
import tempfile

def download_video_then_extract_audio(source, is_local=False):
    if is_local:
        video_path = source
    else:
        yt = YouTube(source)
        stream = yt.streams.filter(file_extension="mp4").first()
        video_path = stream.download()

    clip = VideoFileClip(video_path)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    clip.audio.write_audiofile(temp_audio.name)
    clip.close()

    return temp_audio.name
