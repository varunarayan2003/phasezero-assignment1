import os
import tempfile
import re
import streamlit as st
from utils import download_video_then_extract_audio
from deepgram import DeepgramClient
import requests

# ----------------------------------------------------
# Streamlit Setup
# ----------------------------------------------------
st.set_page_config(page_title="Video Communication Analyzer", layout="centered")
st.title("🎤 Video Communication Analyzer — Deepgram STT")

st.write("""
This app:
- Extracts audio from YouTube or MP4  
- Transcribes audio using **Deepgram Nova-2 (Cloud)**  
- Computes a **Clarity Score (0–100%)**  
- Detects the **Key Focus Sentence**  
""")

# ----------------------------------------------------
# Inputs
# ----------------------------------------------------
url_input = st.text_input("Enter YouTube or MP4 URL:")
uploaded_file = st.file_uploader("Or upload a video (.mp4)", type=["mp4"])
analyze_btn = st.button("Analyze")

# ----------------------------------------------------
# Heuristic scoring helpers
# ----------------------------------------------------
STOPWORDS = {
    "the","a","an","and","or","but","if","then","so","on","in","at","for","with","to","of",
    "is","are","was","were","be","this","that","these","those","it","its","as","by","from",
    "they","their","we","our","you","your","i","me","my","he","she","him","her"
}
FILLERS = {"um","uh","like","you know","i mean","so","actually","basically","ok","okay"}
sentence_split = re.compile(r'(?<=[.!?])\s+')

def calc_clarity(text):
    if not text.strip():
        return 0
    low = text.lower()
    words = re.findall(r"\w+", low)
    total = len(words)
    filler_count = sum(low.count(f) for f in FILLERS)
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

    return max(sentences, key=score)[:300]

# ----------------------------------------------------
# Deepgram Transcription (Correct v3 Method)
# ----------------------------------------------------
def deepgram_transcribe(audio_path):
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        st.error("Missing DEEPGRAM_API_KEY in Streamlit Secrets.")
        st.stop()

    dg = DeepgramClient(key)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = dg.listen.prerecorded(
        buffer=audio_bytes,
        mimetype="audio/wav",
        model="nova-2",
        smart_format=True
    )

    transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
    return transcript

# ----------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------
if analyze_btn:

    if not url_input and not uploaded_file:
        st.error("Please enter a URL or upload a file.")
        st.stop()

    # Step 1 — Extract audio
    st.info("Extracting audio...")
    try:
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(uploaded_file.read())
                video_path_local = tmp.name
            audio_path = download_video_then_extract_audio(video_path_local, is_local=True)
        else:
            audio_path = download_video_then_extract_audio(url_input, is_local=False)

        st.success("Audio extracted successfully!")
    except Exception as e:
        st.error(f"Audio extraction failed: {e}")
        st.stop()

    # Step 2 — Deepgram Transcription
    st.info("Transcribing using Deepgram...")
    try:
        transcript = deepgram_transcribe(audio_path)
        st.success("Transcription complete!")
        st.subheader("Transcript")
        st.write(transcript)
        st.download_button("Download Transcript", transcript, "transcript.txt")
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        st.stop()

    # Step 3 — Analysis
    st.info("Analyzing communication...")
    clarity = calc_clarity(transcript)
    focus = calc_focus_sentence(transcript)

    st.success("Analysis complete!")
    st.metric("Clarity Score", f"{clarity}%")
    st.write("**Communication Focus Sentence:**")
    st.write(focus)

