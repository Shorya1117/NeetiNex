# NeetiNex

## An AI-Powered Government Scheme Assistance Platform

NeetiNex is a major project focused on helping citizens discover and understand Central Government and Rajasthan Government schemes through natural-language interaction.

The platform is designed around two primary capabilities:

1. **Scheme Discovery** — helping users find schemes based on their personal requirements and eligibility conditions.
2. **Scheme Q&A** — allowing users to ask natural-language questions about government schemes and receive answers grounded in verified government information.

The project also includes planned capabilities for document/PDF understanding, temporary document RAG, and voice interaction.

---

# Project Overview

NeetiNex follows an accuracy-first architecture. Official Government websites, department portals, notifications, guidelines, and government documents are treated as the primary sources of scheme information.

The current development pipeline is:

```text
Official Government Sources
          ↓
       Crawling
          ↓
      Extraction
          ↓
      Validation
          ↓
       Cleaning
          ↓
    Deduplication
          ↓
 Section-Aware Chunking
          ↓
      Embeddings
          ↓
     Vector Store
          ↓
     RAG Retrieval
          ↓
    LLM Response
          ↓
 Official Source Reference
```

Alongside the RAG pipeline, Scheme Discovery is planned as a separate eligibility path:

```text
User Information
      ↓
Structured User Profile
      ↓
Rule-Based Eligibility Engine
      ↓
Verified Eligibility Rules
      ↓
Matching Schemes
      ↓
RAG / Official Source
      ↓
Explanation
```

> **Important:** Vector similarity or an LLM should not be treated as proof of eligibility. Eligibility decisions are intended to use verified structured rules wherever possible.

---

# Current Development Status

```text
Government Data Crawling       ✓ Completed
HTML Extraction                ✓ Completed
Data Validation                ✓ Completed
Text Cleaning                  ✓ Completed
Exact Deduplication            ✓ Completed
Section-Aware Chunking         ✓ Completed
Embedding Generation           ✓ Completed
Vector Store Integration       ✓ Completed
RAG Pipeline                   ✓ Completed
Frontend Integration           ✓ Completed
Scheme Q&A                     ✓ Working / Implemented

Scheme Discovery               → Under Development
Rule-Based Eligibility Engine  → Planned / Under Development
PDF Upload                     → Planned
Temporary Document RAG          → Planned
Hybrid Retrieval               → Future Enhancement
Reranking                      → Future Enhancement
Voice Interaction              → Future Phase
```

---

# Technology Stack

## Backend

| Technology | Purpose |
|---|---|
| Python 3.13.14 | Backend, data processing and AI development |
| FastAPI | Backend REST API |
| Uvicorn | Development ASGI server |
| Pydantic | API request/response validation |
| LangChain | Document processing and RAG pipeline |
| LangChain Text Splitters | Section-aware text chunking |
| BeautifulSoup / HTML processing | Government HTML extraction |
| JSON | Structured scheme data storage |

## AI / RAG

| Technology / Component | Purpose |
|---|---|
| Embedding Model | Converts scheme text into vector representations |
| Vector Store | Stores and retrieves embedded scheme chunks |
| LangChain | RAG orchestration and document handling |
| LLM | Generates grounded natural-language responses |
| Metadata | Supports scheme, department, section and source filtering |
| Source URLs | Supports official source references |

## Frontend

| Technology | Purpose |
|---|---|
| Node.js 20.20.0 | Frontend development environment |
| npm | Frontend package management |
| Frontend application | User interface for Scheme Q&A and future features |

## Development Tools

| Tool | Purpose |
|---|---|
| Git | Version control |
| GitHub | Remote repository and source-code management |
| Visual Studio Code | Development environment |
| Python Virtual Environment | Isolated Python dependencies |

---

# Project Directory

```text
NeetiNex/
│
├── backend/
│   │
│   ├── api/
│   │   └── main.py                  # FastAPI application
│   │
│   ├── rag/
│   │   └── rag_chain.py             # RAG pipeline / response generation
│   │
│   ├── app/
│   │   ├── api/                     # Application API components
│   │   ├── core/                    # Configuration and utilities
│   │   ├── db/                      # Database-related components
│   │   ├── eligibility/             # Eligibility-related logic
│   │   ├── models/                  # Data/application models
│   │   ├── rag/                     # RAG-related application components
│   │   ├── schemas/                 # Request/response schemas
│   │   └── services/                # Application services
│   │
│   ├── data/
│   │   ├── raw/
│   │   │   └── jansoochna/
│   │   │       └── eligibility/
│   │   │           └── html/        # Raw Jan Soochna HTML
│   │   │
│   │   └── processed/
│   │       └── jansoochna/
│   │           └── eligibility/
│   │               ├── extracted/   # Extracted JSON
│   │               ├── cleaned/     # Cleaned JSON
│   │               ├── deduplicated/# Duplicate-free JSON
│   │               ├── chunks/      # LangChain-generated chunks
│   │               └── quality_reports/
│   │
│   ├── ingestion/
│   │   ├── extraction/
│   │   │   └── extract_html.py
│   │   ├── validation/
│   │   │   └── validate_eligibility.py
│   │   ├── cleaning/
│   │   │   └── clean_text.py
│   │   ├── deduplication/
│   │   │   └── deduplicate.py
│   │   └── chunking/
│   │       └── chunk_eligibility.py
│   │
│   └── tests/                       # Backend and pipeline tests
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── features/
│       ├── services/
│       └── types/
│
├── docs/                            # Project documentation
│
├── requirements.txt                 # Python dependencies
├── README.md
└── venv/                            # Python virtual environment
```

> Directory contents may expand as the project develops. The structure above represents the current major modules and the data-processing pipeline.

---

# Government Scheme Knowledge Base

The current knowledge base is being prepared primarily from the **Rajasthan Jan Soochna Portal** and related official government sources.

The current dataset contains:

```text
Processed scheme records : 192
Exact duplicates         : 0
Generated chunks         : 721
```

The current scheme record structure contains information such as:

```text
scheme_name
scheme_id
department
source_type
source_file
source_path
source_url
eligibility_rules
documents_required
application_process
```

---

# Data Processing Pipeline

## 1. Crawling

The crawling stage collects Government scheme-related information from official sources.

### Main tasks

- Crawl official government sources
- Discover relevant scheme pages
- Collect document/page URLs
- Download available content
- Store raw data
- Preserve source information

### Example command

```powershell
cd D:\Sem7\Major\NeetiNex
```

The exact crawler command depends on the current crawler implementation.

---

## 2. Extraction

The extraction stage converts the raw Jan Soochna HTML into structured JSON scheme records.

### Main tasks

- Read raw HTML
- Identify the relevant eligibility section
- Extract department
- Identify scheme name and scheme ID
- Extract eligibility rules
- Extract required documents
- Extract application process
- Extract official scheme URL
- Store source metadata

### Current command

From the project root:

```powershell
cd D:\Sem7\Major\NeetiNex\backend
python ingestion\extraction\extract_html.py
```

---

## 3. Validation

Validation checks whether extracted records contain the required information before further processing.

### Main checks

- Scheme name
- Scheme ID
- Department
- Source file
- Source URL
- Eligibility rules
- Required documents
- Application process
- Scheme matching information

### Command

```powershell
cd D:\Sem7\Major\NeetiNex\backend
python ingestion\validation\validate_eligibility.py
```

### Current validation result

```text
Total files : 192
Valid       : 192
Warnings    : 0
Errors      : 0
```

The validation report is stored under:

```text
backend\data\processed\jansoochna\eligibility\quality_reports\
```

---

# 4. Cleaning

The cleaning stage removes formatting noise while preserving government-source wording.

### Cleaning includes

- Whitespace normalization
- Removal of unnecessary numbering
- Removal of leading Roman numeral markers
- List-item cleanup
- Formatting normalization

### Important principle

The cleaning process does **not** automatically correct government-source spelling, grammar, or facts.

This prevents preprocessing from silently changing official information.

### Command

```powershell
cd D:\Sem7\Major\NeetiNex\backend
python ingestion\cleaning\clean_text.py
```

---

# 5. Exact Deduplication

The deduplication stage identifies exact duplicate scheme records.

The comparison uses:

```text
scheme_name
scheme_id
department
eligibility_rules
documents_required
application_process
source_url
```

File names and file paths are not used as the main content identity.

### Command

```powershell
cd D:\Sem7\Major\NeetiNex\backend
python ingestion\deduplication\deduplicate.py
```

### Current result

```text
Input files     : 192
Unique files    : 192
Duplicate files : 0
Failed files    : 0
```

The duplicate report is stored under:

```text
backend\data\processed\jansoochna\eligibility\quality_reports\
```

---

# 6. Section-Aware Chunking

After cleaning and deduplication, the scheme records are converted into LangChain Documents.

The current sections are:

```text
Government Scheme
     │
     ├── Eligibility
     ├── Documents Required
     └── Application Process
```

Each section is processed separately so that unrelated information is not unnecessarily mixed.

### Chunking configuration

```text
Chunk Size   = 700 characters
Overlap      = 100 characters
```

These values are initial parameters and can be tuned later through retrieval evaluation.

### Command

Install the required packages:

```powershell
cd D:\Sem7\Major\NeetiNex\backend
pip install langchain langchain-text-splitters
```

Run chunking:

```powershell
python ingestion\chunking\chunk_eligibility.py
```

### Current result

```text
Input files     : 192
Processed files : 192
Failed files    : 0
Total chunks    : 721
```

Generated chunks are stored in:

```text
backend\data\processed\jansoochna\eligibility\chunks\
```

---

# Complete Data Processing Execution Order

From the project root:

```powershell
cd D:\Sem7\Major\NeetiNex\backend
```

### Step 1 — Extraction

```powershell
python ingestion\extraction\extract_html.py
```

### Step 2 — Validation

```powershell
python ingestion\validation\validate_eligibility.py
```

### Step 3 — Cleaning

```powershell
python ingestion\cleaning\clean_text.py
```

### Step 4 — Deduplication

```powershell
python ingestion\deduplication\deduplicate.py
```

### Step 5 — Chunking

```powershell
python ingestion\chunking\chunk_eligibility.py
```

---

# RAG Architecture

The current Scheme Q&A architecture is:

```text
                    User
                     │
                     ▼
              Frontend Question
                     │
                     ▼
                FastAPI API
                     │
                     ▼
              Query Processing
                     │
                     ▼
              Query Embedding
                     │
                     ▼
                Vector Store
                     │
                     ▼
            Relevant Scheme Chunks
                     │
                     ▼
                RAG Context
                     │
                     ▼
                    LLM
                     │
                     ▼
             Grounded Response
                     │
                     ▼
             Official Source
```

The key principle is:

> The LLM should generate the explanation using retrieved government information rather than relying only on its internal knowledge.

---

# Scheme Discovery Architecture

Scheme Discovery is separate from normal question answering.

The intended flow is:

```text
User
 │
 ▼
Personal Information
 │
 ├── Age
 ├── State / Residence
 ├── Income
 ├── Student Status
 ├── Occupation
 └── Other Criteria
 │
 ▼
Structured User Profile
 │
 ▼
Rule-Based Eligibility Engine
 │
 ▼
Verified Eligibility Rules
 │
 ▼
Matching Schemes
 │
 ▼
RAG / Official Information
 │
 ▼
Explanation + Source
```

The current project does **not** treat vector similarity as a final eligibility decision.

An earlier attempt was made to automatically extract eligibility conditions from natural-language scheme text. It was not reliable enough to be treated as the final eligibility-rule generation method.

Therefore, structured eligibility rules require additional verification and careful design.

---

# Frontend and Backend

The current application architecture connects the frontend to the FastAPI backend.

```text
Frontend
   │
   ▼
FastAPI Backend
   │
   ▼
RAG Pipeline
   │
   ├── Query Processing
   ├── Embedding
   ├── Vector Store
   ├── Retrieval
   └── LLM
   │
   ▼
Response
   │
   ▼
Frontend
```

---

# Running the Backend

Activate the virtual environment first.

### Windows PowerShell

From the project root:

```powershell
cd D:\Sem7\Major\NeetiNex
.\venv\Scripts\Activate.ps1
```

Then move to the backend:

```powershell
cd backend
```

Start FastAPI:

```powershell
uvicorn backend.api.main:app --reload
```

If the project is executed from a directory where the package path is different, use the import path corresponding to the current project structure.

The development server is expected to run at:

```text
http://127.0.0.1:8000
```

FastAPI API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

# Running the Frontend

The frontend uses the Node.js/npm environment.

From the project root:

```powershell
cd frontend
```

Install dependencies if required:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Use the URL shown by the frontend development server in the terminal.

> The exact frontend command can depend on the frontend package configuration.

---

# Python Environment Setup

If the project environment needs to be recreated:

```powershell
cd D:\Sem7\Major\NeetiNex
python -m venv venv
```

Activate:

```powershell
.\venv\Scripts\Activate.ps1
```

Install project dependencies:

```powershell
pip install -r requirements.txt
```

For the current LangChain chunking stage:

```powershell
pip install langchain langchain-text-splitters
```

---

# Git Commands

Check project status:

```powershell
git status
```

Add changes:

```powershell
git add .
```

Commit:

```powershell
git commit -m "update NeetiNex pipeline"
```

Push:

```powershell
git push
```

Pull latest changes:

```powershell
git pull
```

---

# Important Data Directories

## Raw Data

```text
backend\data\raw\jansoochna\eligibility\html\
```

Contains the original crawled HTML files.

**Do not modify raw source files unnecessarily.**

---

## Extracted Data

```text
backend\data\processed\jansoochna\eligibility\extracted\
```

Contains structured JSON generated from raw HTML.

---

## Cleaned Data

```text
backend\data\processed\jansoochna\eligibility\cleaned\
```

Contains normalized JSON after formatting cleanup.

---

## Deduplicated Data

```text
backend\data\processed\jansoochna\eligibility\deduplicated\
```

Contains the unique processed scheme records used for downstream processing.

---

## Chunks

```text
backend\data\processed\jansoochna\eligibility\chunks\
```

Contains the final section-aware chunks used as input to the embedding/retrieval stage.

---

## Quality Reports

```text
backend\data\processed\jansoochna\eligibility\quality_reports\
```

Contains validation and deduplication reports.

---

# Data Quality Principles

NeetiNex follows these principles throughout the knowledge pipeline:

- Use official Government sources as the primary information source.
- Preserve source information.
- Keep raw and processed data separate.
- Avoid unnecessary duplicate data.
- Do not silently modify official facts.
- Validate data before downstream processing.
- Keep ingestion stages modular.
- Preserve metadata required for source citation.
- Do not treat LLM-generated guesses as official information.
- Keep eligibility decision-making separate from normal LLM response generation where possible.

---

# Current Architecture Summary

```text
                         NeetiNex
                            │
             ┌──────────────┴──────────────┐
             │                             │
       Scheme Discovery                Scheme Q&A
             │                             │
     Eligibility Engine                   RAG
             │                             │
    Structured Rules                Vector Retrieval
             │                             │
             │                         LLM Response
             │                             │
             └──────────────┬──────────────┘
                            │
                 Government Knowledge Base
                            │
       ┌────────────────────┴────────────────────┐
       │                                         │
    Raw Sources                            Processed Data
       │                                         │
    Crawling → Extraction → Validation → Cleaning
                            ↓
                     Deduplication
                            ↓
                  Section-Aware Chunking
                            ↓
                       Embeddings
                            ↓
                      Vector Store
```

---

# Future Document / PDF RAG

PDF/document upload is planned as a separate temporary retrieval workflow.

The intended architecture is:

```text
User Uploads PDF
       ↓
Document Processing
       ↓
Temporary Chunks
       ↓
Temporary Vector Store
       ↓
User Question
       ↓
Retrieval
       ↓
Document Context
       ↓
LLM
       ↓
Answer
```

Uploaded documents should remain separate from the permanent Government Scheme Knowledge Base.

This prevents user-provided documents from contaminating the verified government scheme dataset.

---

# Future Development

The upcoming development stages include:

1. Improve and test Scheme Q&A retrieval.
2. Implement and evaluate the Rule-Based Eligibility Engine.
3. Develop Scheme Discovery user flow.
4. Implement PDF upload.
5. Implement temporary PDF/document RAG.
6. Improve retrieval using BM25 and hybrid retrieval.
7. Add reranking.
8. Improve source citation and answer grounding.
9. Add conversational user profile support.
10. Add voice interaction.
11. Perform systematic testing and evaluation.
12. Prepare final project documentation and demonstration.

---

# Current Milestone

```text
Government Scheme Knowledge Base
              ↓
Crawling                 ✓
Extraction               ✓
Validation               ✓
Cleaning                 ✓
Deduplication            ✓
Chunking                 ✓
Embeddings               ✓
Vector Store             ✓
RAG Pipeline             ✓
Frontend                 ✓
```

### Current Major Milestone

**Government scheme data has been processed from raw official HTML through extraction, validation, cleaning, deduplication and section-aware chunking, and the resulting knowledge has been connected to embeddings, vector retrieval, RAG and the initial frontend workflow.**

---

# Project Status Summary

**Project:** NeetiNex

**Title:** An AI-Powered Government Scheme Assistance Platform

**Primary Features:**

- Scheme Discovery
- Scheme Q&A
- Official Source References
- Rule-Based Eligibility Checking
- RAG-based Government Scheme Question Answering
- Temporary Document/PDF RAG
- Future Voice Interaction

**Current Data Pipeline:**

```text
Crawling
   ↓
Extraction
   ↓
Validation
   ↓
Cleaning
   ↓
Deduplication
   ↓
Section-Aware Chunking
   ↓
Embeddings
   ↓
Vector Store
   ↓
RAG
   ↓
Frontend
```

**Current Dataset Result:**

```text
192 processed scheme records
721 generated chunks
0 exact duplicates
0 validation errors
```

---

# Notes for Contributors

Before changing the pipeline:

1. Keep the raw government data unchanged.
2. Test changes on processed data first.
3. Run validation after extraction changes.
4. Run deduplication before chunking.
5. Verify chunk quality before changing embedding/retrieval logic.
6. Preserve scheme metadata and official source URLs.
7. Do not automatically convert uncertain natural-language eligibility text into final eligibility rules.
8. Keep temporary uploaded documents separate from the permanent government knowledge base.
9. Commit changes regularly using Git.
10. Prefer simple, modular and testable implementations.

---

# License / Academic Project

NeetiNex is an academic major project developed for educational and research purposes.

Government scheme information should be verified against the latest official Government source before being used for real-world decisions.
