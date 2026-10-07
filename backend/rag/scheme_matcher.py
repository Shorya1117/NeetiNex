import re
from difflib import SequenceMatcher


class SchemeMatcher:

    def __init__(self, collection):
        self.collection = collection

        self.scheme_names = self._load_scheme_names()

        print(
            f"Loaded {len(self.scheme_names)} unique schemes."
        )

    def _load_scheme_names(self):
        """
        Load all unique scheme names from Chroma metadata.
        """

        results = self.collection.get(
            include=["metadatas"]
        )

        scheme_names = set()

        for metadata in results["metadatas"]:
            scheme_name = metadata.get("scheme_name")

            if scheme_name:
                scheme_names.add(scheme_name)

        return sorted(scheme_names)

    def normalize(self, text):
        """
        Normalize text for comparison.
        """

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def find_scheme(self, query):
        """
        Find the most likely scheme mentioned
        in the user query.
        """

        normalized_query = self.normalize(query)

        # -----------------------------------------
        # 1. Exact / substring match
        # -----------------------------------------

        for scheme in self.scheme_names:

            normalized_scheme = self.normalize(
                scheme
            )

            if normalized_scheme in normalized_query:
                return scheme

        # -----------------------------------------
        # 2. Fuzzy matching
        # -----------------------------------------

        best_scheme = None
        best_score = 0

        for scheme in self.scheme_names:

            normalized_scheme = self.normalize(
                scheme
            )

            score = SequenceMatcher(
                None,
                normalized_scheme,
                normalized_query
            ).ratio()

            if score > best_score:
                best_score = score
                best_scheme = scheme

        # -----------------------------------------
        # Confidence threshold
        # -----------------------------------------

        if best_score >= 0.55:
            return best_scheme

        return None