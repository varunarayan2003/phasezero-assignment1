# app.py
import os
import tempfile
import re
import streamlit as st
from utils import download_video_then_extract_audio
import stable_whisper
import requests

# ----------------------------------------------------
# Streamlit UI
# ----------------------------------------------------
st.set_page_config(page_title="Video Communication Analyzer", layout="centered")
st.title("Video Communication Analyzer — Stable Whisper + Optional DeepSeek")

st.markdown("""
This app:

- Extracts audio using FFmpeg  
- Transcribes speech offline using **Stable Whisper (CPU Safe)**  
- Computes a **Clarity Score (0–100%)**  
- Extracts the **Communication Focus**  

If you set the environment variables:

```
DEEPSEEK_API_KEY
DEEPSEEK_API_URL
```

the app uses DeepSeek for enhanced analysis.
""")


# ----------------------------------------------------
# Inputs
# ----------------------------------------------------
url_input = st.text_input("Enter YouTube or MP4 URL:")
uploaded_file = st.file_uploader("Or upload a video (.mp4)", type=["mp4"])
analyze_btn = st.button("Analyze")


# ----------------------------------------------------
# Heuristic Scoring Helpers
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
    st.info("Step 1 — Extracting audio...")
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
        st.error(f"Audio extraction error: {e}")
        st.stop()

    # Step 2 — Transcription using stable-ts
    st.info("Step 2 — Transcribing audio offline...")

    try:
        model = stable_whisper.load_model("small")
        result = model.transcribe(audio_path)
        transcript = result['text']

        st.success("Transcription complete!")
        st.subheader("Transcript")
        st.write(transcript)

        st.download_button("Download Transcript", transcript, "transcript.txt")

    except Exception as e:
        st.error(f"Transcription failed: {e}")
        st.stop()

    # Step 3 — Analysis
    st.info("Step 3 — Analyzing transcript...")

    ds_result = analyze_with_deepseek(transcript)

    if ds_result:
        clarity = ds_result["clarity_score"]
        focus = ds_result["focus_sentence"]
    else:
        clarity = calc_clarity(transcript)
        focus = calc_focus_sentence(transcript)

    st.success("Analysis complete!")
    st.metric("Clarity Score", f"{clarity}%")
    st.write("**Communication Focus:**", focus)
