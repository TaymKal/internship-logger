import base64
import os
import sys
import tempfile
import time
from pathlib import Path

import requests

# Ensure we can import from app
sys.path.append(str(Path(__file__).parent))

from app.core.config import CLOUD_SERVER_URL, WORKER_SECRET, POLL_INTERVAL
from app.services.whisper import transcribe_audio_file, WhisperError
from app.services.ollama import summarize_transcript, OllamaError


def headers():
    return {"Authorization": f"Bearer {WORKER_SECRET}"}


def poll_for_job() -> dict | None:
    """Ask the cloud server for the next pending job."""
    try:
        resp = requests.get(
            f"{CLOUD_SERVER_URL}/api/queue/next",
            headers=headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  [!] Server returned {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        return data.get("job")
    except requests.RequestException as exc:
        print(f"  [!] Could not reach cloud server: {exc}")
        return None


def process_job(job: dict):
    """Transcribe + summarize locally, then submit results to the cloud."""
    job_id = job["id"]
    clips = job["clips"]
    print(f"  → Processing job {job_id} with {len(clips)} clip(s)...")

    temp_files: list[Path] = []
    try:
        # ── Transcribe each clip ─────────────────────────────────────
        transcripts = []
        for i, clip in enumerate(clips):
            print(f"    Transcribing clip {i + 1}/{len(clips)}...")
            raw = base64.b64decode(clip["audio_b64"])
            suffix = clip.get("suffix", ".webm")
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
            temp_file = Path(temp_path)
            temp_files.append(temp_file)

            transcript = transcribe_audio_file(temp_file)
            transcripts.append(transcript)

        combined_transcript = " ".join(transcripts)
        print(f"    Transcript: {combined_transcript[:100]}...")

        # ── Summarize ────────────────────────────────────────────────
        print("    Summarizing with Ollama...")
        title, body = summarize_transcript(combined_transcript)
        body += f"\n\n## Original Transcript\n\n{combined_transcript}"

        # ── Submit results to cloud ──────────────────────────────────
        print(f"    Sending results to cloud server...")
        resp = requests.post(
            f"{CLOUD_SERVER_URL}/api/queue/{job_id}/complete",
            headers=headers(),
            json={"title": title, "body": body},
            timeout=30,
        )
        if resp.status_code == 200:
            result = resp.json()
            print(f"  ✓ Job {job_id} done! Notion URL: {result.get('notion_url', 'N/A')}")
        else:
            print(f"  ✗ Cloud server rejected results: {resp.status_code} {resp.text[:200]}")

    except (WhisperError, OllamaError) as exc:
        print(f"  ✗ AI processing failed: {exc}")
        try:
            requests.post(
                f"{CLOUD_SERVER_URL}/api/queue/{job_id}/fail",
                headers=headers(),
                json={"error_message": str(exc)},
                timeout=15,
            )
        except Exception:
            pass

    except Exception as exc:
        print(f"  ✗ Unexpected error: {exc}")
        try:
            requests.post(
                f"{CLOUD_SERVER_URL}/api/queue/{job_id}/fail",
                headers=headers(),
                json={"error_message": f"Unexpected: {exc}"},
                timeout=15,
            )
        except Exception:
            pass

    finally:
        for f in temp_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def main():
    print("=" * 50)
    print("  Internship Logger – Local AI Worker")
    print("=" * 50)
    print(f"  Cloud server: {CLOUD_SERVER_URL}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print()

    if not WORKER_SECRET:
        print("ERROR: WORKER_SECRET is not set in .env")
        sys.exit(1)

    while True:
        try:
            job = poll_for_job()
            if job:
                process_job(job)
            else:
                print(f"  No pending jobs. Waiting {POLL_INTERVAL}s...")
        except KeyboardInterrupt:
            print("\n  Worker stopped.")
            break
        except Exception as exc:
            print(f"  [!] Loop error: {exc}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
