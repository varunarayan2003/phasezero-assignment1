# app.py - Deepgram STT version
import os
import tempfile
import re
import streamlit as st
from utils import download_video_then_extract_audio
from deepgram import DeepgramClient, PrerecordedOptions
import requests

st.set_page_config(page_title="Video Communication Analyzer", layout="centered")
st.title("Video Communication Analyzer — Deepgram STT")

url_input = st.text_input("Enter YouTube or MP4 URL:")
uploaded_file = st.file_uploader("Or upload a video (.mp4)", type=["mp4"])
analyze_btn = st.button("Analyze")

STOPWORDS = {"the","a","an","and","or","but","if","then","so","on","in","at","for","with","to","of",
"is","are","was","were","be","this","that","these","those","it","its","as","by","from",
"they","their","we","our","you","your","i","me","my","he","she","him","her"}

FILLERS = {"um","uh","like","you know","i mean","so","actually","basically","ok","okay"}
sentence_split = re.compile(r'(?<=[.!?])\s+')

def calc_clarity(text):
    if not text.strip(): return 0
    low = text.lower()
    words = re.findall(r"\w+", low)
    total = len(words)
    filler_count = sum(low.count(f) for f in FILLERS)
    filler_rate = (filler_count / max(1, total)) * 100
    sentences = [s.strip() for s in sentence_split.split(text) if s.strip()]
    avg_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
    score = 90 - min(40, filler_rate * 2)
    if avg_len < 6: score -= (6 - avg_len) * 2
    if avg_len > 25: score -= (avg_len - 25)
    return max(0, min(100, int(score)))

def calc_focus(text):
    sentences = [s.strip() for s in sentence_split.split(text) if s.strip()]
    if not sentences: return text.strip()
    words = [w.lower() for w in re.findall(r"\w+", text)]
    freq = {}
    for w in words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    return max(sentences, key=lambda s: sum(freq.get(t,0) for t in re.findall(r"\w+", s.lower())))[:300]

def deepgram_transcribe(path):
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        st.error("Deepgram API key missing in Streamlit Secrets.")
        st.stop()
    dg = DeepgramClient(key)
    with open(path, "rb") as f:
        audio = f.read()
    opts = PrerecordedOptions(model="nova-2", smart_format=True)
    res = dg.listen.prerecorded.v("1").transcribe_bytes(audio, opts)
    return res["results"]["channels"][0]["alternatives"][0]["transcript"]

if analyze_btn:
    if not url_input and not uploaded_file:
        st.error("Provide a URL or upload a file.")
        st.stop()

    st.info("Extracting audio...")
    try:
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(uploaded_file.read())
                video_path = tmp.name
            audio_path = download_video_then_extract_audio(video_path, True)
        else:
            audio_path = download_video_then_extract_audio(url_input, False)
        st.success("Audio extracted.")
    except Exception as e:
        st.error(f"Audio extraction failed: {e}")
        st.stop()

    st.info("Transcribing using Deepgram...")
    try:
        transcript = deepgram_transcribe(audio_path)
        st.success("Transcription complete!")
        st.write(transcript)
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        st.stop()

    st.info("Analyzing...")
    clarity = calc_clarity(transcript)
    focus = calc_focus(transcript)
    st.metric("Clarity Score", f"{clarity}%")
    st.write("**Focus Sentence:**", focus)
