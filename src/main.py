# app/main.py
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import router as api_v1_router
from src.configs.logs import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="R2D2 API", version="0.0.4")


# Include CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/")
def read_root():
    return {"message": "Hello R2D2 services"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
