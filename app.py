import os
import time
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Multilingual Video Subtitle Generator",
    page_icon="🎬",
    layout="centered"
)

# API Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

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

st.title("🎬 Multilingual Video Subtitle Generator")
st.markdown(
    """
    Upload a video with speech, select your target translation language, 
    and burn subtitles directly into the video file locally and free!
    """
)

st.divider()

# Initialize session state variables
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

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
        
        # Upload new file to get video_id
        with st.spinner("Uploading video file..."):
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
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to backend server. Please verify FastAPI is running on http://localhost:8000.")
            except Exception as e:
                st.error(f"Error uploading file: {e}")

# If file is uploaded, show preview and generate options
if st.session_state.video_id:
    st.subheader("🛠️ Configure Subtitle Styling & Position")
    
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
    
    # Render Preview
    preview_url = f"{API_URL}/preview/{st.session_state.video_id}?alignment={align_code}"
    
    with st.spinner("Loading position preview frame..."):
        try:
            preview_resp = requests.get(preview_url)
            if preview_resp.status_code == 200:
                st.image(preview_resp.content, caption="Subtitle Location Preview (approx. 1s mark)", use_column_width=True)
            else:
                st.warning(f"Could not load preview frame (HTTP {preview_resp.status_code}): {preview_resp.text}")
        except Exception as e:
            st.warning(f"Error loading preview frame: {e}")
            
    st.divider()
    st.subheader("🌐 Select Language")
    
    target_lang_name = st.selectbox(
        "Select Target Language for Subtitles:",
        options=list(LANGUAGES.keys()),
        index=0  # Defaults to Spanish
    )
    target_lang_code = LANGUAGES[target_lang_name]
    
    # Action Button
    if st.button("🚀 Generate Subtitles", use_container_width=True):
        st.info("Triggering subtitle generation...")
        
        # 2. Trigger Process Request
        try:
            payload = {
                "target_language": target_lang_code,
                "alignment": align_code
            }
            response = requests.post(f"{API_URL}/process/{st.session_state.video_id}", data=payload)
            
            if response.status_code != 200:
                st.error(f"Failed to trigger process. Server responded with: {response.text}")
            else:
                task_data = response.json()
                task_id = task_data["task_id"]
                st.success("Subtitle generation queued in the background.")
                
                # 3. Polling loop
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
                                    status_box.info(f"⏳ Status: Queued (Waiting for worker...) | Time elapsed: {elapsed:.1f}s")
                                    progress_bar.progress(10)
                                elif status == "processing":
                                    status_box.info(f"⚙️ Status: Processing (Transcribing & Translating...) | Time elapsed: {elapsed:.1f}s")
                                    progress_bar.progress(50)
                            else:
                                status_box.warning(f"Warning: Failed to poll status (HTTP {status_resp.status_code}). Retrying...")
                        except Exception as poll_err:
                            status_box.warning(f"Connection warning: {poll_err}. Retrying status poll...")
                            
                        # Wait before polling again
                        time.sleep(3)
                
                # 4. Final Task resolution
                if status == "completed":
                    progress_bar.progress(100)
                    status_box.success("🎉 Subtitle generation completed successfully!")
                    
                    # Download final video bytes to serve locally in streamlit
                    download_url = f"{API_URL}/download/{task_id}"
                    with st.spinner("Downloading subtitled video from API..."):
                        try:
                            video_resp = requests.get(download_url)
                            if video_resp.status_code == 200:
                                video_bytes = video_resp.content
                                
                                # Display native video player
                                st.subheader("🎥 Preview Subtitled Video")
                                st.video(video_bytes)
                                
                                # Provide download button
                                output_filename = f"{os.path.splitext(uploaded_file.name)[0]}_subtitled_{target_lang_code}.mp4"
                                st.download_button(
                                    label="💾 Download Subtitled Video",
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
                    st.error(f"❌ Subtitle generation failed: {error_reason}")
                    
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to backend server. Please verify FastAPI is running on http://localhost:8000.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

st.divider()
st.caption("Powered by faster-whisper, googletrans, and ffmpeg locally.")

