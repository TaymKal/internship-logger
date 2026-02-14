from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Depends

from app.core import database
from app.core.config import WORKER_SECRET
from app.schemas.api_models import (
    SubmitRequest,
    SubmitResponse,
    JobStatusResponse,
    WorkerCompleteRequest,
    WorkerFailRequest,
)
from app.services.notion import create_notion_page, NotionError

router = APIRouter()


# ── Auth helper ──────────────────────────────────────────────────────────

def verify_worker(authorization: Optional[str] = Header(None)):
    if not WORKER_SECRET:
        raise HTTPException(500, "WORKER_SECRET not configured on server")
    if authorization != f"Bearer {WORKER_SECRET}":
        raise HTTPException(401, "Invalid worker secret")


# ── Frontend Endpoints ───────────────────────────────────────────────────

@router.post("/submit", response_model=SubmitResponse)
async def submit_audio(req: SubmitRequest):
    """Accept audio clips from the frontend and queue them."""
    if not req.clips:
        raise HTTPException(status_code=400, detail="No clips provided")
    clips_data = [{"audio_b64": c.audio_b64, "suffix": c.suffix} for c in req.clips]
    job_id = database.create_job(clips_data)
    return SubmitResponse(job_id=job_id)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def job_status(job_id: str):
    """Frontend polls this to check processing status."""
    info = database.get_job_status(job_id)
    if not info:
        raise HTTPException(404, "Job not found")
    return JobStatusResponse(
        job_id=info["id"],
        status=info["status"],
        notion_url=info.get("notion_url"),
        error_message=info.get("error_message"),
    )


# ── Worker Endpoints (protected by secret) ───────────────────────────────

@router.get("/queue/next")
async def queue_next(authorization: Optional[str] = Header(None)):
    """Worker calls this to claim the next pending job."""
    verify_worker(authorization)
    job = database.claim_next_job()
    if not job:
        return {"job": None}
    return {"job": job}


@router.post("/queue/{job_id}/complete")
async def queue_complete(
    job_id: str,
    req: WorkerCompleteRequest,
    authorization: Optional[str] = Header(None),
):
    """Worker submits results; cloud server sends to Notion."""
    verify_worker(authorization)

    info = database.get_job_status(job_id)
    if not info:
        raise HTTPException(404, "Job not found")

    # Send to Notion from the cloud server
    try:
        _, page_url = create_notion_page(req.title, req.body)
    except NotionError as exc:
        database.fail_job(job_id, f"Notion error: {exc}")
        raise HTTPException(502, f"Notion error: {exc}")
    except Exception as exc:
        database.fail_job(job_id, f"Unexpected error: {exc}")
        raise HTTPException(500, f"Unexpected error: {exc}")

    database.complete_job(job_id, page_url)
    return {"status": "done", "notion_url": page_url}


@router.post("/queue/{job_id}/fail")
async def queue_fail(
    job_id: str,
    req: WorkerFailRequest,
    authorization: Optional[str] = Header(None),
):
    """Worker reports a processing failure."""
    verify_worker(authorization)
    database.fail_job(job_id, req.error_message)
    return {"status": "error"}
