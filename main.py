# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from configs.logs import setup_logging
from routers import email, form


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="R2D2 API", version="0.0.2")

# Include CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(email.router, prefix="/email", tags=["Email"])
app.include_router(form.router, prefix="/forms", tags=["Forms"])

@app.get("/")
def read_root():
    return {"message": "Hello R2D2 services"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
