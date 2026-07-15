import os
import uuid
import shutil
import asyncio
import time
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from core_engine import process_video

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
# task_id -> {"status": str, "output_path": str or None, "error": str or None, "target_language": str}
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


def async_process_video_task(task_id: str, input_path: str, target_language: str):
    """
    Background worker that invokes the core video processing engine
    and updates the status database upon completion or failure.
    """
    try:
        tasks_db[task_id]["status"] = "processing"
        
        # Run core processing
        output_path = process_video(input_path, target_language)
        
        if output_path and os.path.exists(output_path):
            tasks_db[task_id]["status"] = "completed"
            tasks_db[task_id]["output_path"] = output_path
        else:
            tasks_db[task_id]["status"] = "failed"
            tasks_db[task_id]["error"] = "Subtitle processing failed to generate output video."
            
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)
        
    finally:
        # Clean up the original uploaded file to save disk space
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as e:
            print(f"Warning: Failed to delete temporary upload file {input_path}: {e}")


@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_language: str = Form(...)
):
    """
    Upload a video file to generate subtitled output.
    Returns immediately with a task ID. Video processing is executed in the background.
    Strictly limits upload size to 25MB.
    """
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".mp4", ".avi", ".mkv", ".mov"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Only .mp4, .avi, .mkv, and .mov are supported."
        )

    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file to temp path with strict 25MB size limit
    temp_filename = f"{task_id}{file_ext}"
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

    # Initialize task status in DB
    tasks_db[task_id] = {
        "status": "queued",
        "output_path": None,
        "error": None,
        "target_language": target_language,
        "original_filename": file.filename
    }

    # Queue background task
    background_tasks.add_task(async_process_video_task, task_id, temp_filepath, target_language)

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Video uploaded successfully. Subtitle generation queued in the background."
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
