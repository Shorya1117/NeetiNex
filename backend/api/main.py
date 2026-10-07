from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag.rag_chain import NeetiNexRAG


# ======================================
# FastAPI Application
# ======================================

app = FastAPI(
    title="NeetiNex API",
    description="AI-powered Government Scheme Assistance API",
    version="1.0.0"
)


# ======================================
# CORS
# ======================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================
# Request Model
# ======================================

class ChatRequest(BaseModel):

    message: str


# ======================================
# Initialize RAG
# ======================================

rag = None


@app.on_event("startup")
def startup_event():

    global rag

    print("======================================")
    print("Starting NeetiNex API")
    print("======================================")

    rag = NeetiNexRAG()

    print("NeetiNex RAG loaded successfully.")
    print("API is ready.")


# ======================================
# Root Endpoint
# ======================================

@app.get("/")
def root():

    return {
        "project": "NeetiNex",
        "status": "running",
        "message": "NeetiNex API is running"
    }


# ======================================
# Health Check
# ======================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "rag_loaded": rag is not None
    }


# ======================================
# Chat Endpoint
# ======================================

@app.post("/chat")
def chat(request: ChatRequest):

    if rag is None:

        return {
            "success": False,
            "error": "RAG system is not initialized."
        }

    try:

        result = rag.ask(
            request.message
        )

        sources = []

        for source in result.get("sources", []):

            sources.append({
                "url": source
            })

        return {
            "success": True,
            "question": request.message,
            "answer": result["answer"],
            "sources": sources
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }