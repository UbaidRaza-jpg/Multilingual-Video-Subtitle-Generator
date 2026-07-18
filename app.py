import os
import time
import uuid
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Multilingual Video Subtitle Generator",
    page_icon="video",
    layout="centered"
)

# Inject custom CSS for premium design
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');

    /* Global Body and Font Settings */
    .stApp {
        background-color: #0E111A;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Gradient Hero Title */
    .hero-title {
        background: -webkit-linear-gradient(135deg, #A855F7 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.6rem;
        text-align: center;
        margin-bottom: 0.5rem;
        font-family: 'Plus Jakarta Sans', sans-serif;
        letter-spacing: -0.5px;
        margin-top: 1rem;
    }

    .hero-subtitle {
        color: #9CA3AF;
        font-size: 1.05rem;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
        line-height: 1.5;
    }

    /* Dialog Style Overrides (Glassmorphism + Dark Mode) */
    div[role="dialog"] {
        background-color: #161922 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5) !important;
        padding: 30px !important;
    }

    div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: white !important;
    }

    /* Sleek Card Headers */
    .custom-card-header {
        font-weight: 700;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #FFFFFF;
        font-size: 1.35rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        letter-spacing: -0.2px;
    }

    /* File Uploader Container */
    div[data-testid="stFileUploader"] {
        background: rgba(26, 29, 36, 0.6) !important;
        border: 2px dashed rgba(168, 85, 247, 0.35) !important;
        border-radius: 16px !important;
        padding: 40px 24px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
        text-align: center;
    }

    div[data-testid="stFileUploader"]:hover {
        border-color: #3B82F6 !important;
        background: rgba(26, 29, 36, 0.8) !important;
        box-shadow: 0 8px 30px rgba(59, 130, 246, 0.12) !important;
    }

    /* Buttons restyling */
    div.stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #3B82F6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3) !important;
        width: 100% !important;
        margin-top: 15px;
    }

    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(139, 92, 246, 0.45) !important;
        background: linear-gradient(135deg, #A78BFA 0%, #60A5FA 100%) !important;
    }

    div.stButton > button:active {
        transform: translateY(1px) !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3) !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #34D399 0%, #10B981 100%) !important;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    /* Custom selectboxes/inputs */
    div[data-baseweb="select"] > div {
        background-color: #1A1D24 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: white !important;
        padding: 2px 4px !important;
    }

    div[data-baseweb="input"] {
        background-color: #1A1D24 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 2px 4px !important;
    }
    
    div[data-baseweb="input"] input {
        color: white !important;
    }
    
    /* Sleek status banners */
    div.stAlert {
        background-color: rgba(26, 29, 36, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        color: white !important;
        backdrop-filter: blur(8px);
    }
    
    /* Sleek divider */
    hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
        margin: 2.5rem 0 !important;
    }
    
    /* Captions */
    .stCaption {
        color: #6B7280 !important;
        font-weight: 300;
        text-align: center;
        margin-top: 2rem;
    }

    /* Orbit Loader Spinner */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 45px 25px;
        background: rgba(26, 29, 36, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        margin: 30px auto !important;
        max-width: 450px !important;
        backdrop-filter: blur(12px) !important;
    }
    
    .orbit-spinner {
        position: relative;
        width: 80px;
        height: 80px;
        margin-bottom: 25px;
    }
    
    .orbit-ball {
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: linear-gradient(135deg, #A855F7 0%, #3B82F6 100%) !important;
        box-shadow: 0 0 15px rgba(168, 85, 247, 0.7) !important;
        animation: orbit-animation 1.6s infinite linear !important;
    }
    
    .ball-1 { animation-delay: 0s; transform: rotate(0deg) translate(30px) rotate(0deg); }
    .ball-2 { animation-delay: 0.53s; transform: rotate(120deg) translate(30px) rotate(-120deg); }
    .ball-3 { animation-delay: 1.06s; transform: rotate(240deg) translate(30px) rotate(-240deg); }

    @keyframes orbit-animation {
        0% {
            transform: rotate(0deg) translate(30px) rotate(0deg);
        }
        100% {
            transform: rotate(360deg) translate(30px) rotate(-360deg);
        }
    }
    
    .loader-title {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #FFFFFF !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        margin-bottom: 6px !important;
        letter-spacing: -0.2px !important;
    }
    
    .loader-subtitle {
        font-family: 'Outfit', sans-serif !important;
        color: #9CA3AF !important;
        font-size: 0.9rem !important;
        font-weight: 300 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# API Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Check if backend FastAPI server is running
if "use_api" not in st.session_state:
    try:
        # Send a quick request to check connectivity
        requests.get(API_URL, timeout=1.0)
        st.session_state.use_api = True
    except Exception:
        st.session_state.use_api = False

# Try importing core engine locally for Standalone Mode fallback
try:
    from core_engine import process_video, generate_subtitle_preview
    LOCAL_ENGINE_AVAILABLE = True
except ImportError:
    LOCAL_ENGINE_AVAILABLE = False


def hex_to_ass_color(hex_str: str) -> str:
    """
    Converts standard HTML color hex (#RRGGBB) to Subtitle ASS primary color format (&H00BBGGRR).
    """
    hex_str = hex_str.lstrip('#').replace('&H00', '').replace('&H', '')
    if len(hex_str) == 6:
        r = hex_str[0:2]
        g = hex_str[2:4]
        b = hex_str[4:6]
        return f"&H00{b}{g}{r}".upper()
    return "&H00FFFFFF"


def render_orbit_loader(title: str, subtitle: str):
    """
    Renders a custom CSS animated orbit spinner with title and subtitle labels.
    """
    st.markdown(
        f"""
        <div class="loader-container">
            <div class="orbit-spinner">
                <div class="orbit-ball ball-1"></div>
                <div class="orbit-ball ball-2"></div>
                <div class="orbit-ball ball-3"></div>
            </div>
            <div class="loader-title">{title}</div>
            <div class="loader-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# Standalone SMTP notifier helper
def send_standalone_email(to_email: str, status: str, original_filename: str, error_reason: str = None):
    # Try to load secrets from Streamlit Cloud Secrets, fallback to os.environ
    host = st.secrets.get("SMTP_HOST") or os.environ.get("SMTP_HOST")
    port = st.secrets.get("SMTP_PORT") or os.environ.get("SMTP_PORT")
    username = st.secrets.get("SMTP_USERNAME") or os.environ.get("SMTP_USERNAME")
    password = st.secrets.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASSWORD")
    from_email = st.secrets.get("SMTP_FROM_EMAIL") or os.environ.get("SMTP_FROM_EMAIL", username)
    
    if not all([host, port, username, password]):
        print("Standalone Email Notification skipped: SMTP credentials are not configured.")
        return
        
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Subtitle Task: {original_filename} - {status.upper()}"
        msg["From"] = from_email
        msg["To"] = to_email
        
        if status == "completed":
            html = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #374151; background-color: #F3F4F6; margin: 0;">
                <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #E5E7EB;">
                    <h2 style="color: #1F2937; border-bottom: 2px solid #F3F4F6; padding-bottom: 15px; margin-top: 0; font-size: 1.4rem; font-weight: 700;">
                        Subtitle Generation Complete!
                    </h2>
                    <p style="font-size: 15px; line-height: 1.6; margin-top: 20px; color: #4B5563;">
                        Your video <strong>{original_filename}</strong> has been successfully subtitled.
                    </p>
                    <div style="background-color: #EFF6FF; border-left: 4px solid #3B82F6; padding: 18px 20px; border-radius: 0 12px 12px 0; margin: 25px 0;">
                        <p style="font-size: 14.5px; line-height: 1.6; color: #1E3A8A; margin: 0;">
                            For maximum security and high-speed delivery, your subtitled video is compiled and served directly within your active browser tab.
                        </p>
                        <p style="font-size: 14.5px; line-height: 1.6; color: #1E3A8A; margin-top: 10px; margin-bottom: 0; font-weight: 600;">
                            Please return to the website tab in your browser to download your video immediately at full speed.
                        </p>
                    </div>
                    <p style="font-size: 15px; line-height: 1.6; color: #4B5563;">
                        Thank you for using our service!
                    </p>
                    <hr style="border: 0; border-top: 1px solid #F3F4F6; margin-top: 35px;" />
                    <p style="font-size: 12px; color: #9CA3AF; text-align: center; margin-bottom: 0;">
                        This is an automated notification from the Multilingual Video Subtitle Generator.
                    </p>
                </div>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 30px; color: #333; background-color: #f9f9f9;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee;">
                    <h2 style="color: #EF4444; border-bottom: 2px solid #E5E7EB; padding-bottom: 12px; margin-top: 0;">Subtitle Generation Failed</h2>
                    <p style="font-size: 15px; line-height: 1.6;">Unfortunately, processing your video <strong>{original_filename}</strong> ran into an error.</p>
                    <p style="font-size: 15px; line-height: 1.6;"><strong>Error Reason:</strong></p>
                    <blockquote style="background: #f9f9f9; border-left: 4px solid #EF4444; margin: 1.5em 0; padding: 12px 16px; border-radius: 0 8px 8px 0;">
                        <code style="font-family: monospace; color: #374151;">{error_reason}</code>
                    </blockquote>
                    <hr style="border: 0; border-top: 1px solid #E5E7EB; margin-top: 30px;" />
                    <p style="font-size: 12px; color: #9CA3AF; text-align: center;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
                </div>
            </body>
            </html>
            """
        msg.attach(MIMEText(html, "html"))
        
        server = smtplib.SMTP(host, int(port))
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        print(f"Standalone email notification sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email notification in standalone: {e}")


# Language mapping
LANGUAGES = {
    # English & Regional Dialects
    "English (Global)": "en",
    "English (Australian)": "en",
    "English (British)": "en",
    "English (American)": "en",
    
    # Western & Central European
    "Spanish (Español)": "es",
    "French (Français)": "fr",
    "German (Deutsch)": "de",
    "Italian (Italiano)": "it",
    "Portuguese (Português)": "pt",
    "Dutch (Nederlands)": "nl",
    "Afrikaans": "af",
    "Basque (Euskara)": "eu",
    "Catalan (Català)": "ca",
    "Galician (Galego)": "gl",
    "Icelandic (Íslenska)": "is",
    "Latin (Latina)": "la",
    "Luxembourgish (Lëtzebuergesch)": "lb",
    "Welsh (Cymraeg)": "cy",
    
    # Eastern European & Slavic
    "Albanian (Shqip)": "sq",
    "Belarusian (Беларуская)": "be",
    "Bosnian (Bosanski)": "bs",
    "Bulgarian (Български)": "bg",
    "Croatian (Hrvatski)": "hr",
    "Czech (Čeština)": "cs",
    "Estonian (Eesti)": "et",
    "Hungarian (Magyar)": "hu",
    "Latvian (Latviešu)": "lv",
    "Lithuanian (Lietuvių)": "lt",
    "Macedonian (Македонски)": "mk",
    "Polish (Polski)": "pl",
    "Romanian (Română)": "ro",
    "Russian (Русский)": "ru",
    "Serbian (Српски)": "sr",
    "Slovak (Slovenčina)": "sk",
    "Slovenian (Slovenščina)": "sl",
    "Ukrainian (Українська)": "uk",
    
    # Middle Eastern & Central Asian
    "Arabic (العربية)": "ar",
    "Armenian (Հայերեն)": "hy",
    "Azerbaijani (Azərbaycan)": "az",
    "Hebrew (עברית)": "he",
    "Kazakh (Қазақ)": "kk",
    "Pashto (پښتو)": "ps",
    "Persian (فارسی)": "fa",
    "Tajik (Тоҷикӣ)": "tg",
    "Turkish (Türkçe)": "tr",
    "Uzbek (Oʻzbek)": "uz",
    "Yiddish (ייִדיש)": "yi",
    
    # South Asian
    "Bengali (বাংলা)": "bn",
    "Gujarati (ગુજરાતી)": "gu",
    "Hindi (हिन्दी)": "hi",
    "Kannada (ಕನ್ನಡ)": "kn",
    "Malayalam (മലയാളം)": "ml",
    "Marathi (मраठी)": "mr",
    "Nepali (नेपाली)": "ne",
    "Punjabi (ਪੰਜਾਬੀ)": "pa",
    "Sindhi (سنڌي)": "sd",
    "Sinhala (සිංহල)": "si",
    "Tamil (தமிழ்)": "ta",
    "Telugu (తెలుగు)": "te",
    "Urdu (اردو)": "ur",
    
    # East & Southeast Asian
    "Burmese (မြန်မာ)": "my",
    "Chinese Simplified (简体中文)": "zh-cn",
    "Indonesian (Bahasa Indonesia)": "id",
    "Japanese (日本語)": "ja",
    "Javanese (Jawa)": "jw",
    "Khmer (ខ្មែរ)": "km",
    "Korean (한국어)": "ko",
    "Lao (лау)": "lo",
    "Malay (Bahasa Melayu)": "ms",
    "Mongolian (Монгол)": "mn",
    "Sundanese (Sunda)": "su",
    "Tagalog (Filipino)": "tl",
    "Thai (ไทย)": "th",
    "Vietnamese (Tiếng Việt)": "vi",
    
    # African
    "Amharic (አማርኛ)": "am",
    "Hausa": "ha",
    "Malagasy": "mg",
    "Shona (Chishona)": "sn",
    "Somali (Soomaali)": "so",
    "Swahili (Kiswahili)": "sw",
    "Yoruba (Yorùbá)": "yo",
    
    # Nordic
    "Danish (Dansk)": "da",
    "Finnish (Suomi)": "fi",
    "Norwegian (Norsk)": "no",
    "Swedish (Svenska)": "sv",
    
    # Other / Regional
    "Georgian (ქართული)": "ka",
    "Haitian Creole (Kreyòl)": "ht",
    "Hawaiian (ʻŌlelo Hawaiʻi)": "haw",
    "Maltese (Malti)": "mt",
    "Maori (Māori)": "mi"
}

# Sort alphabetically for user-friendly selectbox search
LANGUAGES = dict(sorted(LANGUAGES.items()))

# Hero Title and Subtitle Header
st.markdown('<div class="hero-title">Multilingual Video Subtitle Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Upload a video with speech, select your target translation language, and burn customized subtitles directly into your video file instantly.</div>', 
    unsafe_allow_html=True
)

# Show running mode banner only if connected to backend API
if st.session_state.use_api:
    st.success("Connected to backend API server.")

st.divider()

# Initialize state machine variables
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "uploaded_filepath" not in st.session_state:
    st.session_state.uploaded_filepath = None
if "final_video_bytes" not in st.session_state:
    st.session_state.final_video_bytes = None
if "processing_error" not in st.session_state:
    st.session_state.processing_error = None
if "params" not in st.session_state:
    st.session_state.params = {}
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False


# Reset handler helper
def start_over():
    st.session_state.step = "upload"
    st.session_state.video_id = None
    st.session_state.uploaded_filename = None
    st.session_state.uploaded_filepath = None
    st.session_state.final_video_bytes = None
    st.session_state.processing_error = None
    st.session_state.params = {}
    st.session_state.is_processing = False
    st.rerun()


# Modal Configuration Dialog
@st.dialog("Configure Subtitles", width="large")
def show_configure_dialog():
    if st.session_state.is_processing:
        # Hover loader directly inside the dialog while keeping the dims active
        render_orbit_loader("Processing Subtitles", "AI is transcribing and translating your video inside the background queue...")
        
        # Execute processing logic inside the configure dialog popup!
        status_holder = st.empty()
        
        if st.session_state.use_api:
            # API Mode processing
            try:
                payload = {
                    "target_language": st.session_state.params["target_lang_code"],
                    "alignment": st.session_state.params["align_code"],
                    "font_size": st.session_state.params["size_code"],
                    "font_color": st.session_state.params["color_code"],
                    "model_size": st.session_state.params["model_size_code"],
                    "resolution_cap": st.session_state.params["resolution_cap_code"],
                    "segmentation_mode": st.session_state.params["segmentation_mode_code"],
                    "email": st.session_state.params.get("email")
                }
                
                response = requests.post(f"{API_URL}/process/{st.session_state.video_id}", data=payload)
                
                if response.status_code != 200:
                    st.error(f"Failed to trigger process: {response.text}")
                    if st.button("Retry"):
                        st.session_state.is_processing = False
                        st.rerun()
                else:
                    task_data = response.json()
                    task_id = task_data["task_id"]
                    
                    status = "queued"
                    start_time = time.time()
                    
                    while status in ["queued", "processing", "uploaded"]:
                        try:
                            status_resp = requests.get(f"{API_URL}/status/{task_id}")
                            if status_resp.status_code == 200:
                                status_data = status_resp.json()
                                status = status_data["status"]
                                elapsed = time.time() - start_time
                                
                                if status in ["queued", "uploaded"]:
                                    with status_holder:
                                        render_orbit_loader("Queued in Queue", f"Waiting for background worker... (elapsed: {elapsed:.1f}s)")
                                elif status == "processing":
                                    with status_holder:
                                        render_orbit_loader("AI Processing", f"Transcribing audio & translating speech... (elapsed: {elapsed:.1f}s)")
                            else:
                                with status_holder:
                                    render_orbit_loader("Status Check", "Retrying server connection...")
                        except Exception:
                            with status_holder:
                                render_orbit_loader("Interrupted", "Re-connecting to backend server...")
                        time.sleep(2.5)
                    
                    if status == "completed":
                        with status_holder:
                            render_orbit_loader("Retrieving Video", "Completed successfully! Downloading output file...")
                        
                        download_url = f"{API_URL}/download/{task_id}"
                        video_resp = requests.get(download_url)
                        if video_resp.status_code == 200:
                            st.session_state.final_video_bytes = video_resp.content
                            st.session_state.is_processing = False
                            st.session_state.step = "download"
                            st.rerun()
                        else:
                            st.error("Failed to retrieve final subtitle output.")
                            if st.button("Close"):
                                st.session_state.is_processing = False
                                st.rerun()
                    elif status == "failed":
                        try:
                            status_resp = requests.get(f"{API_URL}/status/{task_id}")
                            error_reason = status_resp.json().get("error", "Unknown error")
                        except Exception:
                            error_reason = "Unknown error"
                        st.error(f"Subtitle generation failed: {error_reason}")
                        if st.button("Close"):
                            st.session_state.is_processing = False
                            st.rerun()
            except Exception as e:
                st.error(f"Error occurred: {e}")
                if st.button("Close"):
                    st.session_state.is_processing = False
                    st.rerun()
        else:
            # Standalone Local Processing inside Popup
            if LOCAL_ENGINE_AVAILABLE:
                try:
                    output_filepath = process_video(
                        st.session_state.uploaded_filepath,
                        st.session_state.params["target_lang_code"],
                        st.session_state.params["align_code"],
                        st.session_state.params["size_code"],
                        st.session_state.params["color_code"],
                        model_size=st.session_state.params["model_size_code"],
                        resolution_cap=st.session_state.params["resolution_cap_code"],
                        segmentation_mode=st.session_state.params["segmentation_mode_code"]
                    )
                    
                    if output_filepath and os.path.exists(output_filepath):
                        with open(output_filepath, "rb") as f:
                            st.session_state.final_video_bytes = f.read()
                            
                        # Send email if SMTP is configured
                        if st.session_state.params.get("email"):
                            send_standalone_email(
                                st.session_state.params["email"],
                                "completed",
                                st.session_state.uploaded_filename
                            )
                            
                        try:
                            os.remove(output_filepath)
                        except Exception:
                            pass
                            
                        st.session_state.is_processing = False
                        st.session_state.step = "download"
                        st.rerun()
                    else:
                        raise Exception("Local process engine failed to export file.")
                except Exception as err:
                    st.error(f"Subtitle processing failed: {err}")
                    if st.button("Close"):
                        st.session_state.is_processing = False
                        st.rerun()
                finally:
                    try:
                        if os.path.exists(st.session_state.uploaded_filepath):
                            os.remove(st.session_state.uploaded_filepath)
                    except Exception:
                        pass
            else:
                st.error("Local engine is not available for standalone processing.")
                if st.button("Close"):
                    st.session_state.is_processing = False
                    st.rerun()
    else:
        # Standard configuration dialog view
        st.markdown('<div class="custom-card-header">Select Styling, Language & Accuracy</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ALIGNMENTS = {
                "Bottom (Center)": 2,
                "Top (Center)": 8,
                "Middle (Center)": 5,
                "Bottom Left": 1,
                "Bottom Right": 3,
                "Top Left": 7,
                "Top Right": 9
            }
            align_name = st.selectbox("Position:", options=list(ALIGNMENTS.keys()), index=0)
            align_code = ALIGNMENTS[align_name]
            
        with col2:
            SIZES = {
                "Small (16px)": 16,
                "Medium (20px)": 20,
                "Large (24px)": 24,
                "Extra Large (32px)": 32
            }
            size_name = st.selectbox("Font Size:", options=list(SIZES.keys()), index=1)
            size_code = SIZES[size_name]
            
        with col3:
            COLORS = {
                "White": "&H00FFFFFF",
                "Yellow": "&H0000FFFF",
                "Cyan": "&H00FFFF00",
                "Red": "&H000000FF",
                "Green": "&H0000FF00",
                "Blue": "&H00FF0000",
                "Custom Color Picker...": "custom"
            }
            color_name = st.selectbox("Font Color:", options=list(COLORS.keys()), index=0)
            if COLORS[color_name] == "custom":
                chosen_hex = st.color_picker("Choose Color:", "#FFFFFF")
                color_code = hex_to_ass_color(chosen_hex)
            else:
                color_code = COLORS[color_name]
            
        col_lang, col_acc, col_res, col_seg = st.columns(4)
        with col_lang:
            target_lang_name = st.selectbox(
                "Target Language:",
                options=list(LANGUAGES.keys()),
                index=list(LANGUAGES.keys()).index("English (Global)")
            )
            target_lang_code = LANGUAGES[target_lang_name]
            
        with col_acc:
            ACCURACY_MODELS = {
                "High Accuracy (Recommended)": "small",
                "Fast / Standard Accuracy": "base"
            }
            accuracy_name = st.selectbox("Accuracy:", options=list(ACCURACY_MODELS.keys()), index=0)
            model_size_code = ACCURACY_MODELS[accuracy_name]
            
        with col_res:
            RESOLUTIONS = {
                "Original Resolution (Fastest)": "original",
                "Standard HD (720p)": "720p",
                "Mobile Optimized (480p)": "480p"
            }
            res_name = st.selectbox("Export Resolution:", options=list(RESOLUTIONS.keys()), index=0)
            resolution_cap_code = RESOLUTIONS[res_name]
            
        with col_seg:
            SEGMENTATIONS = {
                "Line by Line": "line_by_line",
                "Word by Word": "word_by_word"
            }
            seg_name = st.selectbox("Subtitle Style:", options=list(SEGMENTATIONS.keys()), index=0)
            segmentation_mode = SEGMENTATIONS[seg_name]
            
        st.divider()
        
        # Email notifier text input (Optional) - placed under options as requested
        email_input = st.text_input(
            "Email Address for Notifications (Optional):",
            placeholder="Enter your email to receive a notification of download when complete.",
            help="Ensure you configure the SMTP details in your .env file or Streamlit Cloud secrets to enable emails."
        )
        
        st.divider()
        
        # Real-time preview frame
        st.markdown('<div class="custom-card-header">Instant Layout Preview</div>', unsafe_allow_html=True)
        with st.spinner("Generating subtitle layout preview..."):
            try:
                if st.session_state.use_api:
                    params = {
                        "alignment": align_code,
                        "font_size": size_code,
                        "font_color": color_code
                    }
                    preview_resp = requests.get(f"{API_URL}/preview/{st.session_state.video_id}", params=params)
                    if preview_resp.status_code == 200:
                        st.image(preview_resp.content, caption="Subtitle Location Preview (approx. 1s mark)", use_column_width=True)
                    else:
                        st.warning(f"Could not load preview frame (HTTP {preview_resp.status_code})")
                else:
                    if LOCAL_ENGINE_AVAILABLE:
                        preview_filename = f"preview_{st.session_state.video_id}_{align_code}_{size_code}_{color_code.replace('&', '').replace('#', '')}.jpg"
                        preview_filepath = os.path.join("temp_outputs", preview_filename)
                        success = generate_subtitle_preview(
                            st.session_state.uploaded_filepath,
                            align_code,
                            size_code,
                            color_code,
                            preview_filepath
                        )
                        if success and os.path.exists(preview_filepath):
                            with open(preview_filepath, "rb") as f:
                                st.image(f.read(), caption="Subtitle Location Preview (approx. 1s mark)", use_column_width=True)
                        else:
                            st.warning("Failed to generate subtitle preview locally.")
                    else:
                        st.warning("Local engine is not available for standalone previews.")
            except Exception as e:
                st.warning(f"Error loading preview frame: {e}")
                
        # Trigger Action Button
        if st.button("Generate Subtitles"):
            st.session_state.params = {
                "target_lang_code": target_lang_code,
                "align_code": align_code,
                "size_code": size_code,
                "color_code": color_code,
                "model_size_code": model_size_code,
                "resolution_cap_code": resolution_cap_code,
                "segmentation_mode_code": segmentation_mode,
                "email": email_input.strip() if email_input.strip() != "" else None
            }
            st.session_state.is_processing = True
            st.rerun()


# Modal Download and share Dialog
@st.dialog("Download & Share Subtitled Video", width="large")
def show_download_dialog():
    st.markdown('<div class="custom-card-header">Your Video is Ready!</div>', unsafe_allow_html=True)
    
    # Subtitled video player
    if st.session_state.final_video_bytes:
        st.video(st.session_state.final_video_bytes)
        
        # Download button
        output_filename = f"{os.path.splitext(st.session_state.uploaded_filename)[0]}_subtitled.mp4"
        st.download_button(
            label="Download Subtitled Video",
            data=st.session_state.final_video_bytes,
            file_name=output_filename,
            mime="video/mp4"
        )
    else:
        st.error("No completed video file found in session memory.")
        
    st.divider()
    
    # Button to start over and reset state machine
    if st.button("Upload Another Video"):
        start_over()


# =========================================================================
# STATE MACHINE EXECUTION FLOW
# =========================================================================

# STEP 1: Upload Screen
if st.session_state.step == "upload":
    uploaded_file = st.file_uploader(
        "Choose a video file...", 
        type=["mp4", "mov", "avi", "mkv"],
        help="Upload your video file (MP4, MOV, AVI, or MKV)."
    )

    if uploaded_file:
        if st.session_state.use_api:
            with st.spinner("Uploading video file to server..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    r = requests.post(f"{API_URL}/upload", files=files)
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state.video_id = res["video_id"]
                        st.session_state.uploaded_filename = uploaded_file.name
                        st.session_state.step = "configure"
                        st.rerun()
                    else:
                        st.error(f"Upload failed (HTTP {r.status_code}): {r.text}")
                except Exception as e:
                    st.error(f"Error uploading file: {e}")
        else:
            # Standalone mode: save local file copy
            with st.spinner("Saving uploaded file locally..."):
                try:
                    st.session_state.video_id = str(uuid.uuid4())
                    st.session_state.uploaded_filename = uploaded_file.name
                    
                    os.makedirs("uploads", exist_ok=True)
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                    temp_filepath = os.path.join("uploads", f"standalone_{st.session_state.video_id}{file_ext}")
                    
                    with open(temp_filepath, "wb") as f:
                        f.write(uploaded_file.getvalue())
                        
                    st.session_state.uploaded_filepath = temp_filepath
                    st.session_state.step = "configure"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving file: {e}")

# STEP 2: Customization Modal Dialog
elif st.session_state.step == "configure":
    st.info("The customization options are open in the dialog popup overlay.")
    if st.button("Re-open Configuration Dialog"):
        show_configure_dialog()
    else:
        show_configure_dialog()

# STEP 3: Success & Download Screen Modal Dialog
elif st.session_state.step == "download":
    st.info("The finalized video is ready in the popup download overlay.")
    if st.button("Re-open Download & Share Dialog"):
        show_download_dialog()
    else:
        show_download_dialog()


st.divider()
st.caption("Powered by faster-whisper, googletrans, and ffmpeg locally.")
