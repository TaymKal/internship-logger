import uvicorn
from app.core import config

if __name__ == "__main__":
    # Use config.PORT which defaults to 8000
    uvicorn.run("app.main_cloud:app", host="0.0.0.0", port=config.PORT)
