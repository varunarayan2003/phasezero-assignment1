# app.py
import os
import tempfile
import re
import streamlit as st
from utils import download_video_then_extract_audio
import whisper
import requests

# ----------------------------------------------------
# Streamlit UI
# ----------------------------------------------------
st.set_page_config(page_title="Video Communication Analyzer", layout="centered")
st.title("Video Communication Analyzer — Whisper CPU + Optional DeepSeek")

st.markdown("""
This app analyzes communication quality from a video:

- Extracts audio using FFmpeg  
- Transcribes speech offline using **OpenAI Whisper (CPU)**  
- Computes **Clarity Score (0–100%)**  
- Extracts **Communication Focus**  

If you set the environment variables:

```
DEEPSEEK_API_KEY
DEEPSEEK_API_URL
```

the app uses DeepSeek for improved scoring.
""")


# ----------------------------------------------------
# Inputs
# ----------------------------------------------------
url_input = st.text_input("Enter a YouTube or MP4 URL:")
uploaded_file = st.file_uploader("Or upload a video (.mp4)", type=["mp4"])
analyze_btn = st.button("Analyze")

# ----------------------------------------------------
# Scoring helpers
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

    # filler penalty
    filler_rate = (filler_count / max(1, total)) * 100

    # sentence length
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

    words = [w.lower() for w in re.findall(r"\w+", text)]
    freq = {}
    for w in words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1

    def score(s):
        tokens = re.findall(r"\w+", s.lower())
        return sum(freq.get(t, 0) for t in tokens)

    return max(sentences, key=score)[:300]


# ----------------------------------------------------
# Optional DeepSeek
# ----------------------------------------------------
def analyze_with_deepseek(transcript):
    key = os.getenv("DEEPSEEK_API_KEY")
    url = os.getenv("DEEPSEEK_API_URL")
    if not key or not url:
        return None

    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Return JSON: {clarity_score:int, focus_sentence:string}"},
                    {"role": "user", "content": transcript}
                ]
            },
            timeout=30
        )

        data = r.json()
        content = data["choices"][0]["message"]["content"]
        if content.strip().startswith("{"):
            return eval(content)
        return None
    except:
        return None


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
if analyze_btn:

    if not url_input and not uploaded_file:
        st.error("Please enter a URL or upload a file.")
        st.stop()

    # Step 1 — Extract Audio
    st.info("Extracting audio...")
    try:
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(uploaded_file.read())
                video_path = tmp.name
            audio_path = download_video_then_extract_audio(video_path, is_local=True)
        else:
            audio_path = download_video_then_extract_audio(url_input, is_local=False)

        st.success("Audio extracted.")
    except Exception as e:
        st.error(f"Audio extraction failed: {e}")
        st.stop()

    # Step 2 — Whisper Transcription (CPU)
    st.info("Transcribing audio with Whisper (CPU)...")

    try:
        model = whisper.load_model("small")
        result = model.transcribe(audio_path)
        transcript = result["text"]

        st.success("Transcription complete!")
        st.subheader("Transcript")
        st.write(transcript)
        st.download_button("Download transcript", transcript, "transcript.txt")

    except Exception as e:
        st.error(f"Transcription failed: {e}")
        st.stop()

    # Step 3 — Analysis
    st.info("Analyzing transcript...")

    ds = analyze_with_deepseek(transcript)

    if ds:
        clarity = ds["clarity_score"]
        focus = ds["focus_sentence"]
    else:
        clarity = calc_clarity(transcript)
        focus = calc_focus_sentence(transcript)

    st.success("Analysis complete!")
    st.metric("Clarity Score", f"{clarity}%")
    st.write("**Communication Focus:**", focus)
