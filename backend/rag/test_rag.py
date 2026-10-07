from rag_chain import NeetiNexRAG


def main():

    print("======================================")
    print("NeetiNex RAG Test")
    print("======================================")

    # Initialize RAG system
    rag = NeetiNexRAG()

    questions = [
        "Aapki Beti Yojana mein kaun eligible hai?",
        "Aapki Beti Yojana ke documents kya hain?",
        "How can I apply for Aapki Beti Yojana?"
    ]

    for question in questions:

        print("\n")
        print("======================================")
        print("QUESTION")
        print("======================================")

        print(question)

        try:

            result = rag.ask(question)

            print("\n")
            print("ANSWER")
            print("--------------------------------------")

            print(result["answer"])

            print("\n")
            print("SOURCES")
            print("--------------------------------------")

            if result["sources"]:

                for source in result["sources"]:
                    print(source)

            else:
                print("No source found.")

        except Exception as e:

            print("\n")
            print("ERROR")
            print("--------------------------------------")

            print(str(e))


if __name__ == "__main__":
    main()