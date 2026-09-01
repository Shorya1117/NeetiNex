# NeetiNex

## AI-Powered Government Scheme Assistance Platform

NeetiNex is an academic major project designed to help citizens discover and understand Central Government and Rajasthan Government schemes using natural language.

The system will use verified official government information, Retrieval-Augmented Generation (RAG), hybrid retrieval, source references, and a separate rule-based eligibility engine.

---

## Project Goals

NeetiNex aims to help users:

- Discover relevant government schemes without knowing the exact scheme name.
- Ask questions about known schemes in natural language.
- Understand scheme benefits, eligibility, required documents, and application procedures.
- Check potential eligibility using structured scheme-specific rules.
- Receive answers grounded in verified official government sources.
- Upload government scheme documents and ask questions about them.
- Interact through text and voice.

The system will initially focus on:

1. Central Government schemes
2. Rajasthan Government schemes

---

## Core Principle

Accuracy and verification are more important than generating an answer.

If information cannot be verified from the available official knowledge base, the system should clearly state that instead of guessing.

AI-generated answers must not be presented as official government information unless supported by retrieved official sources.

---

## Planned Architecture

```text
User Interfaces
│
├── Web Dashboard
├── Voice Interaction
├── Document Upload
└── Telephone Interface (Advanced / Optional)
        │
        ▼
Backend API
        │
        ├── Conversation Management
        ├── Scheme Search
        ├── RAG Pipeline
        ├── Eligibility Engine
        ├── Document RAG
        └── Response Generation
                │
                ▼
Knowledge Layer
        │
        ├── Verified Scheme Data
        ├── Official Documents
        ├── Vector Index
        ├── BM25 Index
        └── Eligibility Rules
```

---

## Planned Technology Stack

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI
- Pydantic

### AI and RAG

- Sentence Transformers for embeddings
- Vector search
- BM25 keyword search
- Hybrid retrieval
- Reranking
- LLM-based response generation

### Data and Storage

- Structured scheme data: PostgreSQL or SQLite during early development
- Vector database: ChromaDB for the MVP
- Local document storage for uploaded files
- JSON-based eligibility rules during the MVP

The exact database and deployment choices may be finalized after the MVP data pipeline is working.

---

# Repository Structure

```text
NeetiNex/
│
├── frontend/                  # Web dashboard
│   ├── public/
│   └── src/
│       ├── components/
│       ├── features/
│       │   ├── chat/
│       │   ├── schemes/
│       │   ├── documents/
│       │   └── voice/
│       ├── hooks/
│       ├── services/
│       └── types/
│
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   │
│   │   ├── rag/
│   │   │   ├── indexing/
│   │   │   └── retrieval/
│   │   │
│   │   ├── eligibility/
│   │   ├── conversation/
│   │   ├── document_rag/
│   │   └── voice/
│   │
│   └── tests/
│
├── data/
│   ├── raw/                   # Collected source data
│   ├── verified/              # Verified source information
│   ├── processed/             # Cleaned/chunked data
│   ├── schemes/               # Structured scheme records
│   └── eligibility_rules/     # Rule definitions
│
├── storage/
│   ├── vector_db/
│   ├── bm25_index/
│   └── uploads/
│
├── scripts/                   # Data processing and utility scripts
├── notebooks/                 # Experiments and analysis
│
├── docs/
│   ├── architecture/
│   ├── data/
│   ├── api/
│   └── evaluation/
│
├── .github/
│   └── workflows/
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Data Source Policy

Primary sources must include official government resources such as:

- Government ministry and department websites
- Official government portals
- Official scheme pages
- Government notifications
- Scheme guidelines
- Official government PDF documents

Every important scheme record should retain source metadata where available:

- Source URL
- Document name
- Relevant page or section
- Verification date
- Last checked date

---

## Eligibility Policy

Eligibility checking is separate from normal language generation whenever possible.

The LLM may help understand user input and explain results, but scheme eligibility conditions should be checked using structured rules derived from verified official criteria.

Possible results:

- Potentially eligible
- Not eligible based on available criteria
- More information needed
- Unable to verify

Final eligibility decisions remain with the competent government authority.

---

## Current Status

**Current stage:** Project foundation

The repository structure and documentation are being prepared first.

The next implementation task is to initialize the backend and frontend and define the official scheme data model before collecting schemes.

---

## Academic Project

**Project:** NeetiNex — An AI-Powered Government Scheme Assistance Platform

Initial scope:

- Central Government schemes
- Rajasthan Government schemes
- Approximately 50–100 verified schemes
- Source-grounded RAG
- Eligibility checking
- Web dashboard
- Voice interaction
- Temporary document RAG
- Telephone interface if feasible

---

## License

This project is currently developed as an academic major project.
