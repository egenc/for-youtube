import os
import time
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from dotenv import load_dotenv
import argparse
import logging
import json
import re

from pydantic import BaseModel, Field
from typing import List

# --- Pydantic Schemas (Strict Enforcement) ---
class KeyTopic(BaseModel):
    timestamp: str = Field(..., description="The timestamp of the topic in MM:SS or HH:MM:SS format")
    topic: str = Field(..., description="A concise title or description of the topic discussed")

class VideoAnalysis(BaseModel):
    title: str = Field(..., description="A generated title for the summary")
    executive_summary: str = Field(..., description="A concise paragraph summarizing the video's main value proposition")
    key_topics: List[KeyTopic] = Field(..., description="A list of key moments and their timestamps")

class TranscriptSegment(BaseModel):
    start: float
    text: str

# --- CONFIGURATION & Logging ---
load_dotenv()

API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise ValueError("No API Key found. Please set GOOGLE_API_KEY in .env file")

genai.configure(api_key=API_KEY)

# Use 2.5 Flash for speed and context window
model = genai.GenerativeModel('gemini-2.5-flash')

LOG_FILE_PATH = '/home/valka/repo/youtube/summarization/agent_logs.txt'
OUTPUT_JSON_PATH = '/home/valka/repo/youtube/summarization/agent_output.json'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(LOG_FILE_PATH),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

def get_video_id(url):
    """Extracts video ID from URL."""
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None

def format_timestamp(seconds):
    """Converts seconds (float) to HH:MM:SS or MM:SS string."""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def download_audio(url, output_filename="audio.mp3"):
    """Downloads audio using yt-dlp (Plan B)."""
    logger.info(f"⬇️  Plan B: Downloading audio for {url}...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_filename.replace('.mp3', ''),
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info("✅ Audio downloaded successfully.")
        return output_filename
    except Exception as e:
        logger.error(f"❌ Error downloading audio: {e}")
        return None

def parse_gemini_output(gemini_output: str) -> VideoAnalysis:
    """Parses Gemini's text output into the Pydantic VideoAnalysis model."""
    title = ""
    executive_summary = ""
    key_topics = []

    # Regex to find title
    title_match = re.search(r"##\s*Title:\s*(.*)", gemini_output, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    # Regex to find Executive Summary
    executive_summary_match = re.search(r"##\s*📝 Executive Summary\n(.*?)(?=\n\n##\s*⏱️ Key Topics & Timestamps|\Z)", gemini_output, re.DOTALL | re.IGNORECASE)
    if executive_summary_match:
        executive_summary = executive_summary_match.group(1).strip()
    
    # Regex to find Key Topics section
    key_topics_section_match = re.search(r"##\s*⏱️ Key Topics & Timestamps\n(.*)", gemini_output, re.DOTALL | re.IGNORECASE)
    if key_topics_section_match:
        key_topics_text = key_topics_section_match.group(1)
        for line in key_topics_text.split('\n'):
            line = line.strip()
            key_topic_match = re.match(r"^- \*\*\[(\d{2}:\d{2}(?::\d{2})?)\]\*\*\s*(.*)", line)
            if key_topic_match:
                timestamp = key_topic_match.group(1)
                topic = key_topic_match.group(2).strip()
                key_topics.append(KeyTopic(timestamp=timestamp, topic=topic))
    
    # Fallback/refinement for title if not found with specific regex or if it's too short
    if not title:
        # Try to extract the first line as title if it doesn't start with '##'
        first_line_match = re.match(r"^(?!##)(.*)", gemini_output.split('\n')[0])
        if first_line_match:
            title = first_line_match.group(1).strip()
    
    # If title is still empty, and executive summary exists, use first sentence of summary
    if not title and executive_summary:
        first_sentence_summary = executive_summary.split('.')[0].strip()
        if first_sentence_summary:
            title = first_sentence_summary
            if len(title) > 100: # Prevent very long titles
                title = title[:97] + "..."

    return VideoAnalysis(title=title, executive_summary=executive_summary, key_topics=key_topics)

def analyze_transcript_data(transcript_object):
    """Formats the FetchedTranscript object and sends to Gemini."""
    logger.info("🧠 Formatting transcript data...")
    
    full_text = ""

    if hasattr(transcript_object, 'snippets'):
        entries = transcript_object.snippets
    else:
        entries = transcript_object

    for entry in entries:
        text = getattr(entry, 'text', '')
        start = getattr(entry, 'start', 0.0)
        
        time_str = format_timestamp(start)
        full_text += f"[{time_str}] {text}\n"

    logger.info(f"📤 Sending {len(full_text)} characters to Gemini for transcript analysis...")

    prompt = (
        f"You are an expert video analyst. I will provide a transcript with timestamps. "
        f"Your task is to create a structured summary. "
        f"The video is about: {full_text[:500]}..." \
        f"Output MUST be in the following format:\n"
        f"## Title: [A generated title for the summary]\n"
        f"## 📝 Executive Summary\n"
        f"[A concise paragraph summarizing the video's main value proposition]\n\n"
        f"## ⏱️ Key Topics & Timestamps\n"
        f"(A bulleted list of key moments and their exact timestamps found in the text)"
        f"- **[MM:SS]** Topic Description\n"
        f"- **[HH:MM:SS]** Another Topic Description\n\n"
        f"TRANSCRIPT DATA:\n{full_text}"
    )
    
    response = model.generate_content(prompt)
    logger.info("✅ Gemini response received for transcript analysis.")
    return parse_gemini_output(response.text)

def analyze_audio(audio_path):
    """Uploads audio to Gemini for native listening."""
    logger.info("🧠 Uploading audio to Gemini (may take a moment)...")
    
    audio_file = genai.upload_file(path=audio_path)
    
    while audio_file.state.name == "PROCESSING":
        logger.info('.', end='', flush=True)
        time.sleep(1)
        audio_file = genai.get_file(audio_file.name)

    logger.info("\n✅ Audio processed. Generating summary from audio...")
    
    prompt = (
        f"Listen to this audio clip from a YouTube video. "
        f"Create a structured summary with estimated timestamps. "
        f"Output MUST be in the following format:\n"
        f"## Title: [A generated title for the summary]\n"
        f"## 📝 Executive Summary\n"
        f"[A concise paragraph summarizing the video's main value proposition]\n\n"
        f"## ⏱️ Key Topics & Timestamps\n"
        f"(A bulleted list of key moments and their approximate timestamps)"
        f"- **[MM:SS]** Topic Description\n"
        f"- **[HH:MM:SS]** Another Topic Description"
    )
    
    response = model.generate_content([prompt, audio_file])
    logger.info("✅ Gemini response received for audio analysis.")
    return parse_gemini_output(response.text)

def run_agent(youtube_url) -> VideoAnalysis | None:
    video_id = get_video_id(youtube_url)
    if not video_id:
        logger.error("❌ Invalid YouTube URL provided.")
        return None

    logger.info(f"🚀 Starting Agent for Video ID: {video_id}")

    # --- PLAN A: Fetch Transcript (Using your specific library usage) ---
    try:
        logger.info("Attempting Plan A: Fetching transcript...")
        
        # Instantiate YouTubeTranscriptApi directly
        transcript_api_instance = YouTubeTranscriptApi()
        
        # This returns a FetchedTranscript object
        transcript_data = transcript_api_instance.fetch(video_id)
        
        analysis = analyze_transcript_data(transcript_data)
        logger.info("✅ Plan A successful. Generated summary from transcript.")
        return analysis

    except Exception as e:
        logger.warning(f"⚠️ Plan A failed. Error: {e}")

    # --- PLAN B: Download Audio (Approximate Timestamps) ---
    try:
        audio_file = download_audio(youtube_url)
        if audio_file and os.path.exists(audio_file):
            analysis = analyze_audio(audio_file)
            logger.info("✅ Plan B successful. Generated summary from audio.")
            os.remove(audio_file)
            logger.info("🧹 Cleanup: Temporary audio file deleted.")
            return analysis
        else:
            logger.error("❌ Plan B failed: Could not download audio or file does not exist.")
            return None

    except Exception as e:
        logger.error(f"❌ Plan B failed with error: {e}")
        return None

# --- Main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a summary of a YouTube video using AI.")
    parser.add_argument("youtube_url", type=str, help="The full URL of the YouTube video.")
    args = parser.parse_args()

    # Create the directory for logs and output if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)

    video_analysis_result = run_agent(args.youtube_url)

    if video_analysis_result:
        try:
            json_output = video_analysis_result.model_dump_json(indent=4)
            with open(OUTPUT_JSON_PATH, 'w') as f:
                f.write(json_output)
            logger.info(f"Generated VideoAnalysis JSON saved to: {OUTPUT_JSON_PATH}")
            print(json_output) # Output to stdout as well
        except Exception as e:
            logger.error(f"❌ Error saving or printing JSON output: {e}")
    else:
        logger.error("Failed to generate video analysis.")
