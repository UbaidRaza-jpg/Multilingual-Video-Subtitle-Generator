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

    /* Sleek Card Headers */
    .custom-card-header {
        font-weight: 700;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #FFFFFF;
        font-size: 1.35rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        letter-spacing: -0.2px;
    }

    /* File Uploader Container */
    div[data-testid="stFileUploader"] {
        background: rgba(26, 29, 36, 0.6) !important;
        border: 2px dashed rgba(168, 85, 247, 0.35) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
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
            <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 30px; color: #333; background-color: #f9f9f9;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee;">
                    <h2 style="color: #4B5563; border-bottom: 2px solid #E5E7EB; padding-bottom: 12px; margin-top: 0;">Subtitle Generation Complete</h2>
                    <p style="font-size: 15px; line-height: 1.6;">Your video <strong>{original_filename}</strong> has been successfully subtitled.</p>
                    <p style="font-size: 15px; line-height: 1.6;">Since the application is running in Standalone Mode, you can find the downloaded file directly on your screen in the browser tab.</p>
                    <hr style="border: 0; border-top: 1px solid #E5E7EB; margin-top: 30px;" />
                    <p style="font-size: 12px; color: #9CA3AF; text-align: center;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
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
    "Marathi (मराठी)": "mr",
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
    "Lao (ລາວ)": "lo",
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

# Initialize session state variables
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "uploaded_filepath" not in st.session_state:
    st.session_state.uploaded_filepath = None

# Form inputs
uploaded_file = st.file_uploader(
    "Choose a video file...", 
    type=["mp4", "mov", "avi", "mkv"],
    help="Upload your video file (MP4, MOV, AVI, or MKV)."
)

# Detect change in uploaded file
if uploaded_file:
    if uploaded_file.name != st.session_state.uploaded_filename:
        # Reset previous state
        st.session_state.video_id = None
        st.session_state.uploaded_filename = None
        st.session_state.uploaded_filepath = None
        
        # Determine upload action based on mode
        if st.session_state.use_api:
            with st.spinner("Uploading video file to server..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    r = requests.post(f"{API_URL}/upload", files=files)
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state.video_id = res["video_id"]
                        st.session_state.uploaded_filename = uploaded_file.name
                        st.success("Video uploaded successfully!")
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
                    st.success("Video saved successfully!")
                except Exception as e:
                    st.error(f"Error saving file: {e}")

# If file is uploaded and processed, show preview and options
if st.session_state.video_id:
    st.markdown('<div class="custom-card-header">Configure Subtitle Styling & Position</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Subtitle alignments
        ALIGNMENTS = {
            "Bottom (Center)": 2,
            "Top (Center)": 8,
            "Middle (Center)": 5,
            "Bottom Left": 1,
            "Bottom Right": 3,
            "Top Left": 7,
            "Top Right": 9
        }
        align_name = st.selectbox(
            "Select Subtitle Position:",
            options=list(ALIGNMENTS.keys()),
            index=0  # Defaults to Bottom (Center)
        )
        align_code = ALIGNMENTS[align_name]
        
    with col2:
        # Font Sizes
        SIZES = {
            "Small (16px)": 16,
            "Medium (20px)": 20,
            "Large (24px)": 24,
            "Extra Large (32px)": 32
        }
        size_name = st.selectbox(
            "Select Font Size:",
            options=list(SIZES.keys()),
            index=1  # Defaults to Medium (20px)
        )
        size_code = SIZES[size_name]
        
    with col3:
        # Font Colors (ASS BGR format)
        COLORS = {
            "White": "&H00FFFFFF",
            "Yellow": "&H0000FFFF",
            "Cyan": "&H00FFFF00",
            "Red": "&H000000FF",
            "Green": "&H0000FF00",
            "Blue": "&H00FF0000"
        }
        color_name = st.selectbox(
            "Select Subtitle Color:",
            options=list(COLORS.keys()),
            index=0  # Defaults to White
        )
        color_code = COLORS[color_name]
    
    # Render Preview
    with st.spinner("Loading subtitle preview frame..."):
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
                    st.warning(f"Could not load preview frame (HTTP {preview_resp.status_code}): {preview_resp.text}")
            else:
                # Standalone preview generation
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
            
    st.divider()
    st.markdown('<div class="custom-card-header">Select Language & Accuracy</div>', unsafe_allow_html=True)
    
    col_lang, col_acc = st.columns(2)
    with col_lang:
        target_lang_name = st.selectbox(
            "Select Target Language for Subtitles:",
            options=list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index("English (Global)")
        )
        target_lang_code = LANGUAGES[target_lang_name]
        
    with col_acc:
        ACCURACY_MODELS = {
            "High Accuracy (Recommended)": "small",
            "Fast / Standard Accuracy": "base"
        }
        accuracy_name = st.selectbox(
            "Select Transcription Accuracy:",
            options=list(ACCURACY_MODELS.keys()),
            index=0
        )
        model_size_code = ACCURACY_MODELS[accuracy_name]
        
    email_input = st.text_input(
        "Email Address for Notifications (Optional):",
        placeholder="Enter your email to receive a notification download link when complete.",
        help="Ensure you configure the SMTP details in your .env file or Streamlit Cloud secrets to enable emails."
    )
    
    # Action Button
    if st.button("Generate Subtitles", use_container_width=True):
        st.info("Triggering subtitle generation...")
        
        if st.session_state.use_api:
            # ---------------------------------------------
            # Mode A: API processing
            # ---------------------------------------------
            try:
                payload = {
                    "target_language": target_lang_code,
                    "alignment": align_code,
                    "font_size": size_code,
                    "font_color": color_code,
                    "email": email_input.strip() if email_input.strip() != "" else None,
                    "model_size": model_size_code
                }
                response = requests.post(f"{API_URL}/process/{st.session_state.video_id}", data=payload)
                
                if response.status_code != 200:
                    st.error(f"Failed to trigger process. Server responded with: {response.text}")
                else:
                    task_data = response.json()
                    task_id = task_data["task_id"]
                    st.success("Subtitle generation queued in the background.")
                    
                    # Polling loop
                    status = "queued"
                    status_box = st.empty()
                    progress_bar = st.progress(0)
                    
                    with st.spinner("Processing video (Transcribing, translating, and burning subtitles)..."):
                        start_time = time.time()
                        
                        while status in ["queued", "processing", "uploaded"]:
                            try:
                                # Poll the status endpoint
                                status_resp = requests.get(f"{API_URL}/status/{task_id}")
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json()
                                    status = status_data["status"]
                                    elapsed = time.time() - start_time
                                    
                                    # Update progress bar and text status
                                    if status in ["queued", "uploaded"]:
                                        status_box.info(f"Status: Queued (Waiting for worker...) | Time elapsed: {elapsed:.1f}s")
                                        progress_bar.progress(10)
                                    elif status == "processing":
                                        status_box.info(f"Status: Processing (Transcribing & Translating...) | Time elapsed: {elapsed:.1f}s")
                                        progress_bar.progress(50)
                                else:
                                    status_box.warning(f"Warning: Failed to poll status (HTTP {status_resp.status_code}). Retrying...")
                            except Exception as poll_err:
                                status_box.warning(f"Connection warning: {poll_err}. Retrying status poll...")
                                
                            # Wait before polling again
                            time.sleep(3)
                    
                    # Final Task resolution
                    if status == "completed":
                        progress_bar.progress(100)
                        status_box.success("Subtitle generation completed successfully!")
                        
                        # Download final video bytes to serve locally in streamlit
                        download_url = f"{API_URL}/download/{task_id}"
                        with st.spinner("Downloading subtitled video from API..."):
                            try:
                                video_resp = requests.get(download_url)
                                if video_resp.status_code == 200:
                                    video_bytes = video_resp.content
                                    
                                    # Display native video player
                                    st.markdown('<div class="custom-card-header">Preview Subtitled Video</div>', unsafe_allow_html=True)
                                    st.video(video_bytes)
                                    
                                    # Provide download button
                                    output_filename = f"{os.path.splitext(uploaded_file.name)[0]}_subtitled_{target_lang_code}.mp4"
                                    st.download_button(
                                        label="Download Subtitled Video",
                                        data=video_bytes,
                                        file_name=output_filename,
                                        mime="video/mp4",
                                        use_container_width=True
                                    )
                                else:
                                    st.error(f"Failed to download finished video from server: {video_resp.status_code}")
                            except Exception as dl_err:
                                st.error(f"Error fetching finalized video: {dl_err}")
                                
                    elif status == "failed":
                        progress_bar.progress(0)
                        try:
                            status_resp = requests.get(f"{API_URL}/status/{task_id}")
                            error_reason = status_resp.json().get("error", "Unknown error")
                        except Exception:
                            error_reason = "Unknown error"
                        st.error(f"Subtitle generation failed: {error_reason}")
                        
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to backend server. Please verify FastAPI is running on http://localhost:8000.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
        else:
            # ---------------------------------------------
            # Mode B: Standalone local container processing
            # ---------------------------------------------
            if LOCAL_ENGINE_AVAILABLE:
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                with st.spinner("Processing video locally... (this might take a few minutes depending on CPU)"):
                    try:
                        status_box.info("Step 1/3: Transcribing & Translating speech...")
                        progress_bar.progress(30)
                        
                        # Process video locally and synchronously
                        output_filepath = process_video(
                            st.session_state.uploaded_filepath,
                            target_lang_code,
                            align_code,
                            size_code,
                            color_code,
                            model_size=model_size_code
                        )
                        
                        if output_filepath and os.path.exists(output_filepath):
                            progress_bar.progress(100)
                            status_box.success("Subtitle generation completed successfully!")
                            
                            # Read final video bytes
                            with open(output_filepath, "rb") as f:
                                video_bytes = f.read()
                                
                            # Display player
                            st.markdown('<div class="custom-card-header">Preview Subtitled Video</div>', unsafe_allow_html=True)
                            st.video(video_bytes)
                            
                            # Provide download button
                            output_filename = f"{os.path.splitext(uploaded_file.name)[0]}_subtitled_{target_lang_code}.mp4"
                            st.download_button(
                                label="Download Subtitled Video",
                                data=video_bytes,
                                file_name=output_filename,
                                mime="video/mp4",
                                use_container_width=True
                            )
                            
                            # Send Email Notification
                            if email_input.strip() != "":
                                status_box.info("Sending email notification...")
                                send_standalone_email(
                                    email_input.strip(),
                                    "completed",
                                    uploaded_file.name
                                )
                                status_box.success("Completed and notification email sent!")
                                
                            # Clean up generated video to save space
                            try:
                                os.remove(output_filepath)
                            except Exception:
                                pass
                        else:
                            raise Exception("Local subtitle burning engine returned empty output path.")
                    except Exception as err:
                        progress_bar.progress(0)
                        status_box.error(f"Subtitle generation failed: {err}")
                        
                        # Send Failure Email
                        if email_input.strip() != "":
                            send_standalone_email(
                                email_input.strip(),
                                "failed",
                                uploaded_file.name,
                                error_reason=str(err)
                            )
                    finally:
                        # Clean up temp uploaded file
                        try:
                            if os.path.exists(st.session_state.uploaded_filepath):
                                os.remove(st.session_state.uploaded_filepath)
                        except Exception:
                            pass
            else:
                st.error("Local engine is not available to run standalone processing.")

st.divider()
st.caption("Powered by faster-whisper, googletrans, and ffmpeg locally.")
