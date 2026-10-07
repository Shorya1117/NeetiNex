from sentence_transformers import CrossEncoder


RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class NeetiNexReranker:

    def __init__(self):
        print("Loading reranker model...")

        self.model = CrossEncoder(
            RERANKER_MODEL
        )

        print("Reranker loaded.")

    def rerank(
        self,
        query,
        documents,
        top_k=3
    ):
        """
        Rank documents according to their
        relevance to the user query.
        """

        if not documents:
            return []

        pairs = []

        for document in documents:

            pairs.append(
                (
                    query,
                    document.page_content
                )
            )

        scores = self.model.predict(
            pairs
        )

        ranked_documents = sorted(
            zip(documents, scores),
            key=lambda x: float(x[1]),
            reverse=True
        )

        results = []

        for document, score in ranked_documents[:top_k]:

            document.metadata[
                "rerank_score"
            ] = float(score)

            results.append(document)

        return results
        