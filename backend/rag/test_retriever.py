from retriever import NeetiNexRetriever


def main():

    print("======================================")
    print("NeetiNex Retrieval Test")
    print("======================================")

    retriever = NeetiNexRetriever()

    queries = [
        "Aapki Beti Yojana mein kaun eligible hai?",
        "Who is eligible for Aapki Beti Yojana?",
        "Aapki Beti Yojana ke documents kya hain?",
        "Tell me about Aapki Beti Yojana",
    ]

    for query in queries:

        documents = retriever.retrieve(
            query,
            n_results=5
        )

        print("\n======================================")
        print("FINAL RETRIEVED DOCUMENTS")
        print("======================================")

        for i, document in enumerate(
            documents,
            start=1
        ):

            print(
                f"\n--- Result {i} ---"
            )

            print(
                "Scheme:",
                document.metadata.get(
                    "scheme_name"
                )
            )

            print(
                "Section:",
                document.metadata.get(
                    "section"
                )
            )

            print("\nContent:")
            print(
                document.page_content
            )

            print(
                "\nSource:",
                document.metadata.get(
                    "source_url"
                )
            )


if __name__ == "__main__":
    main()