# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose any necessary ports (if applicable for web apps, not strictly needed for CLI)
# EXPOSE 8000

# Run main.py when the container launches
# CMD ["python", "main.py"]
# Use an entrypoint script to handle arguments more flexibly if needed,
# or specify the command in `docker run`
ENTRYPOINT ["python", "main.py"]
