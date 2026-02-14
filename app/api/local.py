import base64
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core import database
from app.schemas.api_models import (
    SubmitRequest,
    SubmitResponse,
    JobStatusResponse,
    AudioClip,
)
from app.services.notion import create_notion_page, NotionError
from app.services.ollama import summarize_transcript, OllamaError
from app.services.whisper import transcribe_audio_file, WhisperError

router = APIRouter()


# ── Processing Logic ─────────────────────────────────────────────────────

def process_job_background(job_id: str, clips: list[AudioClip]):
    """Run the entire pipeline (transcribe -> summarize -> Notion)."""
    temp_files = []
    try:
        # 1. Transcribe
        transcripts = []
        for i, clip in enumerate(clips):
            raw = base64.b64decode(clip.audio_b64)
            fd, temp_path = tempfile.mkstemp(suffix=clip.suffix)
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
            temp_file = Path(temp_path)
            temp_files.append(temp_file)

            transcript = transcribe_audio_file(temp_file)
            transcripts.append(transcript)

        combined_transcript = " ".join(transcripts)

        # 2. Summarize
        title, body = summarize_transcript(combined_transcript)
        body += f"\n\n## Original Transcript\n\n{combined_transcript}"

        # 3. Notion Sync
        _, page_url = create_notion_page(title, body)
        database.complete_job(job_id, page_url)

    except (WhisperError, OllamaError, NotionError) as exc:
        database.fail_job(job_id, str(exc))
    except Exception as exc:
        database.fail_job(job_id, f"Unexpected error: {exc}")
    finally:
        for f in temp_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/submit", response_model=SubmitResponse)
async def submit_audio(req: SubmitRequest, background_tasks: BackgroundTasks):
    """Accept audio, queue it, and trigger background processing."""
    if not req.clips:
        raise HTTPException(status_code=400, detail="No clips provided")
    
    # Create database entry (status=pending)
    clips_data = [{"audio_b64": c.audio_b64, "suffix": c.suffix} for c in req.clips]
    job_id = database.create_job(clips_data)

    # Start processing in the background
    background_tasks.add_task(process_job_background, job_id, req.clips)

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
