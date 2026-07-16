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
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2>Subtitle Generation Complete!</h2>
                <p>Your video <strong>{original_filename}</strong> has been successfully subtitled.</p>
                <p>Since the application is running in Standalone Mode, you can find the downloaded file directly on your screen in the browser tab.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2>Subtitle Generation Failed</h2>
                <p>Unfortunately, processing your video <strong>{original_filename}</strong> ran into an error.</p>
                <p><strong>Error Reason:</strong></p>
                <blockquote style="background: #f9f9f9; border-left: 10px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px;">
                    <code>{error_reason}</code>
                </blockquote>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
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
    "Spanish (Español)": "es",
    "French (Français)": "fr",
    "German (Deutsch)": "de",
    "Urdu (اردو)": "ur",
    "Hindi (हिन्दी)": "hi",
    "Arabic (العربية)": "ar",
    "Chinese Simplified (简体中文)": "zh-cn",
    "Japanese (日本語)": "ja",
    "Italian (Italiano)": "it",
    "Portuguese (Português)": "pt",
    "Russian (Русский)": "ru",
    "English": "en"
}

st.title("Multilingual Video Subtitle Generator")
st.markdown(
    """
    Upload a video with speech, select your target translation language, 
    and burn subtitles directly into the video file locally and free!
    """
)

# Show running mode
if st.session_state.use_api:
    st.success("Connected to backend API server.")
else:
    st.info("Running in **Standalone Mode** (processing will run directly inside this app instance).")

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
    st.subheader("Configure Subtitle Styling & Position")
    
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
    st.subheader("Select Language & Notifications")
    
    target_lang_name = st.selectbox(
        "Select Target Language for Subtitles:",
        options=list(LANGUAGES.keys()),
        index=0  # Defaults to Spanish
    )
    target_lang_code = LANGUAGES[target_lang_name]
    
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
                    "email": email_input.strip() if email_input.strip() != "" else None
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
                                    st.subheader("Preview Subtitled Video")
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
                            color_code
                        )
                        
                        if output_filepath and os.path.exists(output_filepath):
                            progress_bar.progress(100)
                            status_box.success("Subtitle generation completed successfully!")
                            
                            # Read final video bytes
                            with open(output_filepath, "rb") as f:
                                video_bytes = f.read()
                                
                            # Display player
                            st.subheader("Preview Subtitled Video")
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
