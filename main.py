import os
import uuid
import shutil
import asyncio
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from core_engine import process_video, generate_subtitle_preview

app = FastAPI(
    title="Multilingual Video Subtitle Generator API",
    description="API for transcribing, translating, and hardcoding subtitles into video files locally.",
    version="1.0.0"
)

# Directory configs
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "temp_outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# In-memory database to store task statuses
# task_id -> {"status": str, "filepath": str, "output_path": str or None, "error": str or None, "target_language": str}
tasks_db = {}


async def periodic_cleanup_task():
    """
    Background task that runs forever, cleaning up uploads/ and temp_outputs/
    directories every 5 minutes. Deletes files older than 15 minutes.
    """
    CLEANUP_INTERVAL = 300  # 5 minutes
    FILE_MAX_AGE = 15 * 60  # 15 minutes
    
    while True:
        try:
            print("Running background file cleanup utility...")
            now = time.time()
            for folder in [UPLOAD_DIR, OUTPUT_DIR]:
                if not os.path.exists(folder):
                    continue
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isdir(filepath) or filename.startswith("."):
                        continue
                    # Check modification time
                    mtime = os.path.getmtime(filepath)
                    age = now - mtime
                    if age > FILE_MAX_AGE:
                        try:
                            os.remove(filepath)
                            print(f"Cleanup: Deleted old file {filepath} (age: {age/60:.1f} mins)")
                        except Exception as e:
                            print(f"Cleanup: Failed to delete {filepath}: {e}")
        except Exception as e:
            print(f"Cleanup task encountered error: {e}")
            
        await asyncio.sleep(CLEANUP_INTERVAL)


@app.on_event("startup")
async def startup_event():
    # Start periodic cleanup task
    asyncio.create_task(periodic_cleanup_task())


def send_email_notification(to_email: str, task_id: str, status: str, filename: str, error_reason: str = None):
    """
    Sends an email notification via SMTP when a subtitle task completes or fails.
    """
    host = os.environ.get("SMTP_HOST")
    port = os.environ.get("SMTP_PORT")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL", username)
    
    if not all([host, port, username, password]):
        print("Email notification skipped: SMTP environment variables are not fully configured in .env.")
        return
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Subtitle Task: {filename} - {status.upper()}"
        msg["From"] = from_email
        msg["To"] = to_email
        
        base_url = os.environ.get("SERVER_URL", "http://localhost:8000")
        download_url = f"{base_url}/download/{task_id}"
        
        if status == "completed":
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #4CAF50;">Subtitle Generation Complete!</h2>
                <p>Your video <strong>{filename}</strong> has been successfully subtitled.</p>
                <p>You can download it now by clicking the link below:</p>
                <p style="margin-top: 20px;">
                    <a href="{download_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Download Subtitled Video</a>
                </p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #F44336;">Subtitle Generation Failed</h2>
                <p>Unfortunately, processing your video <strong>{filename}</strong> ran into an error.</p>
                <p><strong>Error Reason:</strong></p>
                <blockquote style="background: #f9f9f9; border-left: 10px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px;">
                    <code>{error_reason}</code>
                </blockquote>
                <p>Please try uploading the file again with different settings.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">This is an automated notification from the Multilingual Video Subtitle Generator.</p>
            </body>
            </html>
            """
            
        msg.attach(MIMEText(html, "html"))
        
        print(f"Connecting to SMTP server {host}:{port}...")
        server = smtplib.SMTP(host, int(port))
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        print(f"Notification email successfully sent to {to_email}")
    except Exception as e:
        print(f"Error sending notification email to {to_email}: {e}")


def async_process_video_task(task_id: str, input_path: str, target_language: str, alignment: int, font_size: int, font_color: str, email: str = None):
    """
    Background worker that invokes the core video processing engine
    and updates the status database upon completion or failure.
    """
    original_filename = tasks_db[task_id]["original_filename"]
    try:
        tasks_db[task_id]["status"] = "processing"
        
        # Run core processing with specified alignment position, font size, and color
        output_path = process_video(input_path, target_language, alignment, font_size, font_color)
        
        if output_path and os.path.exists(output_path):
            tasks_db[task_id]["status"] = "completed"
            tasks_db[task_id]["output_path"] = output_path
            
            # Send Success Email
            if email:
                send_email_notification(email, task_id, "completed", original_filename)
        else:
            tasks_db[task_id]["status"] = "failed"
            error_msg = "Subtitle processing failed to generate output video."
            tasks_db[task_id]["error"] = error_msg
            
            # Send Fail Email
            if email:
                send_email_notification(email, task_id, "failed", original_filename, error_msg)
            
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)
        
        # Send Fail Email
        if email:
            send_email_notification(email, task_id, "failed", original_filename, str(e))
        
    finally:
        # Clean up the original uploaded file to save disk space
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as e:
            print(f"Warning: Failed to delete temporary upload file {input_path}: {e}")


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Step 1: Upload a video file.
    Saves the file to uploads/ directory and returns a video_id.
    Strictly limits size to 25MB.
    """
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".mp4", ".avi", ".mkv", ".mov"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Only .mp4, .avi, .mkv, and .mov are supported."
        )

    # Generate a unique task ID
    video_id = str(uuid.uuid4())
    
    # Save uploaded file to temp path with strict 25MB size limit
    temp_filename = f"{video_id}{file_ext}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)
    
    MAX_SIZE = 25 * 1024 * 1024  # 25 MB
    total_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunk
    
    try:
        with open(temp_filepath, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_SIZE:
                    # Close and delete the file immediately
                    buffer.close()
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Maximum allowed size is 25MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    # Initialize video task in DB
    tasks_db[video_id] = {
        "status": "uploaded",
        "filepath": temp_filepath,
        "original_filename": file.filename,
        "output_path": None,
        "error": None,
        "target_language": None
    }

    return {
        "video_id": video_id,
        "filename": file.filename,
        "status": "uploaded"
    }


@app.get("/preview/{video_id}")
async def get_video_preview(video_id: str, alignment: int = 2, font_size: int = 20, font_color: str = "&H00FFFFFF"):
    """
    Step 2: Generate and return a single JPEG frame at the 1-second mark 
    with a sample subtitle burned at the chosen styling parameters.
    """
    if video_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Video not found")
        
    task = tasks_db[video_id]
    if not os.path.exists(task["filepath"]):
        raise HTTPException(status_code=404, detail="Uploaded video file not found or already cleaned up.")
        
    # Standardize preview filenames to avoid name conflicts
    preview_filename = f"preview_{video_id}_{alignment}_{font_size}_{font_color.replace('&', '').replace('#', '')}.jpg"
    preview_filepath = os.path.join(OUTPUT_DIR, preview_filename)
    
    success = generate_subtitle_preview(task["filepath"], alignment, font_size, font_color, preview_filepath)
    if not success or not os.path.exists(preview_filepath):
        raise HTTPException(status_code=500, detail="Failed to extract and burn preview frame.")
        
    return FileResponse(preview_filepath, media_type="image/jpeg")


@app.post("/process/{video_id}")
async def process_video_endpoint(
    video_id: str,
    background_tasks: BackgroundTasks,
    target_language: str = Form(...),
    alignment: int = Form(2),
    font_size: int = Form(20),
    font_color: str = Form("&H00FFFFFF"),
    email: str = Form(None)
):
    """
    Step 3: Trigger the full background transcription and subtitle burning process.
    """
    if video_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Video not found")
        
    task = tasks_db[video_id]
    if task["status"] in ["queued", "processing", "completed"]:
        raise HTTPException(status_code=400, detail=f"Task is already in state '{task['status']}'")
        
    if not os.path.exists(task["filepath"]):
        raise HTTPException(status_code=404, detail="Uploaded video file has been cleaned up. Please upload again.")

    # Update task details to queued
    task["status"] = "queued"
    task["target_language"] = target_language

    # Start task in background
    background_tasks.add_task(
        async_process_video_task, 
        video_id, 
        task["filepath"], 
        target_language, 
        alignment,
        font_size,
        font_color,
        email
    )

    return {
        "task_id": video_id,
        "status": "queued",
        "message": f"Subtitle generation started in the background. Target language: '{target_language}'"
    }





@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check current status of a subtitle generation task.
    Returns status, error (if failed), and download link (if completed).
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = tasks_db[task_id]
    response = {
        "task_id": task_id,
        "status": task["status"],
        "target_language": task["target_language"],
        "original_filename": task["original_filename"]
    }
    
    if task["status"] == "completed":
        response["download_url"] = f"/download/{task_id}"
    elif task["status"] == "failed":
        response["error"] = task["error"]
        
    return response


@app.get("/download/{task_id}")
async def download_output_video(task_id: str):
    """
    Download the subtitled output video once task is completed.
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = tasks_db[task_id]
    if task["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Task is in '{task['status']}' state. Subtitles must be completed to download."
        )
        
    output_path = task["output_path"]
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="The subtitled video file could not be found on the server."
        )
        
    original_basename = os.path.splitext(task["original_filename"])[0]
    download_filename = f"{original_basename}_subtitled_{task['target_language']}.mp4"
    
    return FileResponse(
        path=output_path,
        filename=download_filename,
        media_type="video/mp4"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
