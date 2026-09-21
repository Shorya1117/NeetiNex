# NeetiNex

## An AI-Powered Government Scheme Assistance Platform

NeetiNex is a major project focused on helping citizens discover and understand Central Government and Rajasthan Government schemes through natural-language interaction.

The current development work focuses on collecting Government scheme data and preparing it for the next stages of the project.

---

## Project Overview

The current data-processing pipeline of NeetiNex consists of the following stages:

```text
Government Website
       ↓
    Crawling
       ↓
   Extraction
       ↓
    Cleaning
       ↓
 Deduplication
       ↓
    Chunking
```

All stages from **crawling to chunking have been completed**.

---

# Project Directory

```text
NeetiNex/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/                    # API endpoints for the application
│   │   ├── core/                   # Core application configuration and utilities
│   │   ├── db/                     # Database configuration and database-related code
│   │   ├── eligibility/            # Scheme eligibility checking logic
│   │   ├── models/                 # Application and database models
│   │   ├── rag/                    # Retrieval-Augmented Generation components
│   │   ├── schemas/                # Request and response schemas
│   │   └── services/               # Application business logic and services
│   │
│   ├── data/
│   │   ├── raw/
│   │   │   └── jansoochna/          # Raw data collected from Jan Soochna
│   │   │
│   │   ├── processed/
│   │   │   └── jansoochna/
│   │   │       ├── eligibility/     # Processed eligibility-related scheme data
│   │   │       ├── extracted/       # Text/data extracted from collected documents
│   │   │       ├── cleaned/         # Cleaned and normalized extracted data
│   │   │       ├── deduplicated/    # Duplicate-free processed data
│   │   │       ├── chunks/          # Final text chunks generated from documents
│   │   │       └── quality_reports/ # Data-quality and processing reports
│   │   │
│   │   └── verified/                # Verified Government scheme data
│   │
│   ├── ingestion/
│   │   ├── chunking/                # Text chunking logic
│   │   ├── cleaning/                # Text cleaning and normalization
│   │   ├── deduplication/           # Duplicate document/content handling
│   │   ├── extraction/              # Document and text extraction
│   │   ├── jansoochna/              # Jan Soochna-specific ingestion components
│   │   ├── pipeline/                # Data-processing pipeline orchestration
│   │   └── validation/              # Data validation and quality checks
│   │
│   └── tests/                       # Backend and pipeline tests
│
├── frontend/
│   ├── public/                      # Public frontend assets
│   └── src/
│       ├── components/              # Reusable UI components
│       ├── features/                # Feature-specific frontend modules
│       ├── services/                # Frontend API and service integrations
│       └── types/                   # Frontend type definitions
│
├── docs/                            # Project documentation
│
└── venv/                            # Python virtual environment
```

---

# Data Processing Pipeline

## 1. Crawling

The crawling stage collects Government scheme-related information from the official Rajasthan Jan Soochna portal.

The crawler collects the required pages and documents and stores the raw data for further processing.

### Main tasks

* Crawl the official source
* Discover relevant scheme information
* Collect document/page URLs
* Download available documents
* Store the collected raw data
* Maintain source information

### Command

```powershell
cd backend\ingestion\jansoochna\crawler
python crawler.py
```

---

## 2. Extraction

After crawling, the collected documents are processed to extract usable text.

The extraction stage converts the collected document content into text that can be processed further.

### Main tasks

* Read collected documents
* Extract textual content
* Process document content
* Save extracted text

### Command

```powershell
cd backend\ingestion\jansoochna\extraction
python extraction.py
```

---

## 3. Cleaning

The extracted text may contain unnecessary spaces, line breaks, formatting artifacts, and other unwanted content.

The cleaning stage prepares the extracted text into a cleaner and more consistent form.

### Main tasks

* Remove unnecessary spaces
* Normalize line breaks
* Remove unwanted formatting
* Clean extracted content
* Prepare consistent text

### Command

```powershell
cd backend\ingestion\jansoochna\cleaning
python cleaning.py
```

---

## 4. Deduplication

During crawling and processing, the same document or content can appear multiple times.

The deduplication stage identifies duplicate data and keeps the required unique information.

### Main tasks

* Identify duplicate documents
* Detect repeated content
* Avoid unnecessary repeated processing
* Preserve unique documents
* Reduce duplicate data

### Command

```powershell
cd backend\ingestion\jansoochna\deduplication
python deduplication.py
```

---

## 5. Chunking

Chunking is the final completed stage of the current data-preprocessing pipeline.

The cleaned and deduplicated documents are divided into smaller text sections called chunks.

These chunks provide a structured form of the processed Government scheme information for the next stage of the project.

### Main tasks

* Process cleaned documents
* Split documents into smaller sections
* Maintain useful document context
* Preserve source information
* Store the generated chunks

### Command

```powershell
cd backend\ingestion\jansoochna\chunking
python chunking.py
```

---

# Complete Execution Order

The complete pipeline should be executed in the following order:

### Step 1 — Crawling

```powershell
cd backend\ingestion\jansoochna\crawler
python crawler.py
```

↓

### Step 2 — Extraction

```powershell
cd ..\extraction
python extraction.py
```

↓

### Step 3 — Cleaning

```powershell
cd ..\cleaning
python cleaning.py
```

↓

### Step 4 — Deduplication

```powershell
cd ..\deduplication
python deduplication.py
```

↓

### Step 5 — Chunking

```powershell
cd ..\chunking
python chunking.py
```

---

# Current Data Flow

```text
                    Official Government Source
                              │
                              ▼
                       ┌─────────────┐
                       │   Crawler   │
                       └──────┬──────┘
                              │
                              ▼
                         Raw Data
                              │
                              ▼
                       ┌─────────────┐
                       │ Extraction  │
                       └──────┬──────┘
                              │
                              ▼
                       Extracted Text
                              │
                              ▼
                       ┌─────────────┐
                       │   Cleaning  │
                       └──────┬──────┘
                              │
                              ▼
                         Clean Text
                              │
                              ▼
                     ┌─────────────────┐
                     │  Deduplication  │
                     └────────┬────────┘
                              │
                              ▼
                        Unique Data
                              │
                              ▼
                       ┌─────────────┐
                       │   Chunking  │
                       └──────┬──────┘
                              │
                              ▼
                         Text Chunks
```

---

# Issues Handled During Data Collection

During the crawling stage, duplicate documents and repeated resources were encountered.

Some documents could appear through different URLs or could be encountered multiple times during crawling.

These issues were handled as part of the preprocessing pipeline so that duplicate information does not unnecessarily continue into the later stages.

Another important concern was avoiding the accidental skipping of valid documents during the crawling and processing process.

The pipeline therefore focuses on:

* Detecting duplicate documents
* Preserving valid documents
* Avoiding unnecessary repeated processing
* Maintaining source information
* Preparing reliable processed data

---

# Data Processing Output

After completing the current pipeline, the data passes through the following stages:

```text
Raw Data
   ↓
Extracted Data
   ↓
Cleaned Data
   ↓
Deduplicated Data
   ↓
Chunked Data
```

The final output of the current completed work is the **chunked Government scheme dataset**.

---

# Current Project Status

```text
Crawling          ✓ Completed
Extraction        ✓ Completed
Cleaning          ✓ Completed
Deduplication     ✓ Completed
Chunking          ✓ Completed
```

### Current Milestone

**Government Scheme Data Collection and Preprocessing — Completed up to Chunking**

The data has successfully gone through the current preprocessing pipeline from crawling to chunk generation.

---

# Development Sequence

The project development is being carried out step-by-step.

The currently completed sequence is:

```text
1. Crawling
       ↓
2. Extraction
       ↓
3. Cleaning
       ↓
4. Deduplication
       ↓
5. Chunking
```

The project will continue from the processed chunked data in the next development stage.

---

# Data Quality Principles

The following principles are followed during the data-processing pipeline:

* Use Government sources as the primary source of information.
* Preserve source information wherever possible.
* Avoid unnecessary duplicate data.
* Do not lose valid documents during processing.
* Keep raw and processed data separate.
* Maintain a clear processing sequence.
* Keep each processing stage modular.
* Verify processed data before using it in subsequent stages.

---

# Project Status Summary

**Project:** NeetiNex
**Title:** An AI-Powered Government Scheme Assistance Platform

**Current completed milestone:**

> Government scheme data has been crawled, extracted, cleaned, deduplicated, and chunked.

**Current pipeline:**

```text
Crawling → Extraction → Cleaning → Deduplication → Chunking
```

**Status:** Completed up to Chunking
