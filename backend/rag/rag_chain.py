import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from backend.rag.retriever import NeetiNexRetriever
from backend.rag.reranker import NeetiNexReranker


load_dotenv()


class NeetiNexRAG:

    def __init__(self):

        print("======================================")
        print("Initializing NeetiNex RAG")
        print("======================================")

        self.retriever = NeetiNexRetriever()
        self.reranker = NeetiNexReranker()

        # Groq + Llama
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are NeetiNex, an AI assistant for Indian Government Schemes.

Answer the user's question ONLY using the government scheme context provided below.

STRICT RULES:

1. Do not invent government scheme information.
2. Do not use outside knowledge.
3. If the context does not contain the answer, clearly say that the available scheme information does not contain the answer.
4. Keep the answer simple and clear.
5. Mention the scheme name when available.
6. Use only information supported by the context.
7. Do not make an eligibility decision based on assumptions.
8. Include the official source when it is available.

LANGUAGE MATCHING & DUAL RESPONSE RULES:
- Automatically detect the language or instruction requested by the user or prompt wrapper.
- If the user asks in Hinglish or asks for Hinglish (e.g., "palanhar yojana ke bare mein batao"), respond strictly in clear, natural Hinglish (Roman script Hindi) using ONLY the context.
- If the user asks in Hindi or Hindi Devanagari script (e.g., "पालनहार योजना के बारे में बताएं"), respond in Hindi (Devanagari).
- If the instruction specifies "Both (English + Hindi)", provide the response first in English, followed by an equivalent Hindi (Devanagari) translation of the retrieved facts.
- Do NOT add facts during translation—translate ONLY what is verified by the context.

GOVERNMENT SCHEME CONTEXT:
{context}
"""
                ),
                (
                    "human",
                    "{question}"
                )
            ]
        )

        print("RAG initialized successfully.")

    def ask(self, question):

        # 1. Retrieve
        documents = self.retriever.retrieve(
            question,
            n_results=5
        )

        if not documents:
            return {
                "answer": (
                    "I could not find relevant "
                    "government scheme information "
                    "for this question."
                ),
                "sources": []
            }

        # 2. Rerank
        ranked_documents = self.reranker.rerank(
            question,
            documents,
            top_k=3
        )

        # 3. Build context
        context_parts = []
        sources = []

        for document in ranked_documents:

            context_parts.append(
                document.page_content
            )

            source_url = document.metadata.get(
                "source_url"
            )

            if source_url and source_url not in sources:
                sources.append(source_url)

        context = "\n\n---\n\n".join(
            context_parts
        )

        # 4. Create LangChain prompt
        messages = self.prompt.format_messages(
            question=question,
            context=context
        )

        # 5. Generate answer with Groq
        response = self.llm.invoke(messages)

        return {
            "answer": response.content,
            "sources": sources,
            "documents": ranked_documents
        }