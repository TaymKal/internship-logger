from typing import Optional, Literal
from pydantic import BaseModel


class AudioClip(BaseModel):
    audio_b64: str
    suffix: str = ".webm"


class SubmitRequest(BaseModel):
    clips: list[AudioClip]


class SubmitResponse(BaseModel):
    job_id: str
    status: str = "pending"
    message: str = "Recording queued for processing"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    notion_url: Optional[str] = None
    error_message: Optional[str] = None


class WorkerCompleteRequest(BaseModel):
    title: str
    body: str


class WorkerFailRequest(BaseModel):
    error_message: str
