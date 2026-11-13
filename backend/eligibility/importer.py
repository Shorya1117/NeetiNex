"""Import reviewed eligibility data from a JSON file."""
import json
from pathlib import Path
from backend.database.eligibility_db import initialize_database
from backend.database.repositories.eligibility_repository import EligibilityRepository


def import_file(path: str):
    initialize_database()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    repo = EligibilityRepository()
    for scheme in payload.get("schemes", []):
        repo.add_scheme(scheme)
        repo.replace_rules(scheme["scheme_id"], scheme.get("rules", []))
    print(f"Imported {len(payload.get('schemes', []))} scheme records.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    args = parser.parse_args()
    import_file(args.json_file)
