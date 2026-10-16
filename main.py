import os
import uuid
import asyncio
import time
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
    Request,
    Response,
    Security,
    status
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from core_engine import process_video, generate_subtitle_preview
from security import (
    rate_limiter,
    verify_admin_key,
    hash_password,
    verify_password,
    sanitize_filename,
    validate_uuid,
    is_safe_path,
    validate_font_name,
    validate_font_color,
    validate_font_size,
    validate_alignment,
    validate_language_code,
    validate_border_style,
    validate_resolution_cap,
    validate_model_size,
    validate_segmentation_mode,
    validate_email_address,
    sanitize_email_content,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_MIME_TYPES
)

SERVER_START_TIME = time.time()

app = FastAPI(
    title="Multilingual Video Subtitle Generator API",
    description="Secure, production-hardened API for transcribing, translating, and hardcoding subtitles into video files locally.",
    version="1.1.0"
)

# =====================================================================
# Security Headers Middleware
# =====================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: 'unsafe-inline'; "
            "frame-ancestors 'none'; "
            "object-src 'none';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)


# =====================================================================
# Sliding-Window Rate Limiting Middleware
# =====================================================================

class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract client IP safely (supports trusted reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown_client")
        
        path = request.url.path
        method = request.method
        
        # Heavy computing endpoints (Whisper AI transcription & FFmpeg transcoding)
        if path == "/upload" and method == "POST":
            allowed, retry_after = await rate_limiter.is_allowed(f"upload:{client_ip}", max_requests=10, window_seconds=60)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many video upload requests. Please wait before uploading another file."},
                    headers={"Retry-After": str(retry_after)}
                )
        elif path.startswith(("/process", "/transcribe")) and method == "POST":
            allowed, retry_after = await rate_limiter.is_allowed(f"process:{client_ip}", max_requests=10, window_seconds=60)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many video processing requests. Please wait for previous jobs to complete."},
                    headers={"Retry-After": str(retry_after)}
                )
        elif path.startswith("/preview") and method == "GET":
            allowed, retry_after = await rate_limiter.is_allowed(f"preview:{client_ip}", max_requests=25, window_seconds=60)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many preview requests. Please wait a moment."},
                    headers={"Retry-After": str(retry_after)}
                )
        else:
            # General endpoints (status polls, downloads, static assets)
            allowed, retry_after = await rate_limiter.is_allowed(f"general:{client_ip}", max_requests=120, window_seconds=60)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please wait a moment."},
                    headers={"Retry-After": str(retry_after)}
                )
                
        return await call_next(request)

app.add_middleware(RateLimitingMiddleware)


# =====================================================================
# Configurable CORS Configuration
# =====================================================================

raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
if raw_origins.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    if raw_origins.strip():
        ALLOWED_ORIGINS = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
    else:
        ALLOWED_ORIGINS = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "https://built-by-ubaid-multilingual-video-subtitle-generator.streamlit.app",
            "https://ubaidraza-jpg.github.io"
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-API-Key"],
    )


# =====================================================================
# Admin Authentication Setup
# =====================================================================

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    ADMIN_API_KEY = secrets.token_hex(24)
    print("=" * 60)
    print("SECURITY NOTICE: No ADMIN_API_KEY found in environment.")
    print(f"Generated Ephemeral Admin API Key: {ADMIN_API_KEY}")
    print("Set ADMIN_API_KEY in your .env to preserve a persistent key.")
    print("=" * 60)

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)

async def require_admin_auth(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    header_key: Optional[str] = Security(api_key_header)
):
    """
    Dependency to protect administrative routes using constant-time comparison.
    """
    token = None
    if header_key:
        token = header_key
    elif bearer and bearer.credentials:
        token = bearer.credentials
        
    if not token or not verify_admin_key(token, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid Admin Authentication Key required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True


# =====================================================================
# Serve Custom Frontend Files
# =====================================================================

@app.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")

@app.get("/styles.css")
async def serve_styles():
    return FileResponse("frontend/styles.css")

@app.get("/main.js")
async def serve_js():
    return FileResponse("frontend/main.js")

@app.get("/favicon.svg")
@app.get("/favicon.ico")
async def serve_favicon():
    return FileResponse("frontend/favicon.svg", media_type="image/svg+xml")

@app.get("/privacy")
@app.get("/privacy.html")
async def serve_privacy():
    return FileResponse("frontend/privacy.html")

@app.get("/terms")
@app.get("/terms.html")
async def serve_terms():
    return FileResponse("frontend/terms.html")


# Directory configs
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "temp_outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# In-memory database to store task statuses
tasks_db: Dict[str, Dict[str, Any]] = {}


# =====================================================================
# Periodic File Cleanup Task
# =====================================================================

async def periodic_cleanup_task():
    """
    Background task that runs periodically, cleaning up uploads/ and temp_outputs/
    directories. Deletes files older than 15 minutes.
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
    asyncio.create_task(periodic_cleanup_task())


# =====================================================================
# Email Notifications (XSS & HTML Injection Sanitized)
# =====================================================================

def send_email_notification(to_email: str, task_id: str, status: str, filename: str, error_reason: str = None):
    """
    Sends an email notification via SMTP when a subtitle task completes or fails.
    Dynamic variables are strictly HTML-escaped to prevent HTML injection in mail clients.
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
        safe_filename = sanitize_email_content(filename)
        safe_error = sanitize_email_content(error_reason)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Subtitle Task: {safe_filename} - {status.upper()}"
        msg["From"] = from_email
        msg["To"] = to_email
        
        base_url = os.environ.get("SERVER_URL", "http://localhost:8000")
        download_url = f"{base_url}/download/{task_id}"
        
        if status == "completed":
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #4CAF50;">Subtitle Generation Complete!</h2>
                <p>Your video <strong>{safe_filename}</strong> has been successfully subtitled.</p>
                <p>You can download it now by clicking the link below:</p>
                <p style="margin-top: 20px;">
                    <a href="{download_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Download Subtitled Video</a>
                </p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">Automated notification from Multilingual Video Subtitle Generator.</p>
            </body>
            </html>
            """
        else:
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #F44336;">Subtitle Generation Failed</h2>
                <p>Unfortunately, processing your video <strong>{safe_filename}</strong> encountered an error.</p>
                <p><strong>Error Reason:</strong></p>
                <blockquote style="background: #f9f9f9; border-left: 10px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px;">
                    <code>{safe_error}</code>
                </blockquote>
                <p>Please try uploading the file again with different settings.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
                <p style="font-size: 12px; color: #777;">Automated notification from Multilingual Video Subtitle Generator.</p>
            </body>
            </html>
            """
            
        msg.attach(MIMEText(html_body, "html"))
        
        server = smtplib.SMTP(host, int(port), timeout=10)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        print(f"Notification email successfully sent to {to_email}")
    except Exception as e:
        print(f"Error sending notification email: {e}")


# =====================================================================
# Video Processing Background Task
# =====================================================================

def async_process_video_task(task_id: str, input_path: str, target_language: str, alignment: int, font_size: int, font_color: str, email: str = None, model_size: str = "small", resolution_cap: str = "original", segmentation_mode: str = "line_by_line", font_name: str = "Arial", border_style: str = "outline", srt_path: str = None):
    original_filename = tasks_db[task_id]["original_filename"]
    try:
        tasks_db[task_id]["status"] = "processing"
        
        output_path = process_video(
            input_path,
            target_language,
            alignment,
            font_size,
            font_color,
            model_size=model_size,
            resolution_cap=resolution_cap,
            segmentation_mode=segmentation_mode,
            font_name=font_name,
            border_style=border_style,
            srt_path=srt_path
        )
        
        if output_path and os.path.exists(output_path):
            tasks_db[task_id]["status"] = "completed"
            tasks_db[task_id]["output_path"] = output_path
            
            if email:
                send_email_notification(email, task_id, "completed", original_filename)
        else:
            tasks_db[task_id]["status"] = "failed"
            error_msg = "Subtitle processing failed to produce output video."
            tasks_db[task_id]["error"] = error_msg
            
            if email:
                send_email_notification(email, task_id, "failed", original_filename, error_msg)
            
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)
        
        if email:
            send_email_notification(email, task_id, "failed", original_filename, str(e))
        
    finally:
        # Clean up temporary upload file
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as e:
            print(f"Warning: Failed to delete temporary upload file: {e}")
            
        # Clean up custom srt file if passed
        if srt_path:
            try:
                if os.path.exists(srt_path):
                    os.remove(srt_path)
            except Exception as e:
                print(f"Warning: Failed to delete custom SRT file: {e}")


# =====================================================================
# API Endpoints (Hardened & Sanitized)
# =====================================================================

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Step 1: Upload a video file.
    Validates file extension, MIME type, size, and sanitizes filename.
    Strictly limits size to 200MB.
    """
    # Sanitize and validate filename
    safe_name = sanitize_filename(file.filename)
    file_ext = os.path.splitext(safe_name)[1].lower()
    
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}."
        )

    # Validate MIME type if provided
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES and not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Must be a valid video stream."
        )

    # Generate a unique cryptographic task ID
    video_id = str(uuid.uuid4())
    temp_filename = f"{video_id}{file_ext}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)
    
    if not is_safe_path(UPLOAD_DIR, temp_filepath):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file destination path.")
    
    MAX_SIZE = 200 * 1024 * 1024  # 200 MB
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
                    buffer.close()
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds maximum allowed size of 200MB."
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file securely."
        )

    # Initialize video task in memory
    tasks_db[video_id] = {
        "status": "uploaded",
        "filepath": temp_filepath,
        "original_filename": safe_name,
        "output_path": None,
        "error": None,
        "target_language": None,
        "created_at": time.time()
    }

    return {
        "video_id": video_id,
        "filename": safe_name,
        "status": "uploaded"
    }


@app.get("/preview/{video_id}")
async def get_video_preview(
    video_id: str,
    alignment: int = 2,
    font_size: int = 20,
    font_color: str = "&H00FFFFFF",
    font_name: str = "Arial",
    border_style: str = "outline"
):
    """
    Step 2: Generate and return a single JPEG frame at the 1-second mark 
    with a sample subtitle burned at the chosen styling parameters.
    """
    if not validate_uuid(video_id) or video_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
    task = tasks_db[video_id]
    if not os.path.exists(task["filepath"]) or not is_safe_path(UPLOAD_DIR, task["filepath"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded video file not found or already cleaned up.")
        
    # Sanitize all styling arguments
    alignment = validate_alignment(alignment)
    font_size = validate_font_size(font_size)
    font_color = validate_font_color(font_color)
    font_name = validate_font_name(font_name)
    border_style = validate_border_style(border_style)
    
    clean_color_code = font_color.replace("&", "").replace("#", "")
    preview_filename = f"preview_{video_id}_{alignment}_{font_size}_{clean_color_code}.jpg"
    preview_filepath = os.path.join(OUTPUT_DIR, preview_filename)
    
    if not is_safe_path(OUTPUT_DIR, preview_filepath):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid preview destination path.")
    
    success = generate_subtitle_preview(
        task["filepath"],
        alignment,
        font_size,
        font_color,
        preview_filepath,
        font_name=font_name,
        border_style=border_style
    )
    if not success or not os.path.exists(preview_filepath):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to extract and burn preview frame.")
        
    return FileResponse(preview_filepath, media_type="image/jpeg")


@app.post("/process/{video_id}")
async def process_video_endpoint(
    video_id: str,
    background_tasks: BackgroundTasks,
    target_language: str = Form(...),
    alignment: int = Form(2),
    font_size: int = Form(20),
    font_color: str = Form("&H00FFFFFF"),
    email: Optional[str] = Form(None),
    model_size: str = Form("small"),
    resolution_cap: str = Form("original"),
    segmentation_mode: str = Form("line_by_line"),
    font_name: str = Form("Arial"),
    border_style: str = Form("outline"),
    srt_path: Optional[str] = Form(None)
):
    """
    Step 3: Trigger background transcription and subtitle hardcoding.
    """
    if not validate_uuid(video_id) or video_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
    task = tasks_db[video_id]
    if task["status"] in ["queued", "processing", "completed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is already in state '{task['status']}'")
        
    if not os.path.exists(task["filepath"]) or not is_safe_path(UPLOAD_DIR, task["filepath"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded video file has been cleaned up. Please upload again.")

    # Sanitize and validate all parameters
    target_language = validate_language_code(target_language)
    alignment = validate_alignment(alignment)
    font_size = validate_font_size(font_size)
    font_color = validate_font_color(font_color)
    font_name = validate_font_name(font_name)
    border_style = validate_border_style(border_style)
    resolution_cap = validate_resolution_cap(resolution_cap)
    model_size = validate_model_size(model_size)
    segmentation_mode = validate_segmentation_mode(segmentation_mode)
    safe_email = validate_email_address(email)

    task["status"] = "queued"
    task["target_language"] = target_language

    background_tasks.add_task(
        async_process_video_task, 
        video_id, 
        task["filepath"], 
        target_language, 
        alignment,
        font_size,
        font_color,
        safe_email,
        model_size,
        resolution_cap,
        segmentation_mode,
        font_name,
        border_style,
        srt_path
    )

    return {
        "task_id": video_id,
        "status": "queued",
        "message": f"Subtitle generation queued in background. Target language: '{target_language}'"
    }


@app.post("/process_custom/{video_id}")
async def process_custom_video_endpoint(
    video_id: str,
    background_tasks: BackgroundTasks,
    srt_file: UploadFile = File(...),
    target_language: str = Form(...),
    alignment: int = Form(2),
    font_size: int = Form(20),
    font_color: str = Form("&H00FFFFFF"),
    email: Optional[str] = Form(None),
    model_size: str = Form("small"),
    resolution_cap: str = Form("original"),
    segmentation_mode: str = Form("line_by_line"),
    font_name: str = Form("Arial"),
    border_style: str = Form("outline")
):
    """
    Step 3 (Custom/Edited): Trigger subtitle burning using an edited client SRT file.
    """
    if not validate_uuid(video_id) or video_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
    task = tasks_db[video_id]
    if task["status"] in ["queued", "processing", "completed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is already in state '{task['status']}'")
        
    if not os.path.exists(task["filepath"]) or not is_safe_path(UPLOAD_DIR, task["filepath"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded video file has been cleaned up. Please upload again.")

    # Validate SRT extension
    srt_ext = os.path.splitext(srt_file.filename)[1].lower() if srt_file.filename else ".srt"
    if srt_ext != ".srt":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom subtitle file must be in .srt format.")

    # Save custom srt_file to temp_outputs (max 5MB for SRT files)
    MAX_SRT_SIZE = 5 * 1024 * 1024
    content = await srt_file.read(MAX_SRT_SIZE + 1)
    if len(content) > MAX_SRT_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="SRT subtitle file exceeds 5MB limit.")

    custom_srt_name = f"custom_{video_id}_{uuid.uuid4().hex}.srt"
    custom_srt_path = os.path.join(OUTPUT_DIR, custom_srt_name)
    
    if not is_safe_path(OUTPUT_DIR, custom_srt_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid destination path for SRT file.")
    
    try:
        with open(custom_srt_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save custom SRT file.")

    target_language = validate_language_code(target_language)
    alignment = validate_alignment(alignment)
    font_size = validate_font_size(font_size)
    font_color = validate_font_color(font_color)
    font_name = validate_font_name(font_name)
    border_style = validate_border_style(border_style)
    resolution_cap = validate_resolution_cap(resolution_cap)
    model_size = validate_model_size(model_size)
    segmentation_mode = validate_segmentation_mode(segmentation_mode)
    safe_email = validate_email_address(email)

    task["status"] = "queued"
    task["target_language"] = target_language

    background_tasks.add_task(
        async_process_video_task, 
        video_id, 
        task["filepath"], 
        target_language, 
        alignment,
        font_size,
        font_color,
        safe_email,
        model_size,
        resolution_cap,
        segmentation_mode,
        font_name,
        border_style,
        custom_srt_path
    )

    return {
        "task_id": video_id,
        "status": "queued",
        "message": f"Custom subtitle generation queued in background. Target language: '{target_language}'"
    }


@app.post("/transcribe/{video_id}")
async def transcribe_only_endpoint(
    video_id: str,
    target_language: str = Form(...),
    model_size: str = Form("small"),
    segmentation_mode: str = Form("line_by_line"),
    bilingual: bool = Form(False)
):
    """
    Generate and translate subtitle blocks for interactive timeline review without hardcoding.
    """
    if not validate_uuid(video_id) or video_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
    task = tasks_db[video_id]
    if not os.path.exists(task["filepath"]) or not is_safe_path(UPLOAD_DIR, task["filepath"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found or cleaned up.")
    
    target_language = validate_language_code(target_language)
    model_size = validate_model_size(model_size)
    segmentation_mode = validate_segmentation_mode(segmentation_mode)
    
    raw_srt = os.path.join(OUTPUT_DIR, f"transcribe_{video_id}_raw_{uuid.uuid4().hex}.srt")
    translated_srt = os.path.join(OUTPUT_DIR, f"transcribe_{video_id}_trans_{uuid.uuid4().hex}.srt")
    
    try:
        from core_engine import transcribe_video, translate_srt, parse_srt
        transcribe_video(task["filepath"], raw_srt, model_size=model_size, segmentation_mode=segmentation_mode)
        translate_srt(raw_srt, translated_srt, target_language, bilingual=bilingual)
        
        blocks = parse_srt(translated_srt)
        
        # Immediate cleanup of temporary intermediate files
        for temp_f in [raw_srt, translated_srt]:
            if os.path.exists(temp_f):
                try:
                    os.remove(temp_f)
                except Exception:
                    pass
            
        return {"status": "success", "blocks": blocks}
    except Exception as e:
        for temp_f in [raw_srt, translated_srt]:
            if os.path.exists(temp_f):
                try:
                    os.remove(temp_f)
                except Exception:
                    pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Transcription/translation process failed.")


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check current status of a subtitle task.
    """
    if not validate_uuid(task_id) or task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
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
    Download the subtitled output video once completed.
    Enforces path traversal checks and UUID validation.
    """
    if not validate_uuid(task_id) or task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    task = tasks_db[task_id]
    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Task is in '{task['status']}' state. Subtitles must be completed to download."
        )
        
    output_path = task.get("output_path")
    if not output_path or not os.path.exists(output_path) or not is_safe_path(OUTPUT_DIR, output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The subtitled video file could not be found on the server."
        )
        
    original_basename = os.path.splitext(sanitize_filename(task["original_filename"]))[0]
    safe_target = validate_language_code(task.get("target_language") or "subtitled")
    download_filename = f"{original_basename}_subtitled_{safe_target}.mp4"
    
    return FileResponse(
        path=output_path,
        filename=download_filename,
        media_type="video/mp4"
    )


# =====================================================================
# Protected Admin Routes
# =====================================================================

@app.get("/admin/stats")
async def get_admin_stats(authenticated: bool = Security(require_admin_auth)):
    """
    Protected Admin Route: Returns system status, task counts, and storage metrics.
    Requires Bearer token or X-Admin-API-Key header.
    """
    counts = {"uploaded": 0, "queued": 0, "processing": 0, "completed": 0, "failed": 0}
    for t in tasks_db.values():
        st_val = t.get("status", "unknown")
        counts[st_val] = counts.get(st_val, 0) + 1
        
    upload_size = sum(
        os.path.getsize(os.path.join(UPLOAD_DIR, f))
        for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))
    ) if os.path.exists(UPLOAD_DIR) else 0

    output_size = sum(
        os.path.getsize(os.path.join(OUTPUT_DIR, f))
        for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))
    ) if os.path.exists(OUTPUT_DIR) else 0

    return {
        "status": "healthy",
        "uptime_seconds": int(time.time() - SERVER_START_TIME),
        "total_tasks": len(tasks_db),
        "task_counts": counts,
        "storage": {
            "upload_dir_bytes": upload_size,
            "output_dir_bytes": output_size
        }
    }


@app.get("/admin/tasks")
async def list_admin_tasks(authenticated: bool = Security(require_admin_auth)):
    """
    Protected Admin Route: List all tasks currently registered in memory.
    Requires Bearer token or X-Admin-API-Key header.
    """
    safe_tasks = []
    for tid, t in tasks_db.items():
        safe_tasks.append({
            "task_id": tid,
            "status": t.get("status"),
            "original_filename": t.get("original_filename"),
            "target_language": t.get("target_language"),
            "has_output": bool(t.get("output_path") and os.path.exists(t.get("output_path", ""))),
            "created_at": t.get("created_at")
        })
    return {"tasks": safe_tasks}


@app.post("/admin/cleanup")
async def trigger_admin_cleanup(authenticated: bool = Security(require_admin_auth)):
    """
    Protected Admin Route: Force immediate cleanup of expired temporary files.
    Requires Bearer token or X-Admin-API-Key header.
    """
    deleted_files = []
    now = time.time()
    FILE_MAX_AGE = 15 * 60
    
    for folder in [UPLOAD_DIR, OUTPUT_DIR]:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isdir(filepath) or filename.startswith("."):
                continue
            if now - os.path.getmtime(filepath) > FILE_MAX_AGE:
                try:
                    os.remove(filepath)
                    deleted_files.append(filename)
                except Exception:
                    pass
    return {"message": f"Cleanup executed successfully. Removed {len(deleted_files)} files.", "deleted_count": len(deleted_files)}


# =====================================================================
# Application Entrypoint (Debug / Reload disabled)
# =====================================================================

if __name__ == "__main__":
    import uvicorn
    # Debug/reload explicitly disabled for production stability and security
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
