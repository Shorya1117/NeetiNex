import hashlib
import json
from pathlib import Path

# ============================================================
# BASE DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "cleaned"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "deduplicated"
)

REPORT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "quality_reports"
)

# ============================================================
# CONTENT HASH
# ============================================================

def create_content_hash(data):
    """
    Create a SHA-256 hash from the actual scheme content.

    Metadata such as source_file and source_path are excluded
    because two files can contain the same scheme content
    while having different filenames or paths.
    """
    content = {
        "scheme_name": data.get("scheme_name"),
        "scheme_id": data.get("scheme_id"),
        "department": data.get("department"),
        "eligibility_rules": data.get("eligibility_rules", []),
        "documents_required": data.get("documents_required", []),
        "application_process": data.get("application_process", []),
        "source_url": data.get("source_url"),
    }

    # Convert to deterministic JSON.
    serialized = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True
    )

    # Create SHA-256 hash.
    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # Create output directories
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find cleaned JSON files
    # --------------------------------------------------------

    json_files = sorted(INPUT_DIR.glob("*.json"))

    print(f"Found {len(json_files)} cleaned JSON files.")

    # --------------------------------------------------------
    # Track hashes
    # --------------------------------------------------------

    seen_hashes = {}

    unique_count = 0
    duplicate_count = 0
    failed_count = 0

    duplicates = []

    # ========================================================
    # PROCESS EACH FILE
    # ========================================================

    for json_file in json_files:
        try:
            # ------------------------------------------------
            # Read JSON
            # ------------------------------------------------

            with json_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            # ------------------------------------------------
            # Create content hash
            # ------------------------------------------------

            content_hash = create_content_hash(data)

            # =================================================
            # CHECK DUPLICATE
            # =================================================

            if content_hash in seen_hashes:
                original_file = seen_hashes[content_hash]

                duplicate_count += 1

                duplicates.append(
                    {
                        "duplicate_file": json_file.name,
                        "original_file": original_file,
                        "content_hash": content_hash,
                        "scheme_name": data.get("scheme_name"),
                        "scheme_id": data.get("scheme_id"),
                    }
                )

                print(f"[DUPLICATE] {json_file.name}")
                print(f"            Same as: {original_file}")

                continue

            # =================================================
            # UNIQUE FILE
            # =================================================

            seen_hashes[content_hash] = json_file.name

            # ------------------------------------------------
            # Save unique record
            # ------------------------------------------------

            output_file = OUTPUT_DIR / json_file.name

            output_file.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )

            unique_count += 1

            print(f"[UNIQUE] {json_file.name}")

        except Exception as exc:
            failed_count += 1

            print(f"[ERROR] {json_file.name}")
            print(f"        {exc}")

    # ========================================================
    # CREATE REPORT
    # ========================================================

    report = {
        "summary": {
            "input_files": len(json_files),
            "unique_files": unique_count,
            "duplicate_files": duplicate_count,
            "failed_files": failed_count,
        },
        "duplicates": duplicates,
    }

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    report_file = REPORT_DIR / "deduplication_report.json"

    report_file.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 50)
    print("Deduplication completed.")
    print("=" * 50)
    print(f"Input files     : {len(json_files)}")
    print(f"Unique files    : {unique_count}")
    print(f"Duplicate files : {duplicate_count}")
    print(f"Failed files    : {failed_count}")
    print("=" * 50)
    print()
    print("Deduplicated files saved to:")
    print(OUTPUT_DIR)
    print()
    print("Report saved to:")
    print(report_file)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()