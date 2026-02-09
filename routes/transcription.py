import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from rq import Queue
from nanoid import generate

from backend.redis_conn import redis
from backend.job_store import create_job, update_job, transcription_running, acquire_transcription
from backend.worker import run_transcription_job

router = APIRouter()
queue = Queue("transcription", connection=redis)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    job_id = generate()
    path = f"{UPLOAD_DIR}/{job_id}_{file.filename}"

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"path": path}

@router.post("/transcribe")
def start_transcription(payload: dict):
    if transcription_running():
        raise HTTPException(409, "Transcription already running")

    job_id = generate()

    job = {
        "id": job_id,
        "name": "Audio Transcription",
        "type": "transcription",
        "status": "queued",
        "created_at": __import__("time").time(),
        "started_at": None,
        "finished_at": None,
        "error": None,
        "data": None
    }

    create_job(job)
    acquire_transcription(job_id)

    queue.enqueue(run_transcription_job, job_id, payload["path"])

    return {"job_id": job_id}
