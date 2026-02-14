# Internship Logger

Record voice notes about your internship and automatically transcribe, summarize, and save them to Notion.

## Architecture

The app has two deployment modes:

### Cloud Mode (recommended)

```
Phone → Cloud Server (Railway) → Job Queue → Local AI Worker (your PC) → Notion
```

| Component | Runs via | Description |
|---|---|---|
| Cloud server | `run_cloud.py` | Hosted on Railway. Receives audio, queues jobs. |
| Local AI worker | `run_worker.py` | Runs on your PC. Processes queue with Whisper + Ollama. |
| Job queue | `app/core/database.py` | SQLite database (on Railway). |

### Local Mode (development)

```
Browser → Local Server (localhost) → Whisper + Ollama
```

| Component | Runs via | Description |
|---|---|---|
| Local server | `run_local.py` | Runs everything in one process on your machine. |

## Project Structure

```
internship-logger/
├── app/
│   ├── core/                # Config & Database
│   ├── schemas/             # Pydantic models
│   ├── services/            # Notion, Ollama, Whisper clients
│   ├── api/                 # API Routes
│   ├── main_cloud.py        # Cloud app entry
│   ├── main_local.py        # Local app entry
│   └── worker.py            # Worker logic
├── static/                  # Frontend assets
├── run_cloud.py             # Script to run cloud server
├── run_local.py             # Script to run local server
├── run_worker.py            # Script to run worker
└── ...
```

## Prerequisites

For the **Local AI Worker** (and Local Mode) to function, your PC must have:

1.  **Ollama**: [Download and install Ollama](https://ollama.com/).
    -   Pull the Llama 3.2 model: `ollama run llama3.2`
2.  **FFmpeg**: Required for audio processing.
    -   **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your System PATH.
    -   **Mac**: `brew install ffmpeg`
    -   **Linux**: `sudo apt install ffmpeg`
3.  **Python 3.10+**: Ensure Python is installed and added to PATH.

## Setup & Running

### 1. Install dependencies

```bash
# For local worker / local mode
pip install -r requirements-worker.txt

# Cloud server dependencies (handled by Railway)
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values.

### 3. Run

**Cloud mode:**
```bash
# 1. Deploy to Railway (uses run_cloud.py automatically)
# 2. Run the worker locally:
python run_worker.py
```

**Local mode:**
```bash
python run_local.py
```
