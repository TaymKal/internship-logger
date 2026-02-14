import os
import sys
from pathlib import Path
from typing import Optional


from app.core.config import WHISPER_MODEL_NAME


class WhisperError(Exception):
    """Raised when Whisper transcription fails."""


def transcribe_audio_file(audio_path: Path) -> str:
    """
    Transcribe the given audio file using Whisper.

    Uses the Python API directly instead of CLI to avoid PATH issues.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise WhisperError(f"Audio file not found: {audio_path}")

    try:
        import whisper
    except ImportError as exc:
        raise WhisperError(
            "Whisper library not found. Install with: pip install openai-whisper"
        ) from exc

    try:
        # Load the model
        model = whisper.load_model(WHISPER_MODEL_NAME)
        
        # Transcribe the audio
        result = model.transcribe(
            str(audio_path),
            # language="en", # Auto-detect language
            fp16=False,  # Disable FP16 for CPU compatibility
        )
        
        text = result.get("text", "").strip()
        
        if not text:
            raise WhisperError("Whisper returned empty transcript.")
        
        return text
        
    except Exception as exc:
        if isinstance(exc, WhisperError):
            raise
        raise WhisperError(f"Whisper transcription failed: {exc}") from exc

