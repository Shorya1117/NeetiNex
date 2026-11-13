import re
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.rag.rag_chain import NeetiNexRAG
from backend.rag.pdf_rag import TemporaryPDFRAG
from backend.api.routers.eligibility import router as eligibility_router
from backend.services.eligibility.chat_eligibility_service import handle_eligibility_chat
from backend.services.eligibility.rag_bridge import build_llm_fn, build_semantic_fn

import logging
import os
import uuid
from typing import List, Optional
from pathlib import Path


# ======================================
# FastAPI Application
# ======================================

app = FastAPI(
    title="NeetiNex API",
    description="AI-powered Government Scheme Assistance Platform",
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
# Eligibility Engine (rule-based, separate from RAG)
# ======================================

app.include_router(eligibility_router)


# ======================================
# Request Models
# ======================================

class ChatRequest(BaseModel):
    message: str
    profile: Optional[dict] = None   # details told earlier in this chat (session only)
    topics: Optional[List[str]] = None   # topic of the earlier eligibility search


class PDFQuestionRequest(BaseModel):
    document_id: str
    question: str


class PDFDeleteRequest(BaseModel):
    document_id: str


# ======================================
# Initialize RAG Systems
# ======================================

scheme_rag = None
pdf_rag = None


@app.on_event("startup")
def startup_event():

    global scheme_rag
    global pdf_rag

    print("======================================")
    print("Starting NeetiNex API")
    print("======================================")

    print("Loading Scheme RAG...")
    scheme_rag = NeetiNexRAG()

    print("Loading PDF RAG...")
    pdf_rag = TemporaryPDFRAG()

    print("======================================")
    print("NeetiNex RAG systems loaded successfully.")
    print("API is ready.")
    print("======================================")


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
        "scheme_rag_loaded": scheme_rag is not None,
        "pdf_rag_loaded": pdf_rag is not None
    }


# ======================================
# Chat Endpoint
# ======================================

@app.post("/chat")
def chat(request: ChatRequest):

    if scheme_rag is None:

        return {
            "success": False,
            "error": "Scheme RAG system is not initialized."
        }

    if re.fullmatch(r"\s*(hi+|hello+|hey+|namaste|namaskar|hii+|good (morning|evening|afternoon)|नमस्ते)\W*",
                    request.message, re.I):
        return {
            "success": True,
            "answer": "Namaste! Main NeetiNex hu. Kisi Rajasthan scheme ke baare mein poochiye, "
                      "ya apni details batayiye (jaise: class, income, category, kaam) aur main "
                      "aapke liye eligible schemes ki table bana dunga.",
            "sources": []
        }

    try:

        # "I am in class 8, income 1 lakh, which scholarships?" -> comparison
        # table from the rule engine. Other questions continue to normal RAG.
        try:
            eligibility_response = handle_eligibility_chat(
                request.message,
                request.profile,
                llm_fn=build_llm_fn(scheme_rag),
                semantic_fn=build_semantic_fn(scheme_rag),
                previous_topics=request.topics
            )
        except Exception:
            logging.getLogger(__name__).exception("Eligibility chat failed")
            eligibility_response = None

        if eligibility_response:
            return eligibility_response

        result = scheme_rag.ask(
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


# ======================================
# PDF Upload Endpoint
# ======================================

@app.post("/pdf/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    if pdf_rag is None:

        raise HTTPException(
            status_code=503,
            detail="PDF RAG system is not initialized."
        )

    # ----------------------------------
    # Check file type
    # ----------------------------------

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # ----------------------------------
    # Temporary upload directory
    # ----------------------------------

    temp_dir = "data/temp_pdf/uploads"

    os.makedirs(
        temp_dir,
        exist_ok=True
    )

    # basename + unique prefix: no path tricks, no clash between two uploads
    safe_name = os.path.basename(file.filename.replace("\\", "/"))
    temp_path = os.path.join(
        temp_dir,
        f"{uuid.uuid4().hex[:8]}_{safe_name}"
    )

    try:

        # ----------------------------------
        # Save uploaded PDF
        # ----------------------------------

        with open(
            temp_path,
            "wb"
        ) as buffer:

            content = await file.read()

            buffer.write(content)

        print(
            f"Processing uploaded PDF: {file.filename}"
        )

        # ----------------------------------
        # Process PDF
        # ----------------------------------

        result = pdf_rag.process_pdf(
            temp_path
        )

        # ----------------------------------
        # Return document information
        # ----------------------------------

        return {
            "success": True,
            "filename": file.filename,
            "document_id": result["document_id"]
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing error: {str(e)}"
        )


# ======================================
# PDF Question Endpoint
# ======================================

@app.post("/pdf/chat")
async def pdf_chat(
    request: PDFQuestionRequest
):

    if pdf_rag is None:

        raise HTTPException(
            status_code=503,
            detail="PDF RAG system is not initialized."
        )

    try:

        result = pdf_rag.ask(
            document_id=request.document_id,
            question=request.question
        )

        return {
            "success": True,
            "answer": result["answer"],
            "sources": result["sources"]
        }

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ======================================
# PDF Delete Endpoint
# ======================================

@app.delete("/pdf/delete")
async def delete_pdf(
    request: PDFDeleteRequest
):

    if pdf_rag is None:

        raise HTTPException(
            status_code=503,
            detail="PDF RAG system is not initialized."
        )

    try:

        return pdf_rag.delete_document(
            request.document_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )