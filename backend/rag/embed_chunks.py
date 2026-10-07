import json
from pathlib import Path

import chromadb
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

CHUNKS_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "chunks"
)

VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"


# --------------------------------------------------
# Embedding model
# --------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# --------------------------------------------------
# Chroma collection
# --------------------------------------------------

COLLECTION_NAME = "neetinex_schemes"


def load_chunks():
    """Load all chunk JSON files and convert them to LangChain Documents."""

    documents = []

    json_files = sorted(CHUNKS_DIR.glob("*.json"))

    print(f"Found {len(json_files)} JSON files.")

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as file:
                chunks = json.load(file)

            if not isinstance(chunks, list):
                print(f"Skipping {json_file.name}: expected a list.")
                continue

            for chunk in chunks:
                page_content = chunk.get("page_content", "").strip()
                metadata = chunk.get("metadata", {})

                if not page_content:
                    continue

                # Add chunk-level information to metadata
                metadata = dict(metadata)

                metadata["chunk_id"] = chunk.get("chunk_id", "")
                metadata["chunk_index"] = chunk.get("chunk_index", 0)
                metadata["source_json"] = json_file.name

                documents.append(
                    Document(
                        page_content=page_content,
                        metadata=metadata,
                    )
                )

        except Exception as error:
            print(f"Error reading {json_file.name}: {error}")

    return documents


def main():
    print("======================================")
    print("NeetiNex - Embedding Pipeline")
    print("======================================")

    print(f"\nChunks directory:")
    print(CHUNKS_DIR)

    print(f"\nVector store directory:")
    print(VECTORSTORE_DIR)

    if not CHUNKS_DIR.exists():
        raise FileNotFoundError(
            f"Chunks directory not found: {CHUNKS_DIR}"
        )

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------
    # Load chunks
    # ----------------------------------------------

    print("\nLoading chunks...")

    documents = load_chunks()

    print(f"Loaded {len(documents)} documents.")

    if not documents:
        raise RuntimeError("No valid chunks found.")

    # ----------------------------------------------
    # Embedding model
    # ----------------------------------------------

    print("\nLoading embedding model...")
    print(f"Model: {EMBEDDING_MODEL}")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    print("Embedding model loaded.")

    # ----------------------------------------------
    # Chroma
    # ----------------------------------------------

    print("\nInitializing Chroma...")

    client = chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Existing vectors: {collection.count()}")

    # ----------------------------------------------
    # Prepare data
    # ----------------------------------------------

    ids = []
    texts = []
    metadatas = []

    for index, document in enumerate(documents):

        chunk_id = document.metadata.get("chunk_id")

        if not chunk_id:
            chunk_id = f"chunk_{index}"

        # Make ID unique across files
        source_json = document.metadata.get(
            "source_json",
            "unknown",
        )

        document_id = f"{source_json}::{chunk_id}"

        ids.append(document_id)
        texts.append(document.page_content)
        metadatas.append(document.metadata)

    # ----------------------------------------------
    # Generate embeddings
    # ----------------------------------------------

    print("\nGenerating embeddings...")

    vectors = embeddings.embed_documents(texts)

    print(f"Generated {len(vectors)} embeddings.")

    # ----------------------------------------------
    # Store in Chroma
    # ----------------------------------------------

    print("\nStoring vectors in Chroma...")

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=vectors,
    )

    print("\n======================================")
    print("Embedding completed successfully!")
    print("======================================")

    print(f"Documents processed : {len(documents)}")
    print(f"Vectors in database : {collection.count()}")
    print(f"Vector store        : {VECTORSTORE_DIR}")


if __name__ == "__main__":
    main()