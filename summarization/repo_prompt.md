Requirements:
1. **Architecture**: Convert the procedural code into OOP. Create specific classes (e.g., 'VideoScraper', 'TranscriptParser') with single responsibilities.
2. **Best Practices**: Add Python type hinting, proper logging (no print statements), and error handling (try/except blocks).
3. **Configuration**: Use argparse for CLI arguments (URL input) and read configuration from a .env or config file if needed.
4. **Structure**: Output the response as multiple files representing a standard repo layout:
   - README.md
   - requirements.txt
   - src/__init__.py
   - src/scraper.py
   - src/utils.py
   - main.py
   - Dockerfile
5. **Code**: Provide the full code for each file. Repository path: `/home/valka/repo/youtube/summarization/agent_repo`