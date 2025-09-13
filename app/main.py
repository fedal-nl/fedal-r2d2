from fastapi import FastAPI

app = FastAPI(
    title="Fedal R2D2",
    description="A FastAPI that contains services like Sending an email.",
    version="1.0.0"
)


@app.get("/")
async def read_root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to Fedal R2D2 - FastAPI Email Service"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}