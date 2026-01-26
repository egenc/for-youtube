import streamlit as st
import subprocess
import sys

SCRIPT_PATH = "/home/valka/repo/youtube/summarization/agent_scraper.py"

st.set_page_config(
    page_title="YouTube Summarizer",
    page_icon="🎥",
    layout="centered"
)

st.title("🎥 YouTube Video Summarizer")
st.caption("Runs your existing Python agent")

youtube_url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

if st.button("Analyze", type="primary"):
    if not youtube_url:
        st.warning("Please enter a YouTube URL")
    else:
        with st.spinner("Analyzing video... this may take up to a minute"):
            try:
                result = subprocess.run(
                    [sys.executable, SCRIPT_PATH, youtube_url],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode != 0:
                    st.error("Agent failed")
                    st.code(result.stderr)
                else:
                    st.success("Analysis complete")

                    # If output is JSON
                    try:
                        st.json(result.stdout)
                    except Exception:
                        st.text(result.stdout)

            except Exception as e:
                st.error(str(e))
