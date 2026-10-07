import os
import uuid
from pathlib import Path
from typing import Dict

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


class TemporaryPDFRAG:

    def __init__(self):

        print("======================================")
        print("Initializing Temporary PDF RAG")
        print("======================================")

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are NeetiNex Temporary Document Assistant.

Answer the user's question ONLY using the content retrieved
from the uploaded PDF.

STRICT RULES:

1. Do not use outside knowledge.
2. Do not invent information.
3. If the PDF does not contain the answer, clearly say that
   the uploaded document does not contain enough information.
4. Keep the answer simple and clear.
5. If page information is available, mention the relevant page.
6. Do not make assumptions.
7. If the user asks in Hindi, answer in Hindi.
8. If the user asks in Hinglish, answer in natural Hinglish.
9. If the user asks in English, answer in English.

UPLOADED PDF CONTEXT:

{context}
"""
                ),
                (
                    "human",
                    "{question}"
                )
            ]
        )

        # document_id -> FAISS vectorstore
        self.vectorstores: Dict[str, FAISS] = {}

        print("Temporary PDF RAG initialized successfully.")

    # ==================================================
    # PROCESS PDF
    # ==================================================

    def process_pdf(self, file_path: str):

        document_id = str(uuid.uuid4())

        print(f"Processing PDF: {file_path}")

        # Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        if not documents:
            raise ValueError(
                "Could not extract any text from the PDF."
            )

        # Chunk
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )

        chunks = splitter.split_documents(documents)

        if not chunks:
            raise ValueError(
                "No usable text chunks were created."
            )

        # Add document ID + page metadata
        for chunk in chunks:

            chunk.metadata["document_id"] = document_id

            if "page" in chunk.metadata:
                chunk.metadata["page"] = (
                    chunk.metadata["page"] + 1
                )

        # Create temporary FAISS vector store
        vectorstore = FAISS.from_documents(
            chunks,
            self.embeddings
        )

        self.vectorstores[document_id] = vectorstore

        print(
            f"PDF processed successfully: "
            f"{len(chunks)} chunks"
        )

        return {
            "document_id": document_id,
            "filename": Path(file_path).name,
            "pages": len(documents),
            "chunks": len(chunks)
        }

    # ==================================================
    # ASK QUESTION
    # ==================================================

    def ask(
        self,
        document_id: str,
        question: str
    ):

        if document_id not in self.vectorstores:

            raise ValueError(
                "PDF session not found or expired."
            )

        vectorstore = self.vectorstores[document_id]

        # Retrieve relevant chunks
        documents = vectorstore.similarity_search(
            question,
            k=5
        )

        if not documents:

            return {
                "answer": (
                    "The uploaded PDF does not "
                    "contain enough information "
                    "to answer this question."
                ),
                "sources": []
            }

        # Build context
        context_parts = []
        sources = []

        for document in documents:

            page = document.metadata.get("page")

            if page:
                source = {
                    "page": page
                }

                if source not in sources:
                    sources.append(source)

                context_parts.append(
                    f"[Page {page}]\n"
                    f"{document.page_content}"
                )

            else:
                context_parts.append(
                    document.page_content
                )

        context = "\n\n---\n\n".join(
            context_parts
        )

        # Generate answer
        messages = self.prompt.format_messages(
            question=question,
            context=context
        )

        response = self.llm.invoke(messages)

        return {
            "answer": response.content,
            "sources": sources
        }

    # ==================================================
    # DELETE TEMPORARY DOCUMENT
    # ==================================================

    def delete_document(self, document_id: str):

        if document_id in self.vectorstores:

            del self.vectorstores[document_id]

        return {
            "document_id": document_id,
            "deleted": True
        }