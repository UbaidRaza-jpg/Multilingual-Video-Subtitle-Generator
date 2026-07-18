# Multilingual Video Subtitle Generator

A premium, feature-rich web application that transcribes, translates, and hardcodes subtitles into user-uploaded videos. The application offers a state-of-the-art interactive timeline editor, advanced styling customizer, and a hybrid architecture supporting both a performant FastAPI/Streamlit API mode and a lightweight, database-free Streamlit Standalone deployment mode.

---

## Key Features

* **Interactive Subtitle Timeline Editor**: Review and edit transcription/translation segment text directly inside a multi-step modal dialog before burning the subtitles into the final video.
* **Premium Typography & Bounding Box Styling**: 
  * Choose from 12 popular fonts (Arial, Arial Black, Calibri, Comic Sans MS, Consolas, Courier New, Georgia, Impact, Tahoma, Times New Roman, Trebuchet MS, Verdana).
  * **Dynamic Dropdown Previews**: Dropdown menu items and closed values are styled in their exact corresponding font families dynamically.
  * **Netflix-Style Bounding Box**: Toggle between a standard text outline or a semi-transparent black padded bounding box container behind subtitles for maximum readability.
* **Word-by-Word & Line-by-Line subtitle timings**:
  * **Word-by-Word**: Subtitle words pop up and transition as they are spoken, powered by Whisper word-level timestamps.
  * **Line-by-Line**: Subtitles remain as complete single-sentence lines.
* **Bilingual (Dual-Language) Subtitles**: Toggle dual-stacked subtitles to display the original spoken language and the translated language at the same time.
* **Separate SRT Downloader**: Export and download the translated `.srt` subtitle file independently from the hardcoded video file.
* **Modern glassmorphic UI**: Streamlit interface enhanced with custom CSS stylesheets, responsive alignment selectors (Top/Middle/Bottom rows), and CSS-animated orbit sphere loading screens that prevent browser freeze-ups.
* **Email Notification System**: Optional email notifications that advise users when their video is ready, prompting them back to their browser tab for secure, high-speed delivery.

---

## Technology Stack

* **Transcription Engine**: `faster-whisper` (Fast Transformer-based Whisper transcription)
* **Translation Engine**: `googletrans` (v4.0.0-rc1)
* **Video & Audio Processing**: `ffmpeg` (wrapped with custom filter pipelines for scale and subtitle burns)
* **Web App UI**: `streamlit` (enhanced with custom HTML/CSS portal overrides)
* **API Framework**: `fastapi` & `uvicorn`

---

## Getting Started

### Prerequisites

* Python 3.8 or higher.
* `ffmpeg` installed on your system and added to your system PATH.

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/UbaidRaza-jpg/Multilingual-Video-Subtitle-Generator.git
   cd Multilingual-Video-Subtitle-Generator
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the project root to configure SMTP email notification credentials (optional):
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-google-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   ```

---

## Project Structure

* [app.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/app.py): The main Streamlit web application. Contains the multi-step styling wizard, interactive timeline text editor, and download layout.
* [core_engine.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/core_engine.py): The core subtitle generation engine handling transcription, translation, and FFmpeg burning operations.
* [main.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/main.py): The FastAPI backend exposing REST endpoints for API Mode integration.
* [requirements.txt](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/requirements.txt): Python package requirements.
* [packages.txt](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/packages.txt): APT packages required for Cloud hosting (e.g. `ffmpeg`).

---

## How to Run

### Option A: Standalone Mode (Recommended for Streamlit Cloud)
Running the Streamlit app alone will trigger local standalone processing. This mode is lightweight, database-free, and handles uploads locally:
```bash
streamlit run app.py
```

### Option B: API Mode (FastAPI + Streamlit)
If you want to run the separate backend processor:
1. **Start the FastAPI backend server**:
   ```bash
   uvicorn main:app --reload
   ```
2. **Start the Streamlit web interface** in a separate terminal:
   ```bash
   streamlit run app.py
   ```
   *The Streamlit frontend will automatically detect the backend on `http://localhost:8000` and route requests through it.*

---

## License

This project is licensed under the MIT License.
