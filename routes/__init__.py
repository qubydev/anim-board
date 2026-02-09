from fastapi import APIRouter
from .transcription import router as transcription
from .jobs import router as jobs

router = APIRouter()
router.include_router(transcription)
router.include_router(jobs)
