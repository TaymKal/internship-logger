from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import database
from app.api import cloud

ROOT_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Internship Logger – Cloud")

app.include_router(cloud.router, prefix="/api")

@app.on_event("startup")
def on_startup():
    database.init_db()

@app.get("/")
async def root():
    return FileResponse(ROOT_DIR / "static" / "index.html")

app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
