import os
import re
import time
import logging
from typing import List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

from src.utils import VideoAnalysis, KeyTopic, TranscriptSegment, format_timestamp

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    A class to interact with the Google Gemini API for analyzing video transcripts
    or audio and generating structured summaries.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the GeminiAnalyzer with an optional API key.
        If no API key is provided, it attempts to load from environment variables.
        """
        if api_key:
            genai.configure(api_key=api_key)
        else:
            load_dotenv()
            configured_api_key = os.getenv('GOOGLE_API_KEY')
            if not configured_api_key:
                raise ValueError("No GOOGLE_API_KEY found. Please set it in .env file or pass during initialization.")
            genai.configure(api_key=configured_api_key)
        
        # Use 2.5 Flash for speed and context window
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("GeminiAnalyzer initialized with 'gemini-2.5-flash' model.")

    def _parse_gemini_output(self, gemini_output: str) -> VideoAnalysis:
        """
        Parses Gemini's text output into the Pydantic VideoAnalysis model.

        Args:
            gemini_output: The raw text output from the Gemini model.

        Returns:
            A VideoAnalysis object containing the parsed summary.
        """
        title = ""
        executive_summary = ""
        key_topics: List[KeyTopic] = []

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
                key_topic_match = re.match(r"^- \*\*\[(\d{2}:\d{2}(?:\:\d{2})?)\]\*\*\s*(.*)", line)
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
        
        if not title and executive_summary: # Final fallback, use executive summary as title
            title = executive_summary[:100] + "..." if len(executive_summary) > 100 else executive_summary

        return VideoAnalysis(title=title, executive_summary=executive_summary, key_topics=key_topics)

    def analyze_transcript_data(self, transcript_segments: List[TranscriptSegment]) -> VideoAnalysis:
        """
        Formats the list of transcript segments and sends them to Gemini for analysis.

        Args:
            transcript_segments: A list of TranscriptSegment objects.

        Returns:
            A VideoAnalysis object containing the structured summary.
        """
        logger.info("Formatting transcript data for Gemini analysis...")
        
        full_text = ""
        for segment in transcript_segments:
            time_str = format_timestamp(segment.start)
            full_text += f"[{time_str}] {segment.text}\n"

        logger.info(f"Sending {len(full_text)} characters to Gemini for transcript analysis...")

        prompt = (
            f"You are an expert video analyst. I will provide a transcript with timestamps. "
            f"Your task is to create a structured summary. "
            f"The video content begins with: {full_text[:500]}..." \
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
        
        try:
            response = self.model.generate_content(prompt)
            logger.info("Gemini response received for transcript analysis.")
            return self._parse_gemini_output(response.text)
        except Exception as e:
            logger.error(f"Error during Gemini transcript analysis: {e}", exc_info=True)
            raise

    def analyze_audio(self, audio_path: str) -> VideoAnalysis:
        """
        Uploads audio to Gemini for native listening and summarization.

        Args:
            audio_path: The file path to the audio to be analyzed.

        Returns:
            A VideoAnalysis object containing the structured summary.
        """
        logger.info(f"Uploading audio file '{audio_path}' to Gemini (may take a moment)...")
        
        try:
            audio_file = genai.upload_file(path=audio_path)
            
            while audio_file.state.name == "PROCESSING":
                logger.debug("Waiting for audio file to process...")
                time.sleep(5) # Wait a bit longer for audio processing
                audio_file = genai.get_file(audio_file.name)

            logger.info("Audio processed. Generating summary from audio...")
            
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
            
            response = self.model.generate_content([prompt, audio_file])
            logger.info("Gemini response received for audio analysis.")
            return self._parse_gemini_output(response.text)
        except Exception as e:
            logger.error(f"Error during Gemini audio analysis: {e}", exc_info=True)
            raise
        finally:
            # Clean up uploaded file from Gemini (optional, but good practice)
            if 'audio_file' in locals() and audio_file.state.name != "FAILED":
                genai.delete_file(audio_file.name)
                logger.info(f"Deleted temporary uploaded audio file: {audio_file.name}")
