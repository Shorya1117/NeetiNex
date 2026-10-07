from retriever import NeetiNexRetriever
from scheme_matcher import SchemeMatcher


def main():

    print("======================================")
    print("NeetiNex Scheme Matcher Test")
    print("======================================")

    retriever = NeetiNexRetriever()

    matcher = SchemeMatcher(
        retriever.collection
    )

    queries = [
        "Aapki Beti Yojana mein kaun eligible hai?",
        "Who is eligible for Aapki Beti Yojana?",
        "aapki beti yojana",
        "Aapki Beti scheme",
        "Tell me about Aapki Beti Yojana",
    ]

    for query in queries:

        print("\n--------------------------------------")
        print("Query:")
        print(query)

        scheme = matcher.find_scheme(query)

        print("\nDetected scheme:")
        print(scheme)


if __name__ == "__main__":
    main()