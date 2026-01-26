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

def format_timestamp(seconds: float) -> str:
    """Converts seconds (float) to HH:MM:SS or MM:SS string."""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
