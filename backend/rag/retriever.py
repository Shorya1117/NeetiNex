import chromadb

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from backend.rag.scheme_matcher import SchemeMatcher


VECTORSTORE_DIR = "backend/data/vectorstore"
COLLECTION_NAME = "neetinex_schemes"

EMBEDDING_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


class NeetiNexRetriever:

    def __init__(self):
        print("Loading embedding model...")

        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )

        print("Connecting to Chroma...")

        self.client = chromadb.PersistentClient(
            path=VECTORSTORE_DIR
        )

        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

        print(
            f"Loaded {self.collection.count()} vectors."
        )

        self.scheme_matcher = SchemeMatcher(
            self.collection
        )

    def get_scheme_chunks(self, scheme_name):
        """
        Retrieve all chunks belonging to a scheme.
        """

        results = self.collection.get(
            where={
                "scheme_name": scheme_name
            },
            limit=50,
        )

        documents = []

        for i in range(len(results["ids"])):

            metadata = results["metadatas"][i]

            documents.append(
                Document(
                    page_content=results["documents"][i],
                    metadata=metadata,
                )
            )

        return documents

    def semantic_search(
        self,
        query,
        n_results=5,
    ):
        """
        Global semantic search across all schemes.

        Used when no specific scheme can be identified.
        """

        query_embedding = (
            self.embeddings.embed_query(query)
        )

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        documents = []

        for i in range(
            len(results["documents"][0])
        ):

            metadata = results["metadatas"][0][i]

            documents.append(
                Document(
                    page_content=results["documents"][0][i],
                    metadata=metadata,
                )
            )

        return documents

    def retrieve(
        self,
        query,
        n_results=5,
    ):
        """
        Main NeetiNex retrieval method.

        1. Detect scheme.
        2. If scheme found, retrieve only
           chunks belonging to that scheme.
        3. If no scheme found, fall back
           to global semantic search.
        """

        print("\n======================================")
        print("NEETINEX RETRIEVAL")
        print("======================================")

        print(f"\nQuery:")
        print(query)

        scheme_name = self.scheme_matcher.find_scheme(
            query
        )

        # -----------------------------------------
        # Scheme-aware retrieval
        # -----------------------------------------

        if scheme_name:

            print(
                f"\nDetected scheme:"
                f" {scheme_name}"
            )

            documents = self.get_scheme_chunks(
                scheme_name
            )

            print(
                f"Retrieved {len(documents)} "
                f"scheme chunks."
            )

            return documents

        # -----------------------------------------
        # Global semantic fallback
        # -----------------------------------------

        print(
            "\nNo specific scheme detected."
        )

        print(
            "Using global semantic search..."
        )

        documents = self.semantic_search(
            query,
            n_results=n_results,
        )

        return documents