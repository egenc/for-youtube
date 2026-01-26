# Role: Senior Python Engineer & AI Agent Architect

**Objective:**
Please keep functions exactly how they are as they are optimized. Convert the provided Jupyter Notebook code into a Python script designed to function as an AI Agent tool. 

**Input:**
The Python code from a Jupyter Notebook (provided below this prompt).

**Output:**
A single, complete Python script (`/home/valka/repo/youtube/summarization/agent_scraper.py`) that incorporates the following requirements.

---

## 1. Core Functionality
- **Input:** The script must accept a single command-line argument: a YouTube video URL.
- **Logging:** Create a log file in this path: `/home/valka/repo/youtube/summarization/agent_logs.txt`
- **Consider:** `ytt_api.fetch(video_id)`  returns something like `FetchedTranscript(snippets=[FetchedTranscriptSnippet(text="In this video, we'll be focusing on", start=0.08, duration=4.32), FetchedTranscriptSnippet(text='`
- **Output:** The script must output **only** valid JSON defined by the Pydantic schema below (unless in debug mode). Please also save this json here: `/home/valka/repo/youtube/summarization/agent_output.json`

## 2. Pydantic Schema (Strict Enforcement)
The output must adhere strictly to these Pydantic models. The AI (Gemini) must be instructed to generate JSON matching this schema.

```python
from pydantic import BaseModel, Field
from typing import List

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