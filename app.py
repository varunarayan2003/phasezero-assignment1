import os
import tempfile
import re
import streamlit as st
from utils import download_video_then_extract_audio

try:
    import whisper
except Exception:
    whisper = None

st.set_page_config(page_title="Video Communication Analyzer", layout="centered")
st.title("🎤 Video Communication Analyzer — Whisper STT (Offline)")

# Inputs
url_input = st.text_input("YouTube/MP4 URL:")
uploaded_file = st.file_uploader("Or upload an MP4 file:", type=["mp4"])
analyze_btn = st.button("Analyze")

STOPWORDS = {
    "the","a","an","and","or","but","if","then","so","on","in","at","for","with","to","of",
    "is","are","was","were","be","this","that","these","those","it","its","as","by","from",
    "they","their","we","our","you","your","i","me","my","he","she","him","her"
}

FILLERS = {"um","uh","like","you","know","i","mean","so","actually","basically","ok","okay"}

sentence_split = re.compile(r'(?<=[.!?])\s+')


def calc_clarity(text):
    if not text.strip():
        return 0

    low = text.lower()
    words = re.findall(r"\w+", low)
    total = len(words)

    filler_count = sum(1 for w in words if w in FILLERS)
    filler_rate = (filler_count / max(1, total)) * 100

    sentences = [s.strip() for s in sentence_split.split(text) if s.strip()]
    avg_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))

    score = 90 - min(40, filler_rate * 2)

    if avg_len < 6:
        score -= (6 - avg_len) * 2
    if avg_len > 25:
        score -= (avg_len - 25)

    return max(0, min(100, int(score)))


def calc_focus_sentence(text):
    sentences = [s.strip() for s in sentence_split.split(text) if s.strip()]
    if not sentences:
        return text.strip()

    freq = {}
    for w in re.findall(r"\w+", text.lower()):
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1

    def score(s):
        tokens = re.findall(r"\w+", s.lower())
        return sum(freq.get(t, 0) for t in tokens)

    best_sentence = max(sentences, key=score)
    return best_sentence[:300]


# -----------------------------
# Whisper Transcription
# -----------------------------
def whisper_transcribe(audio_path: str) -> str:
    if whisper is None:
        raise RuntimeError(
            "The 'whisper' package is not installed. Install openai-whisper."
        )

    model_name = os.environ.get("WHISPER_MODEL", "base")
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return result.get("text", "")


# -----------------------------
# MAIN PROCESS
# -----------------------------
if analyze_btn:

    if not url_input and not uploaded_file:
        st.error("Enter a URL or upload a video file.")
        st.stop()

    temp_files = []

    try:
        # Extract Audio
        with st.spinner("Extracting audio..."):
            try:
                if uploaded_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                        tmp.write(uploaded_file.read())
                        video_path_local = tmp.name

                    audio_path = download_video_then_extract_audio(
                        video_path_local, is_local=True
                    )
                    temp_files.extend([video_path_local, audio_path])

                else:
                    audio_path = download_video_then_extract_audio(
                        url_input, is_local=False
                    )
                    temp_files.append(audio_path)

                st.success("Audio extracted successfully!")

            except Exception as e:
                st.error(f"Audio extraction failed: {e}")
                st.stop()

        # Whisper Transcription
        with st.spinner("Transcribing using Whisper (offline)..."):
            try:
                transcript = whisper_transcribe(audio_path)
                st.success("Transcription complete!")
                st.subheader("Transcript")
                st.write(transcript)
                st.download_button(
                    "Download Transcript",
                    data=transcript,
                    file_name="transcript.txt"
                )
            except Exception as e:
                st.error(f"Transcription failed: {e}")
                st.stop()

        # Analysis
        clarity = calc_clarity(transcript)
        focus = calc_focus_sentence(transcript)

        st.metric("Clarity Score", f"{clarity}%")
        st.write("### Communication Focus Sentence")
        st.write(focus)

    finally:
        for p in temp_files:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass
