import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "deduplicated"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "chunks"
)

# ============================================================
# CHUNK SETTINGS
# ============================================================

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# ============================================================
# LANGCHAIN TEXT SPLITTER
# ============================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ],
)

# ============================================================
# BUILD SECTION TEXT
# ============================================================

def build_section_text(items):
    """
    Convert a list of extracted values into text.

    Government wording is preserved.
    No spelling or grammar correction is performed.
    """
    if not isinstance(items, list):
        return ""

    values = []

    for item in items:
        if not isinstance(item, str):
            continue

        item = item.strip()

        if item:
            values.append(item)

    return "\n".join(values)

# ============================================================
# CREATE ONE LANGCHAIN DOCUMENT
# ============================================================

def create_section_document(
    data,
    section_name,
    section_items,
):
    """
    Create a LangChain Document for one scheme section.
    """
    section_text = build_section_text(section_items)

    if not section_text:
        return None

    scheme_name = data.get("scheme_name", "")
    scheme_id = data.get("scheme_id", "")
    department = data.get("department", "")
    source_file = data.get("source_file", "")
    source_url = data.get("source_url", "")

    page_content = (
        f"Scheme: {scheme_name}\n"
        f"Department: {department}\n"
        f"Section: {section_name}\n\n"
        f"{section_text}"
    )

    metadata = {
        "document_type": "government_scheme",
        "scheme_name": scheme_name,
        "scheme_id": scheme_id,
        "department": department,
        "section": section_name,
        "source_file": source_file,
        "source_url": source_url,
        "source_type": data.get(
            "source_type",
            "jansoochna_eligibility"
        ),
    }

    return Document(
        page_content=page_content,
        metadata=metadata,
    )

# ============================================================
# CREATE SECTION DOCUMENTS
# ============================================================

def create_documents(data):
    """
    Convert one scheme JSON into separate
    section-aware LangChain Documents.
    """
    documents = []

    sections = [
        (
            "eligibility",
            data.get("eligibility_rules", []),
        ),
        (
            "documents_required",
            data.get("documents_required", []),
        ),
        (
            "application_process",
            data.get("application_process", []),
        ),
    ]

    for section_name, section_items in sections:
        document = create_section_document(
            data,
            section_name,
            section_items,
        )

        if document is not None:
            documents.append(document)

    return documents

# ============================================================
# SPLIT DOCUMENTS
# ============================================================

def split_documents(documents):
    """
    Split each section independently.

    This prevents eligibility, documents,
    and application information from being
    unnecessarily mixed together.
    """
    chunks = []

    for document in documents:
        section_chunks = text_splitter.split_documents(
            [document]
        )

        chunks.extend(section_chunks)

    return chunks

# ============================================================
# SAVE CHUNKS
# ============================================================

def save_chunks(
    json_file,
    chunks,
):
    """
    Save all chunks belonging to one scheme.
    """
    output_file = OUTPUT_DIR / f"{json_file.stem}_chunks.json"

    chunk_records = []

    for index, chunk in enumerate(chunks):
        record = {
            "chunk_id": f"{json_file.stem}_{index + 1}",
            "chunk_index": index,
            "page_content": chunk.page_content,
            "metadata": chunk.metadata,
        }

        chunk_records.append(record)

    output_file.write_text(
        json.dumps(
            chunk_records,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

# ============================================================
# MAIN
# ============================================================

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    json_files = sorted(INPUT_DIR.glob("*.json"))

    print(
        f"Found {len(json_files)} deduplicated JSON files."
    )

    processed_count = 0
    failed_count = 0
    total_chunks = 0

    for json_file in json_files:
        try:
            with json_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            documents = create_documents(data)
            chunks = split_documents(documents)

            save_chunks(
                json_file,
                chunks
            )

            processed_count += 1
            total_chunks += len(chunks)

            print(
                f"[CHUNKED] {json_file.name} "
                f"-> {len(chunks)} chunks"
            )

        except Exception as exc:
            failed_count += 1

            print(f"[ERROR] {json_file.name}")
            print(f"        {exc}")

    print()
    print("=" * 55)
    print("Chunking completed.")
    print("=" * 55)
    print(f"Input files     : {len(json_files)}")
    print(f"Processed files : {processed_count}")
    print(f"Failed files    : {failed_count}")
    print(f"Total chunks    : {total_chunks}")
    print("=" * 55)
    print()
    print("Chunks saved to:")
    print(OUTPUT_DIR)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()