from fastapi import APIRouter
from backend.job_store import list_jobs, get_job

router = APIRouter()

@router.get("/jobs")
def jobs():
    return list_jobs()

@router.get("/jobs/{job_id}")
def job(job_id: str):
    return get_job(job_id)
