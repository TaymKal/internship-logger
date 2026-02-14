import uvicorn
from app.core import config

if __name__ == "__main__":
    uvicorn.run("app.main_local:app", host="0.0.0.0", port=8000)
