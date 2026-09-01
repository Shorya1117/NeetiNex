from fastapi import FastAPI

app = FastAPI(
    title="NeetiNex API",
    description="AI-Powered Government Scheme Assistance Platform",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "project": "NeetiNex",
        "message": "API is running",
        "status": "healthy"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }