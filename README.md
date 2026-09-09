# NeetiNex

## AI-Powered Government Scheme Assistance Platform

NeetiNex is an academic major project designed to help citizens discover and understand Central Government and Rajasthan Government schemes using natural language.

The system will use verified official government information, Retrieval-Augmented Generation (RAG), hybrid retrieval, source references, and a separate rule-based eligibility engine.

---

## Project Goals

NeetiNex aims to help users:

* Discover relevant government schemes without knowing the exact scheme name.
* Ask questions about known schemes in natural language.
* Understand scheme benefits, eligibility, required documents, and application procedures.
* Check potential eligibility using structured scheme-specific rules.
* Receive answers grounded in verified official government sources.
* Upload government scheme documents and ask questions about them.
* Interact through text and voice.

The system will initially focus on:

1. Central Government schemes
2. Rajasthan Government schemes

---

## Core Principle

Accuracy and verification are more important than generating an answer.

If information cannot be verified from the available official knowledge base, the system should clearly state that instead of guessing.

AI-generated answers must not be presented as official government information unless supported by retrieved official sources.

---

# Planned Architecture

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

# Planned Technology Stack

## Frontend

* React
* Vite
* TypeScript
* Tailwind CSS

## Backend

* Python 3.11
* FastAPI
* Pydantic

## AI and RAG

* Sentence Transformers for embeddings
* Vector Search
* BM25 Keyword Search
* Hybrid Retrieval
* Reranking
* LLM-based Response Generation

## Data and Storage

* Structured scheme data: PostgreSQL or SQLite during early development
* Vector database: ChromaDB for the MVP
* Local document storage for uploaded files
* JSON-based eligibility rules during the MVP

The exact database and deployment choices may be finalized after the MVP data pipeline is working.

---

# Repository Structure

```text
NeetiNex/

NeetiNex/
│
├── frontend/
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
├── backend/
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
│   ├── raw/
│   ├── verified/
│   ├── processed/
│   ├── schemes/
│   └── eligibility_rules/
│
├── storage/
│   ├── vector_db/
│   ├── bm25_index/
│   └── uploads/
│
├── docs/
│   ├── architecture/
│   ├── data/
│   ├── api/
│   └── evaluation/
│
├── scripts/
├── notebooks/
│
├── .github/
│   └── workflows/
│
├── .gitignore
├── LICENSE
└── README.md
```

---

# Prerequisites

Before running the project, install:

* Python 3.11
* Node.js 18 or newer
* npm
* Git
* VS Code (Recommended)

Check installed versions:

```bash
python --version
node --version
npm --version
git --version
```

> **Note:** Python 3.11 is recommended for this project because AI, RAG, and machine learning libraries generally have stable compatibility with this version.

---

# Project Setup

## 1. Clone the Repository

```bash
git clone <repository-url>
```

Move into the project directory:

```bash
cd NeetiNex
```

---

# Backend Setup

## 1. Move to the Backend Directory

```bash
cd backend
```

## 2. Create a Python 3.11 Virtual Environment

On Windows:

```bash
py -3.11 -m venv venv
```

This creates a virtual environment using Python 3.11.

## 3. Activate the Virtual Environment

### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
venv\Scripts\activate
```

After activation, verify the Python version:

```bash
python --version
```

Expected output:

```text
Python 3.11.x
```

---

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## 5. Install Backend Dependencies

After creating the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

Example dependencies:

```text
fastapi
uvicorn
pydantic
sentence-transformers
chromadb
rank-bm25
python-multipart
pypdf
python-dotenv
```

---

# Run the Backend

Make sure the virtual environment is activated.

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The backend server will start locally.

Default API URL:

```text
http://127.0.0.1:8000
```

FastAPI interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

Open another terminal.

Move to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

---

# Run the Frontend

Start the Vite development server:

```bash
npm run dev
```

The terminal will display a local URL similar to:

```text
http://localhost:5173
```

Open this URL in your browser.

---

# Running the Complete Project

Two terminals are required during development.

## Terminal 1 — Backend

```bash
cd NeetiNex/backend
```

Activate the Python environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

---

## Terminal 2 — Frontend

```bash
cd NeetiNex/frontend
```

Run:

```bash
npm run dev
```

---

# Development Workflow

The recommended development order is:

```text
1. Initialize Backend
        ↓
2. Create Scheme Data Model
        ↓
3. Collect Official Scheme Data
        ↓
4. Verify and Store Sources
        ↓
5. Implement Basic Scheme Search
        ↓
6. Add Embeddings and Vector Search
        ↓
7. Implement BM25 Search
        ↓
8. Implement Hybrid Retrieval
        ↓
9. Add Reranking
        ↓
10. Implement RAG Response Generation
        ↓
11. Add Source References
        ↓
12. Implement Eligibility Engine
        ↓
13. Develop Frontend Dashboard
        ↓
14. Add Document RAG
        ↓
15. Add Voice Interaction
        ↓
16. Telephone Interface (Optional)
```

---

# Data Source Policy

Primary sources must include official government resources such as:

* Government ministry and department websites
* Official government portals
* Official scheme pages
* Government notifications
* Scheme guidelines
* Official government PDF documents

Every important scheme record should retain source metadata where available:

* Source URL
* Document name
* Relevant page or section
* Verification date
* Last checked date

---

# Eligibility Policy

Eligibility checking is separate from normal language generation whenever possible.

The LLM may help understand user input and explain results, but scheme eligibility conditions should be checked using structured rules derived from verified official criteria.

Possible results:

* Potentially eligible
* Not eligible based on available criteria
* More information needed
* Unable to verify

Final eligibility decisions remain with the competent government authority.

---

# Environment Variables

Sensitive configuration should not be stored directly in the source code.

Create a `.env` file inside the `backend` directory when required.

Example:

```text
DATABASE_URL=
LLM_API_KEY=
LLM_MODEL=
CHROMA_DB_PATH=
```

The `.env` file should not be committed to GitHub.

---

# Current Status

**Current Stage:** Project Foundation

The repository structure and documentation are being prepared first.

The next implementation tasks are:

1. Initialize the FastAPI backend.
2. Initialize the React frontend.
3. Define the official scheme data model.
4. Create the initial project API structure.
5. Begin collecting verified official scheme information.

---

# Academic Project

**Project:** NeetiNex — An AI-Powered Government Scheme Assistance Platform

Initial scope:

* Central Government schemes
* Rajasthan Government schemes
* Approximately 50–100 verified schemes
* Source-grounded RAG
* Eligibility checking
* Web dashboard
* Voice interaction
* Temporary document RAG
* Telephone interface if feasible

---

# Important Disclaimer

NeetiNex is an academic assistance platform.

The system provides information based on retrieved and verified sources available in its knowledge base. It does not make official government decisions.

Eligibility results are preliminary and based on available criteria.

Final eligibility and approval decisions remain with the relevant government authority.

---

# License

This project is currently developed as an academic major project.
