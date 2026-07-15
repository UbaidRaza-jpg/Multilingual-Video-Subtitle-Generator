# Multilingual Video Subtitle Generator

A free-tier web application that transcribes, translates, and hardcodes subtitles into user-uploaded videos.

## Features

- **Automated Transcription**: Powered by `faster-whisper` for fast and high-accuracy speech-to-text.
- **Multilingual Translation**: Seamlessly translate generated subtitles into various target languages using `googletrans`.
- **Subtitle Hardcoding**: Burn translated subtitles directly into the video output using `moviepy` and `ffmpeg`.
- **Double Interface**: 
  - A modern frontend built with **Streamlit** for interactive user uploads and options.
  - A performant backend API powered by **FastAPI** to handle video processing workflows.

## Technology Stack

- **Core Logic**: Python 3.8+
- **Transcription Engine**: `faster-whisper` (Fast Transformer-based Whisper transcription)
- **Translation Engine**: `googletrans` (v4.0.0-rc1)
- **Video & Audio Processing**: `moviepy`, `ffmpeg-python`, and system-level `ffmpeg`
- **Web App UI**: `streamlit`
- **API Framework**: `fastapi` & `uvicorn`

## Getting Started

### Prerequisites

- Python 3.8 or higher.
- `ffmpeg` installed on your system and added to your system PATH.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/Multilingual-Video-Subtitle-Generator.git
   cd Multilingual-Video-Subtitle-Generator
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows (Command Prompt):
   venv\Scripts\activate
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Project Structure

- `core_engine.py`: Contains the core subtitle generation pipeline (transcription, translation, and burning subtitles via FFmpeg).
- `main.py`: FastAPI asynchronous backend server exposing endpoints for upload, status polling, and downloads.
- `app.py`: Interactive Streamlit frontend UI for easy video uploads and subtitle configuration.
- `test_run.py`: Script to quickly test the subtitle engine locally via command-line.
- `requirements.txt`: Project library dependencies.
- `.env`: Environment variables configuration file.

## How to Run

### Step 1: Run the Backend API
Start the FastAPI server on port 8000:
```bash
uvicorn main:app --reload
```

### Step 2: Run the Streamlit Frontend
Start the Streamlit web interface (in a separate terminal window):
```bash
streamlit run app.py
```

Open your browser and navigate to `http://localhost:8501` to start generating subtitles!

## License

This project is licensed under the MIT License.

