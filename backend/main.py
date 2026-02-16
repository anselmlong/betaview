"""
BetaView API
FastAPI backend for climbing video analysis.
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from processor import process_video_file
from heuristics import calculate_all_metrics
from visualizer import annotate_video, VisualizationConfig
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

app = FastAPI(
    title="BetaView API",
    description="Climbing video analysis for technique improvement",
    version="0.1.0"
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
    duration: float


@app.get("/")
async def root():
    return {"status": "ok", "service": "betaview-api", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
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
            raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB")
        
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
        created_at=datetime.utcnow().isoformat()
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
            raise ValueError("No poses detected in video. Ensure the climber is visible.")
        
        # Calculate metrics
        metrics = calculate_all_metrics(
            hip_trajectory=trajectories["hip_trajectory"],
            timestamps=trajectories["timestamps"],
            ankle_trajectories=trajectories["ankle_trajectories"],
            shoulder_positions=trajectories["shoulder_trajectory"]
        )
        job.progress = 70
        
        metrics_dict = metrics.to_dict()
        job.metrics = metrics_dict
        
        # Generate annotated video
        output_path = OUTPUT_DIR / f"{job_id}_annotated.mp4"
        await asyncio.to_thread(
            annotate_video,
            video_path,
            str(output_path),
            pose_frames,
            metrics_dict
        )
        job.progress = 85
        
        # Generate coach feedback
        feedback = await asyncio.to_thread(
            generate_coach_feedback, metrics_dict
        )
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
    
    return job.dict()


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
        duration=job.metrics.get("climb_duration", 0)
    )


@app.get("/video/{job_id}")
async def get_annotated_video(job_id: str):
    """Download the annotated video."""
    video_path = OUTPUT_DIR / f"{job_id}_annotated.mp4"
    
    if not video_path.exists():
        raise HTTPException(404, "Video not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"betaview_{job_id}.mp4"
    )


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


# Cleanup old files on startup
@app.on_event("startup")
async def cleanup_old_files():
    """Remove files older than CLEANUP_AFTER_HOURS."""
    cutoff = datetime.utcnow() - timedelta(hours=CLEANUP_AFTER_HOURS)
    
    for directory in [UPLOAD_DIR, OUTPUT_DIR]:
        for f in directory.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink(missing_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
