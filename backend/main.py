"""
BetaView API
FastAPI backend for climbing video analysis.
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone
import json
import gzip
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from processor import process_video_file
from heuristics import calculate_all_metrics
from visualizer import annotate_video, VisualizationConfig, create_clean_video
from coach import generate_coach_feedback, format_metrics_for_display

load_dotenv()

# Configuration
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/betaview/uploads"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/betaview/outputs"))
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
CLEANUP_AFTER_HOURS = 24

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup: cleanup old files
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CLEANUP_AFTER_HOURS)
    for directory in [UPLOAD_DIR, OUTPUT_DIR]:
        for f in directory.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    f.unlink(missing_ok=True)

    yield
    # Shutdown: cleanup code here if needed


app = FastAPI(
    title="BetaView API",
    description="Climbing video analysis for technique improvement",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (use Redis for production)
jobs = {}


class JobStatus(BaseModel):
    id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    created_at: str
    metrics: Optional[dict] = None
    feedback: Optional[str] = None
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    job_id: str
    status: str
    metrics: dict
    formatted_metrics: dict
    feedback: str
    video_url: str
    clean_video_url: str
    duration: float


@app.get("/")
async def root():
    return {"status": "ok", "service": "betaview-api", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """
    Upload a climbing video for analysis.
    Returns a job ID to poll for results.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not supported. Use: {ALLOWED_EXTENSIONS}")

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{job_id}{ext}"

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                400, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )

        with open(upload_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")

    # Create job
    jobs[job_id] = JobStatus(
        id=job_id,
        status="pending",
        progress=0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    # Start processing in background
    background_tasks.add_task(process_job, job_id, str(upload_path))

    return {"job_id": job_id, "status": "pending"}


async def process_job(job_id: str, video_path: str):
    """Process a video analysis job."""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        job.status = "processing"
        job.progress = 10

        # Process video
        pose_frames, trajectories, video_info = await asyncio.to_thread(
            process_video_file, video_path
        )
        job.progress = 50

        if not pose_frames:
            raise ValueError(
                "No poses detected in video. Ensure the climber is visible."
            )

        # Calculate metrics
        metrics = calculate_all_metrics(
            pose_keypoints_per_frame=[pf.keypoints for pf in pose_frames],
            pose_timestamps=[pf.timestamp for pf in pose_frames],
        )
        job.progress = 70

        metrics_dict = metrics.to_dict()
        job.metrics = metrics_dict

        # Save pose data to JSON for frontend overlay rendering
        pose_data_path = OUTPUT_DIR / f"{job_id}_poses.json.gz"
        pose_data = {
            "fps": video_info["fps"],
            "width": video_info["width"],
            "height": video_info["height"],
            "frames": [pf.to_dict() for pf in pose_frames],
        }
        with gzip.open(pose_data_path, "wt", encoding="utf-8") as f:
            json.dump(pose_data, f)
        job.progress = 75

        # Generate annotated video (for download)
        output_path = OUTPUT_DIR / f"{job_id}_annotated.mp4"
        await asyncio.to_thread(
            annotate_video, video_path, str(output_path), pose_frames, metrics_dict
        )
        job.progress = 80

        # Generate clean video (for client-side overlay viewing)
        clean_output_path = OUTPUT_DIR / f"{job_id}_clean.mp4"
        await asyncio.to_thread(create_clean_video, video_path, str(clean_output_path))
        job.progress = 85

        # Generate coach feedback
        feedback = await asyncio.to_thread(generate_coach_feedback, metrics_dict)
        job.feedback = feedback
        job.progress = 100

        job.status = "completed"

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        print(f"Job {job_id} failed: {e}")


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of an analysis job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return job.model_dump()


@app.get("/job/{job_id}/result")
async def get_job_result(job_id: str):
    """Get the complete result of a finished job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "completed":
        raise HTTPException(400, f"Job not completed. Status: {job.status}")

    return AnalysisResult(
        job_id=job_id,
        status="completed",
        metrics=job.metrics,
        formatted_metrics=format_metrics_for_display(job.metrics),
        feedback=job.feedback,
        video_url=f"/video/{job_id}",
        clean_video_url=f"/video/{job_id}/clean",
        duration=job.metrics.get("climb_duration", 0),
    )


@app.get("/job/{job_id}/pose-data")
async def get_pose_data(job_id: str):
    """Get per-frame pose data for overlay rendering."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "completed":
        raise HTTPException(400, f"Job not completed. Status: {job.status}")

    pose_data_path = OUTPUT_DIR / f"{job_id}_poses.json.gz"
    if not pose_data_path.exists():
        raise HTTPException(404, "Pose data not found")

    with gzip.open(pose_data_path, "rt", encoding="utf-8") as f:
        pose_data = json.load(f)

    return JSONResponse(content=pose_data)


def get_file_range_response(
    file_path: Path, request: Request, media_type: str
) -> Response:
    """Serve file with HTTP Range support for video streaming."""
    if not file_path.exists():
        raise HTTPException(404, "Video not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # Parse range header (e.g., "bytes=0-1023")
        try:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            end = min(end, file_size - 1)
        except (ValueError, IndexError):
            raise HTTPException(400, "Invalid Range header")

        content_length = end - start + 1

        def read_file_range():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": media_type,
        }
        return StreamingResponse(
            read_file_range(),
            status_code=206,
            headers=headers,
            media_type=media_type,
        )
    else:
        # No range requested - serve entire file
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": media_type,
        }
        return FileResponse(
            file_path,
            media_type=media_type,
            headers=headers,
        )


@app.get("/video/{job_id}")
async def get_annotated_video(job_id: str, request: Request):
    """Stream the annotated video with Range header support."""
    video_path = OUTPUT_DIR / f"{job_id}_annotated.mp4"
    return get_file_range_response(video_path, request, "video/mp4")


@app.get("/video/{job_id}/clean")
async def get_clean_video(job_id: str, request: Request):
    """Stream the clean video (no overlays) with Range header support."""
    video_path = OUTPUT_DIR / f"{job_id}_clean.mp4"
    return get_file_range_response(video_path, request, "video/mp4")


@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files."""
    if job_id in jobs:
        del jobs[job_id]

    # Clean up files
    for pattern in [f"{job_id}*"]:
        for f in UPLOAD_DIR.glob(pattern):
            f.unlink(missing_ok=True)
        for f in OUTPUT_DIR.glob(pattern):
            f.unlink(missing_ok=True)

    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
