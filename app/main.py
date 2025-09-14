from fastapi import FastAPI



# models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="R2D2 API", version="0.0.2")

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI + uv!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
