import os
import time
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise ValueError("No API Key found. Please set GOOGLE_API_KEY in .env file")

genai.configure(api_key=API_KEY)

# Use 1.5 Pro for power
model = genai.GenerativeModel('gemini-1.5-pro-latest')

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
    print(f"⬇️  Plan B: Downloading audio for {url}...")
    
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
        print("✅ Audio downloaded successfully.                         ")
        return output_filename
    except Exception as e:
        print(f"❌ Error downloading audio: {e}")
        return None

def analyze_transcript_data(transcript_list):
    """Formats the transcript and sends to Gemini."""
    print("🧠 Formatting transcript data...")
    
    full_text = ""
    for entry in transcript_list:
        text = entry.get('text', '')
        start = entry.get('start', 0.0)
        
        time_str = format_timestamp(start)
        full_text += f"[{time_str}] {text}\n"

    print(f"📤 Sending {len(full_text)} characters to Gemini...")

    # Using the more detailed script_prompt.md for better results
    with open('youtube/summarization/script_prompt.md', 'r') as f:
        prompt = f.read()

    prompt = prompt.replace("{{TRANSCRIPT}}", full_text)
    
    response = model.generate_content(prompt)
    return response.text

def analyze_audio(audio_path):
    """Uploads audio to Gemini for native listening."""
    print("🧠 Uploading audio to Gemini (may take a moment)...")
    
    # Let's use a context manager for the file upload
    audio_file = genai.upload_file(path=audio_path, display_name=audio_path)
    
    # Simplified polling loop
    while audio_file.state.name == "PROCESSING":
        print('.', end='', flush=True)
        time.sleep(2) # A slightly longer sleep to not spam the API
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise ValueError(f"🔴 Audio file processing failed: {audio_file.state}")

    print("\n✅ Audio processed. Generating summary...")
    
    # Using the more detailed repo_prompt.md for audio
    with open('youtube/summarization/repo_prompt.md', 'r') as f:
        prompt = f.read()
    
    response = model.generate_content([prompt, audio_file])

    # It's good practice to delete the file from the service when done
    genai.delete_file(audio_file.name)
    print(f"☁️  Cleaned up remote file: {audio_file.name}")
    
    return response.text

def run_agent(youtube_url):
    video_id = get_video_id(youtube_url)
    if not video_id:
        print("❌ Invalid YouTube URL")
        return

    print(f"🚀 Starting Agent for Video ID: {video_id}")

    # --- PLAN A: Fetch Transcript (Standard Method) ---
    try:
        print("▶️  Plan A: Fetching transcript...")
        # Standard, reliable way to get a transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        summary = analyze_transcript_data(transcript_list)
        print("\n" + "="*50)
        print(summary)
        print("="*50)
        return

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"ℹ️  Plan A failed: {e}. Transcript not available.")
    except Exception as e:
        print(f"⚠️  Plan A failed with an unexpected error: {e}")

    # --- PLAN B: Download Audio & Analyze ---
    print("\n🔄 Falling back to Plan B: Audio Analysis")
    try:
        audio_file = download_audio(youtube_url)
        if audio_file and os.path.exists(audio_file):
            try:
                summary = analyze_audio(audio_file)
                print("\n" + "="*50)
                print(summary)
                print("="*50)
            finally:
                # Ensure cleanup happens even if analysis fails
                os.remove(audio_file)
                print("🧹 Cleanup: Temporary audio file deleted.")
        else:
            print("❌ Plan B failed: Could not download audio.")

    except Exception as e:
        # Using a more specific error message for Plan B
        print(f"❌ Plan B failed during analysis: {e}")

# --- RUN IT ---
if __name__ == "__main__":
    # You can easily change the link here
    link = 'https://www.youtube.com/watch?v=GxDTx1bx-x0'
    run_agent(link)
