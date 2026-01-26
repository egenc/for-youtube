# YouTube Summarizer

This project provides a command-line interface (CLI) tool to summarize YouTube videos using the Gemini AI model. It attempts to fetch transcripts first and falls back to audio analysis if transcripts are unavailable.

## Features

- **Transcript-based Summarization**: Leverages YouTube's official transcripts for accurate summaries.
- **Audio-based Summarization**: Falls back to downloading and analyzing video audio if transcripts are not available.
- **Structured Output**: Provides a title, executive summary, and key topics with timestamps.
- **Configurable**: Uses environment variables for API keys and `argparse` for CLI arguments.
- **Containerized**: Includes a Dockerfile for easy deployment.

## Setup

### Prerequisites

- Python 3.9+
- An API key for Google Gemini (set as `GOOGLE_API_KEY` in a `.env` file).

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/youtube-summarizer.git
    cd youtube-summarizer
    ```

2.  **Create a virtual environment and install dependencies**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure API Key**:
    Create a `.env` file in the root directory of the project with your Google Gemini API key:
    ```
    GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
    ```

## Usage

Run the `main.py` script with the YouTube video URL as an argument:

```bash
python main.py "YOUR_YOUTUBE_VIDEO_URL"
```

The summary will be printed to the console and saved as `output.json` in the project root.

## Docker Usage

To build and run the application using Docker:

1.  **Build the Docker image**:
    ```bash
    docker build -t youtube-summarizer .
    ```

2.  **Run the Docker container**:
    ```bash
    docker run --rm -e GOOGLE_API_KEY="YOUR_GEMINI_API_KEY" youtube-summarizer "YOUR_YOUTUBE_VIDEO_URL"
    ```
    Replace `"YOUR_GEMINI_API_KEY"` with your actual key and `"YOUR_YOUTUBE_VIDEO_URL"` with the video you want to summarize.
