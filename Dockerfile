# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies: ffmpeg, fontconfig, and standard fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements file first to utilize Docker build cache
COPY requirements.txt /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and frontend files
COPY main.py core_engine.py /app/
COPY frontend /app/frontend

# Create directory structures and grant full read/write permissions
# Hugging Face Spaces run with a non-root user (UID 1000)
RUN mkdir -p /app/uploads /app/temp_outputs \
    && chmod -R 777 /app/uploads /app/temp_outputs

# Expose Hugging Face Space default port
EXPOSE 7860

# Launch FastAPI application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
