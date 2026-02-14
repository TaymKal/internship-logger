"""
SQLite-backed job queue logic.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[2] / "queue.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TEXT NOT NULL,
            completed_at TEXT,
            notion_url  TEXT,
            error_message TEXT
        );
        CREATE TABLE IF NOT EXISTS job_clips (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id   TEXT NOT NULL,
            audio_b64 TEXT NOT NULL,
            suffix    TEXT NOT NULL DEFAULT '.webm',
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
    """)
    conn.commit()
    conn.close()


# ── Write operations ─────────────────────────────────────────────────────

def create_job(clips: list[dict]) -> str:
    """
    Insert a new job with its audio clips.
    clips: [{"audio_b64": "...", "suffix": ".webm"}, ...]
    Returns the job id.
    """
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "INSERT INTO jobs (id, status, created_at) VALUES (?, 'pending', ?)",
        (job_id, now),
    )
    for clip in clips:
        conn.execute(
            "INSERT INTO job_clips (job_id, audio_b64, suffix) VALUES (?, ?, ?)",
            (job_id, clip["audio_b64"], clip.get("suffix", ".webm")),
        )
    conn.commit()
    conn.close()
    return job_id


def claim_next_job() -> Optional[dict]:
    """
    Atomically claim the oldest pending job (set status='processing').
    Returns {"id", "clips": [{"audio_b64", "suffix"}, ...]} or None.
    """
    conn = _connect()
    row = conn.execute(
        "SELECT id FROM jobs WHERE status='pending' ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    if not row:
        conn.close()
        return None

    job_id = row["id"]
    conn.execute(
        "UPDATE jobs SET status='processing' WHERE id=?", (job_id,)
    )
    conn.commit()

    clips = conn.execute(
        "SELECT audio_b64, suffix FROM job_clips WHERE job_id=?", (job_id,)
    ).fetchall()
    conn.close()

    return {
        "id": job_id,
        "clips": [{"audio_b64": c["audio_b64"], "suffix": c["suffix"]} for c in clips],
    }


def complete_job(job_id: str, notion_url: str):
    """Mark a job as done with its Notion URL."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "UPDATE jobs SET status='done', completed_at=?, notion_url=? WHERE id=?",
        (now, notion_url, job_id),
    )
    conn.commit()
    conn.close()


def fail_job(job_id: str, error_message: str):
    """Mark a job as failed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        "UPDATE jobs SET status='error', completed_at=?, error_message=? WHERE id=?",
        (now, error_message, job_id),
    )
    conn.commit()
    conn.close()


# ── Read operations ──────────────────────────────────────────────────────

def get_job_status(job_id: str) -> Optional[dict]:
    """Return job status info or None if not found."""
    conn = _connect()
    row = conn.execute(
        "SELECT id, status, created_at, completed_at, notion_url, error_message "
        "FROM jobs WHERE id=?",
        (job_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)
