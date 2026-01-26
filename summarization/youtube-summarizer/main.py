import argparse
import logging
import os
import json
import tempfile

from src.scraper import VideoScraper
from src.analyzer import GeminiAnalyzer
from src.utils import VideoAnalysis

# --- CONFIGURATION & Logging Setup ---
# Use an environment variable for the log file path or default to a temp location
LOG_FILE_PATH = os.getenv('AGENT_LOG_FILE', os.path.join(tempfile.gettempdir(), 'youtube_summarizer_agent.log'))
OUTPUT_JSON_PATH = os.getenv('AGENT_OUTPUT_JSON', 'output.json') # Default to project root

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Main function to parse arguments, orchestrate video scraping and analysis,
    and output the summary.
    """
    parser = argparse.ArgumentParser(description="Generate a summary of a YouTube video using AI.")
    parser.add_argument("youtube_url", type=str, help="The full URL of the YouTube video.")
    args = parser.parse_args()

    logger.info(f"Starting summarization for YouTube URL: {args.youtube_url}")

    scraper = VideoScraper()
    analyzer = GeminiAnalyzer() # API key handled internally by GeminiAnalyzer

    video_id = scraper.get_video_id(args.youtube_url)
    if not video_id:
        logger.error("Could not extract video ID from the provided URL. Exiting.")
        return

    video_analysis_result: Optional[VideoAnalysis] = None
    audio_file_path: Optional[str] = None

    # --- PLAN A: Fetch Transcript ---
    try:
        logger.info("Attempting Plan A: Fetching transcript...")
        transcript_segments = scraper.fetch_transcript(video_id)
        if transcript_segments:
            video_analysis_result = analyzer.analyze_transcript_data(transcript_segments)
            logger.info("Plan A successful. Generated summary from transcript.")
        else:
            logger.warning("Plan A failed: No transcript available or could not be fetched.")

    except Exception as e:
        logger.warning(f"Plan A failed with an error: {e}. Falling back to Plan B.", exc_info=True)

    # --- PLAN B: Download Audio and Analyze (if Plan A failed) ---
    if not video_analysis_result:
        logger.info("Attempting Plan B: Downloading audio for analysis...")
        try:
            # Use a temporary file for audio download
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                audio_file_path = tmp_audio_file.name
            
            downloaded_path = scraper.download_audio(args.youtube_url, output_path=audio_file_path)
            
            if downloaded_path and os.path.exists(downloaded_path):
                video_analysis_result = analyzer.analyze_audio(downloaded_path)
                logger.info("Plan B successful. Generated summary from audio.")
            else:
                logger.error("Plan B failed: Could not download audio or file does not exist.")
        except Exception as e:
            logger.error(f"Plan B failed with an error: {e}. Cannot generate summary.", exc_info=True)
        finally:
            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
                logger.info(f"Cleaned up temporary audio file: {audio_file_path}")

    # --- Output Result ---
    if video_analysis_result:
        try:
            json_output = video_analysis_result.model_dump_json(indent=4)
            with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
                f.write(json_output)
            logger.info(f"Generated VideoAnalysis JSON saved to: {OUTPUT_JSON_PATH}")
            print(json_output) # Also print to stdout for immediate feedback
        except Exception as e:
            logger.error(f"Error saving or printing JSON output: {e}", exc_info=True)
    else:
        logger.error("Failed to generate video analysis for the provided URL.")

if __name__ == "__main__":
    main()
