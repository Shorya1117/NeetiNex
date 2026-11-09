
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import fitz
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


class TemporaryPDFRAG:

    def __init__(self):
        print("Initializing Temporary PDF RAG...")

        # -------------------------------------------------
        # TESSERACT CONFIGURATION
        # -------------------------------------------------

        tesseract_path = shutil.which("tesseract")

        if not tesseract_path:
            default_path = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )

            if os.path.isfile(default_path):
                tesseract_path = default_path

        if not tesseract_path:
            raise RuntimeError(
                "Tesseract not found. Install Tesseract OCR "
                "and configure its PATH."
            )

        pytesseract.pytesseract.tesseract_cmd = tesseract_path

        languages = pytesseract.get_languages(config="")

        if "eng" not in languages or "hin" not in languages:
            raise RuntimeError(
                "Tesseract requires both English (eng) "
                "and Hindi (hin) language data."
            )

        print(f"Tesseract: {tesseract_path}")
        print(f"OCR languages available: {languages}")

        # -------------------------------------------------
        # EMBEDDING MODEL
        # -------------------------------------------------

        self.embeddings = HuggingFaceEmbeddings(
            model_name=(
                "sentence-transformers/"
                "paraphrase-multilingual-MiniLM-L12-v2"
            )
        )

        # -------------------------------------------------
        # LLM
        # -------------------------------------------------

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing from environment variables."
            )

        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=api_key
        )

        # -------------------------------------------------
        # GROUNDED ANSWER PROMPT
        # -------------------------------------------------

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
You are NeetiNex Temporary Document Assistant.

Your task is to answer questions using ONLY the supplied
context extracted from the user's uploaded PDF.

STRICT RULES:

1. Never use outside knowledge to fill missing information.
2. Never invent dates, names, locations, eligibility rules,
   amounts, page numbers, or document requirements.
3. OCR text may contain recognition mistakes. Do not silently
   convert unclear characters into a confident factual answer.
4. If the requested information is missing or unreadable,
   clearly say that it could not be verified from the extracted
   text of the uploaded PDF.
5. If the user asks about a particular PDF page, prioritize
   information from that page. Do not present information
   from another page as if it came from the requested page.
6. For tables, distinguish institution names, locations,
   and states carefully. Do not combine different rows.
7. Use the page numbers provided in the context.
8. Cite relevant pages in your answer, for example:
   Source: PDF page 8.
9. Do not claim that you verified the original document image
   when you only received extracted text.
10. Answer in the language used by the user.
11. Keep answers clear and concise.
12. If the context contradicts itself or contains suspicious
    OCR text, explain the uncertainty instead of guessing.

Retrieved PDF context:
{context}
"""
            ),
            ("human", "{question}")
        ])

        # -------------------------------------------------
        # TEMPORARY IN-MEMORY STORAGE
        # -------------------------------------------------

        self.vectorstores: Dict[str, FAISS] = {}
        self.files: Dict[str, str] = {}

        # Original extracted text for each PDF page.
        self.page_texts: Dict[str, Dict[int, str]] = {}

        # All chunks belonging to each document.
        self.document_chunks: Dict[str, List[Document]] = {}

        print("Temporary PDF RAG initialized successfully.")

    # =====================================================
    # OCR IMAGE PREPROCESSING
    # =====================================================

    @staticmethod
    def preprocess_image(image: Image.Image) -> Image.Image:
        """
        Improve scanned page readability before OCR.
        """

        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)

        image = ImageEnhance.Contrast(image).enhance(1.5)
        image = image.filter(ImageFilter.SHARPEN)

        return image

    # =====================================================
    # OCR TEXT EXTRACTION
    # =====================================================

    def run_ocr(self, page: fitz.Page, page_number: int) -> str:
        """
        Render a PDF page at 300 DPI and extract Hindi/English text.
        """

        print(f"Page {page_number}: Running OCR...")

        pix = page.get_pixmap(
            matrix=fitz.Matrix(300 / 72, 300 / 72),
            colorspace=fitz.csRGB,
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples
        )

        image = self.preprocess_image(image)

        ocr_results = []

        # PSM 3: automatic page layout analysis.
        # PSM 6: assumes a single uniform text block.
        # Comparing both can help with differently formatted pages.
        for psm in (3, 6):
            try:
                config = f"--oem 3 --psm {psm}"

                result = pytesseract.image_to_string(
                    image,
                    lang="hin+eng",
                    config=config
                ).strip()

                if result:
                    ocr_results.append(result)

            except pytesseract.TesseractError as exc:
                print(
                    f"Page {page_number}: OCR PSM {psm} failed: {exc}"
                )

        if not ocr_results:
            print(f"Page {page_number}: OCR returned no text.")
            return ""

        # Keep the OCR result containing the most text.
        # This is a heuristic, not a guarantee of accuracy.
        best_result = max(
            ocr_results,
            key=lambda text: len(text)
        )

        print(
            f"Page {page_number}: "
            f"OCR extracted {len(best_result)} characters."
        )

        return best_result

    # =====================================================
    # EXTRACT PDF TEXT PAGE BY PAGE
    # =====================================================

    def extract_pdf_pages(self, file_path: str):

        documents = []
        page_text_map = {}

        try:
            pdf = fitz.open(file_path)

        except Exception as exc:
            raise ValueError(
                f"Could not open PDF: {exc}"
            ) from exc

        try:
            if pdf.page_count == 0:
                raise ValueError("The PDF contains no pages.")

            for page_index, page in enumerate(pdf):
                page_number = page_index + 1

                # Step 1: Extract selectable PDF text.
                extracted_text = page.get_text("text").strip()

                # Step 2: Detect whether the page contains images.
                # Scanned documents often have little selectable text.
                has_images = bool(page.get_images(full=True))

                # Step 3: Decide whether OCR is needed.
                should_run_ocr = (
                    len(extracted_text) < 100
                    or has_images
                )

                final_text = extracted_text

                if should_run_ocr:
                    ocr_text = self.run_ocr(
                        page,
                        page_number
                    )

                    # Keep the OCR result when it appears more
                    # informative. Avoid blindly duplicating both
                    # complete page texts.
                    if ocr_text:
                        if (
                            not extracted_text
                            or len(ocr_text) > len(extracted_text) * 1.15
                        ):
                            final_text = ocr_text

                # Step 4: Normalize whitespace without removing
                # useful line breaks from tables.
                final_text = final_text.replace("\x00", "")
                final_text = re.sub(
                    r"[ \t]+",
                    " ",
                    final_text
                )
                final_text = re.sub(
                    r"\n{3,}",
                    "\n\n",
                    final_text
                ).strip()

                page_text_map[page_number] = final_text

                if final_text:
                    documents.append(
                        Document(
                            page_content=final_text,
                            metadata={
                                "source": str(Path(file_path).resolve()),
                                "page": page_number,
                                "page_number": page_number,
                                "page_numbering": "pdf_page_index_1_based"
                            }
                        )
                    )

                print(
                    f"Page {page_number}/{pdf.page_count}: "
                    f"{len(final_text)} characters; "
                    f"images={has_images}"
                )

        finally:
            pdf.close()

        if not documents:
            raise ValueError(
                "No readable text was extracted. "
                "The PDF may be blank, damaged, or difficult to OCR."
            )

        return documents, page_text_map

    # =====================================================
    # PROCESS PDF AND CREATE VECTOR STORE
    # =====================================================

    def process_pdf(self, file_path: str):

        document_id = str(uuid.uuid4())
        resolved_path = str(Path(file_path).resolve())

        print(f"Processing temporary PDF: {resolved_path}")

        try:
            documents, page_text_map = self.extract_pdf_pages(
                resolved_path
            )

            # Smaller chunks can improve retrieval of individual
            # table rows and short factual statements.
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=700,
                chunk_overlap=120,
                separators=[
                    "\n\n",
                    "\n",
                    "।",
                    ". ",
                    " ",
                    ""
                ],
                add_start_index=True
            )

            # split_documents() copies each page Document's metadata into
            # every chunk created from that page. Keep page metadata explicit
            # so retrieval and citations can reliably identify the PDF page.
            chunks = splitter.split_documents(documents)

            if not chunks:
                raise ValueError(
                    "No usable text chunks were created."
                )

            for chunk in chunks:
                chunk.metadata["document_id"] = document_id
                # `page` is the 1-based PDF page number, assigned during
                # extract_pdf_pages(). Keep `page_number` as a clear alias.
                page_value = chunk.metadata.get(
                    "page",
                    chunk.metadata.get("page_number")
                )
                if page_value is not None:
                    page_value = int(page_value)
                    chunk.metadata["page"] = page_value
                    chunk.metadata["page_number"] = page_value
                chunk.metadata["source"] = str(
                    chunk.metadata.get("source", resolved_path)
                )

            # Log page -> chunk counts so metadata can be checked in backend logs.
            chunks_per_page = {}
            for chunk in chunks:
                page_value = chunk.metadata.get("page")
                chunks_per_page[page_value] = (
                    chunks_per_page.get(page_value, 0) + 1
                )
            print("Chunk metadata summary (PDF page -> chunks):", chunks_per_page)

            vectorstore = FAISS.from_documents(
                chunks,
                self.embeddings
            )

            # Register the document only after successful indexing.
            self.vectorstores[document_id] = vectorstore
            self.files[document_id] = resolved_path
            self.page_texts[document_id] = page_text_map
            self.document_chunks[document_id] = chunks

            total_pages = len(page_text_map)
            pages_with_text = sum(
                1
                for text in page_text_map.values()
                if text.strip()
            )

            chunks_per_page = {}
            for chunk in chunks:
                page_value = chunk.metadata.get("page")
                if page_value is not None:
                    chunks_per_page[str(page_value)] = (
                        chunks_per_page.get(str(page_value), 0) + 1
                    )

            return {
                "document_id": document_id,
                "filename": Path(resolved_path).name,
                "pages": total_pages,
                "pages_with_text": pages_with_text,
                "chunks": len(chunks),
                "chunks_per_page": chunks_per_page
            }

        except Exception:
            # Do not leave partial in-memory entries after failure.
            self.vectorstores.pop(document_id, None)
            self.files.pop(document_id, None)
            self.page_texts.pop(document_id, None)
            self.document_chunks.pop(document_id, None)
            raise

    # =====================================================
    # DETECT EXPLICIT PDF PAGE REQUESTS
    # =====================================================

    @staticmethod
    def get_requested_page(question: str) -> Optional[int]:
        """
        Recognize explicit references such as:
        'PDF page 8', 'page number 8', or 'पेज 8'.
        """

        patterns = [
            r"\b(?:pdf\s+)?page\s*(?:number\s*)?[:#-]?\s*(\d+)\b",
            r"\bp\.?\s*(\d+)\b",
            r"पृष्ठ\s*(\d+)",
            r"पेज\s*(\d+)"
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                question,
                flags=re.IGNORECASE
            )

            if match:
                return int(match.group(1))

        return None

    # =====================================================
    # LIGHTWEIGHT LEXICAL RERANKING
    # =====================================================

    @staticmethod
    def lexical_score(question: str, text: str) -> float:
        """
        Score query-term overlap.

        This is a simple reranking signal, not a replacement
        for semantic retrieval.
        """

        stop_words = {
            "the", "is", "are", "was", "were", "what",
            "which", "where", "when", "who", "how", "for",
            "from", "this", "that", "with", "and", "in",
            "of", "to", "a", "an", "me", "tell", "please",
            "hai", "he", "ka", "ki", "ke", "kya", "mein",
            "par", "se", "aur", "bataye", "batao"
        }

        question_terms = {
            term.lower()
            for term in re.findall(
                r"[A-Za-z0-9]+|[\u0900-\u097F]+",
                question
            )
            if len(term) > 1 and term.lower() not in stop_words
        }

        if not question_terms:
            return 0.0

        text_terms = {
            term.lower()
            for term in re.findall(
                r"[A-Za-z0-9]+|[\u0900-\u097F]+",
                text
            )
        }

        matched_terms = question_terms.intersection(text_terms)

        return len(matched_terms) / len(question_terms)

    # =====================================================
    # RETRIEVE RELEVANT DOCUMENT CHUNKS
    # =====================================================

    def retrieve_chunks(
        self,
        document_id: str,
        question: str,
        k: int = 8
    ) -> List[Document]:

        chunks = self.document_chunks[document_id]
        vectorstore = self.vectorstores[document_id]

        requested_page = self.get_requested_page(question)

        # If a page is explicitly requested, focus on that PDF
        # page rather than returning unrelated pages.
        if requested_page is not None:
            page_chunks = [
                chunk for chunk in chunks
                if chunk.metadata.get("page") == requested_page
            ]

            if not page_chunks:
                print(
                    f"Requested PDF page {requested_page} "
                    "has no extracted text chunks."
                )
                return []

            # A page-specific request is constrained to that page.
            # Return its relevant chunks instead of unrelated pages.
            if len(page_chunks) <= k:
                return page_chunks

            page_store = FAISS.from_documents(
                page_chunks,
                self.embeddings
            )

            candidates = page_store.similarity_search_with_score(
                question,
                k=min(15, len(page_chunks))
            )

        else:
            candidates = vectorstore.similarity_search_with_score(
                question,
                k=min(15, len(chunks))
            )

        # Lower FAISS distance means a better semantic match.
        # Combine vector rank with lexical overlap.
        ranked = []

        for rank, (document, distance) in enumerate(candidates):
            lexical = self.lexical_score(
                question,
                document.page_content
            )

            semantic_rank_score = 1.0 / (60 + rank + 1)

            combined_score = (
                0.65 * semantic_rank_score
                + 0.35 * lexical
            )

            ranked.append(
                (combined_score, document, float(distance))
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True
        )

        selected = [
            document
            for _, document, _ in ranked[:k]
        ]

        return selected

    # =====================================================
    # ASK QUESTION ABOUT THE UPLOADED PDF
    # =====================================================

    def ask(self, document_id: str, question: str):

        if document_id not in self.vectorstores:
            raise ValueError(
                "PDF session not found or expired. "
                "Please upload the PDF again."
            )

        documents = self.retrieve_chunks(
            document_id=document_id,
            question=question,
            k=8
        )

        if not documents:
            requested_page = self.get_requested_page(question)

            if requested_page is not None:
                message = (
                    f"No readable text was extracted from PDF page "
                    f"{requested_page}, or that page does not exist. "
                    "Please verify the page or try a clearer PDF."
                )
            else:
                message = (
                    "The extracted text does not provide enough "
                    "information to answer this question reliably."
                )

            return {
                "answer": message,
                "sources": []
            }

        context_parts = []
        sources = []

        for document in documents:
            page = document.metadata.get("page")

            if page is not None:
                context_parts.append(
                    f"[PDF page {page}]\n"
                    f"{document.page_content}"
                )

                source = {"page": int(page)}

                if source not in sources:
                    sources.append(source)

        if not context_parts:
            return {
                "answer": (
                    "No readable source text was found "
                    "for this question."
                ),
                "sources": []
            }

        context = "\n\n---\n\n".join(context_parts)

        messages = self.prompt.format_messages(
            question=question,
            context=context
        )

        response = self.llm.invoke(messages)

        answer = response.content

        if not isinstance(answer, str):
            answer = str(answer)

        return {
            "answer": answer,
            "sources": sources
        }

    # =====================================================
    # DELETE TEMPORARY DOCUMENT
    # =====================================================

    def delete_document(self, document_id: str):

        existed = document_id in self.vectorstores

        self.vectorstores.pop(document_id, None)
        self.page_texts.pop(document_id, None)
        self.document_chunks.pop(document_id, None)

        file_path = self.files.pop(document_id, None)
        file_deleted = False

        if file_path:
            try:
                path = Path(file_path)

                if path.is_file():
                    path.unlink()

                file_deleted = not path.exists()

            except OSError as exc:
                print(
                    f"Temporary PDF deletion warning: {exc}"
                )

        return {
            "document_id": document_id,
            "deleted": existed,
            "file_deleted": file_deleted
        }
