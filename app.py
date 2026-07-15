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

# Form inputs
uploaded_file = st.file_uploader(
    "Choose a video file...", 
    type=["mp4", "mov", "avi", "mkv"],
    help="Upload your video file (MP4, MOV, AVI, or MKV)."
)

target_lang_name = st.selectbox(
    "Select Target Language for Subtitles:",
    options=list(LANGUAGES.keys()),
    index=0  # Defaults to Spanish
)
target_lang_code = LANGUAGES[target_lang_name]

# Action Button
if st.button("🚀 Generate Subtitles", use_container_width=True):
    if not uploaded_file:
        st.error("Please upload a video file first.")
    else:
        st.info("Uploading video and queueing the subtitle job...")
        
        # 1. POST file to backend
        try:
            # Prepare files and data payload
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"target_language": target_lang_code}
            
            # Send post request
            response = requests.post(f"{API_URL}/upload", files=files, data=data)
            
            if response.status_code != 200:
                st.error(f"Failed to initiate task. Server responded with: {response.text}")
            else:
                task_data = response.json()
                task_id = task_data["task_id"]
                st.success(f"Video uploaded successfully! Task ID: {task_id}")
                
                # 2. Polling loop
                status = "queued"
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                # We show a spinner while polling
                with st.spinner("Processing video (Transcribing, translating, and burning subtitles)..."):
                    start_time = time.time()
                    
                    while status in ["queued", "processing"]:
                        try:
                            # Poll the status endpoint
                            status_resp = requests.get(f"{API_URL}/status/{task_id}")
                            if status_resp.status_code == 200:
                                status_data = status_resp.json()
                                status = status_data["status"]
                                elapsed = time.time() - start_time
                                
                                # Update progress bar and text status
                                if status == "queued":
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
                
                # 3. Final Task resolution
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
                    # Try to fetch error reason
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
