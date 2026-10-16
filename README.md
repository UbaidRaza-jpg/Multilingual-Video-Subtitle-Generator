# Multilingual Video Subtitle Generator

![Author](https://img.shields.io/badge/Developed%20By-Muhammad%20Ubaid%20Raza-purple?style=for-the-badge&logo=github)
![Live Demo](https://img.shields.io/badge/Streamlit%20Cloud-Live%20Demo-red?style=for-the-badge&logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

A premium, AI-powered web application that automatically transcribes audio, translates subtitles into foreign languages, and hardcodes customizable subtitles into user-uploaded videos. Developed by **Muhammad Ubaid Raza** ([@UbaidRaza-jpg](https://github.com/UbaidRaza-jpg)).

The application features an interactive segment timeline editor, advanced styling options (font, size, color, drop-shadow, Netflix-style bounding boxes, alignment), and a hybrid architecture supporting both a high-throughput FastAPI/Streamlit API mode and a lightweight, serverless Streamlit Standalone deployment mode.

---

## Key Features

* **Interactive Subtitle Timeline Editor**: Review, edit, and adjust transcription and translation segment text directly inside a multi-step modal editor before burning subtitles into the output video.
* **AI Speech Recognition & Translation**: 
  * Powered by `faster-whisper` for fast transformer-based speech recognition with precise word-level timestamps.
  * Multi-tier translation pipeline integrating DeepL API, Google Cloud Official Translation API, `deep-translator`, and `googletrans`.
* **Premium Typography & Bounding Box Styling**: 
  * Choose from 12 popular web fonts (*Arial, Arial Black, Calibri, Comic Sans MS, Consolas, Courier New, Georgia, Impact, Tahoma, Times New Roman, Trebuchet MS, Verdana*).
  * **Dynamic Dropdown Previews**: Dropdown select options are rendered in their exact native font styles.
  * **Netflix-Style Bounding Box**: Toggle between text outlines or a semi-transparent black padded container for high contrast and readability.
* **Timing Modes (Word-by-Word vs. Line-by-Line)**:
  * **Word-by-Word**: Subtitle words pop up dynamically as they are spoken, driven by Whisper word-level timestamps.
  * **Line-by-Line**: Subtitles remain formatted as full single-sentence captions.
* **Bilingual (Dual-Language) Subtitles**: Display dual-stacked subtitles (original spoken language + translated target language) simultaneously.
* **Independent SRT File Export**: Export and download clean `.srt` subtitle files independently from burned video files.
* **Modern UI & Processing Screens**: Streamlit interface customized with CSS glassmorphism, responsive alignment selectors (Top, Middle, Bottom), and non-blocking orbit loader animations.
* **Email Notification Dispatch**: Optional SMTP notification system alerting users when video compilation finishes.

---

## Technology Stack

* **Developer**: **Muhammad Ubaid Raza** ([UbaidRaza-jpg](https://github.com/UbaidRaza-jpg))
* **Speech Recognition**: `faster-whisper` (Fast CTranslate2 Whisper implementation)
* **Translation Pipeline**: `deep-translator`, `googletrans`, DeepL API, Google Translation API
* **Video & Subtitle Processing**: `FFmpeg` (wrapped via `moviepy` and `imageio-ffmpeg`)
* **Web Application UI**: `streamlit` (enhanced with custom HTML/CSS portal overrides)
* **API Engine**: `fastapi` & `uvicorn`

---

## Getting Started

### Prerequisites

* Python 3.8 or higher.
* `ffmpeg` (automatically bundled via `imageio-ffmpeg` or system PATH).

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

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration** *(Optional)*:
   Create a `.env` file in the project root to set API keys and SMTP credentials (refer to `.env.example`):
   ```env
   ADMIN_API_KEY=your_secure_admin_token
   ALLOWED_ORIGINS=http://localhost:8000,http://localhost:8501
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-google-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   ```

---

## Project Structure

* [app.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/app.py): Streamlit web application interface with multi-step styling wizard, timeline editor, and export workflow.
* [core_engine.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/core_engine.py): Core processing pipeline for transcription, translation, SRT parsing, and FFmpeg subtitle burning.
* [main.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/main.py): Production-hardened FastAPI REST backend with rate limiting, input sanitization, security headers, and authenticated admin routes.
* [security.py](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/security.py): Security utilities for password hashing (PBKDF2-HMAC-SHA256), token verification, input validation, and sliding-window rate limiting.
* [frontend/](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/frontend): Modern single-page web client interface built with HTML5, CSS3, and JavaScript with XSS defense.
* [requirements.txt](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/requirements.txt): Python package requirements.
* [packages.txt](file:///c:/Users/ubaid/Desktop/Multilingual-Video-Subtitle-Generator/packages.txt): Cloud container package manifest.

---

## How to Run

### Option A: Standalone Streamlit Mode (Recommended for Cloud)
```bash
streamlit run app.py
```

### Option B: Full API Mode (FastAPI + Streamlit)
1. **Start backend API**:
   ```bash
   uvicorn main:app
   ```
2. **Start Streamlit frontend**:
   ```bash
   streamlit run app.py
   ```

---

## Developer & Author

**Muhammad Ubaid Raza**
* **Role**: Software Developer & AI/Web Engineering Student
* **Education**: BS Information Technology, Bahria University Karachi
* **GitHub Profile**: [@UbaidRaza-jpg](https://github.com/UbaidRaza-jpg)
* **LinkedIn**: [Muhammad Ubaid Raza](https://www.linkedin.com/in/)
* **Flagship Project**: Multilingual Video Subtitle Generator
* **Live Application**: [Streamlit Cloud Deployment](https://built-by-ubaid-multilingual-video-subtitle-generator.streamlit.app/)
* **Developed By**: [Muhammad Ubaid Raza](https://ubaidraza-jpg.github.io/portfolio/)
---

## License

This project is open-source under the [MIT License](LICENSE).
