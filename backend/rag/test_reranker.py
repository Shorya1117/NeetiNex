from retriever import NeetiNexRetriever
from reranker import NeetiNexReranker


def test_query(
    retriever,
    reranker,
    query
):

    print("\n======================================")
    print("QUERY")
    print("======================================")

    print(query)

    # Retrieve scheme-specific chunks
    documents = retriever.retrieve(
        query,
        n_results=5
    )

    print("\nBefore reranking:")

    for i, document in enumerate(
        documents,
        start=1
    ):

        print(
            f"{i}. "
            f"{document.metadata.get('section')}"
        )

    # Rerank
    ranked_documents = reranker.rerank(
        query,
        documents,
        top_k=3
    )

    print("\nAfter reranking:")

    for i, document in enumerate(
        ranked_documents,
        start=1
    ):

        print(
            f"{i}. "
            f"{document.metadata.get('section')} "
            f"| score="
            f"{document.metadata.get('rerank_score'):.4f}"
        )


def main():

    print("======================================")
    print("NeetiNex Reranker Test")
    print("======================================")

    retriever = NeetiNexRetriever()

    reranker = NeetiNexReranker()

    queries = [

        "Aapki Beti Yojana mein kaun eligible hai?",

        "Aapki Beti Yojana ke documents kya hain?",

        "How can I apply for Aapki Beti Yojana?"

    ]

    for query in queries:

        test_query(
            retriever,
            reranker,
            query
        )


if __name__ == "__main__":
    main()