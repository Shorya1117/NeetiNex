import json
import re
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
    / "extracted"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "cleaned"
)

# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    """
    Clean formatting noise from extracted text.

    IMPORTANT:
    This function does not correct spelling,
    grammar, facts, or government wording.
    """
    if not isinstance(text, str):
        return text

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    text = re.sub(r"\s+", " ", text)

    # --------------------------------------------------------
    # Remove numbering at the beginning
    #
    # Examples:
    # 1. Text
    # 2) Text
    # 3 - Text
    # --------------------------------------------------------

    text = re.sub(r"^\s*\d+\s*[\.\)\-:]\s*", "", text)

    # --------------------------------------------------------
    # Remove Roman numeral numbering
    #
    # Examples:
    # (i) Text
    # (ii) Text
    # (iii) Text
    # --------------------------------------------------------

    text = re.sub(
        r"^\s*\([ivxlcdm]+\)\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Remove leading/trailing whitespace
    # --------------------------------------------------------

    text = text.strip()

    return text

# ============================================================
# CLEAN LIST
# ============================================================

def clean_list(items):
    """
    Clean a list of extracted text values.
    """
    if not isinstance(items, list):
        return items

    cleaned_items = []

    for item in items:
        cleaned = clean_text(item)

        # Ignore empty values.
        if not cleaned:
            continue

        cleaned_items.append(cleaned)

    return cleaned_items

# ============================================================
# CLEAN ONE JSON RECORD
# ============================================================

def clean_record(data):
    """
    Clean one extracted scheme record.

    Metadata is preserved.
    Only text fields are cleaned.
    """
    cleaned_data = data.copy()

    # --------------------------------------------------------
    # Scheme name
    # --------------------------------------------------------

    if isinstance(cleaned_data.get("scheme_name"), str):
        cleaned_data["scheme_name"] = clean_text(
            cleaned_data["scheme_name"]
        )

    # --------------------------------------------------------
    # Department
    #
    # We only normalize whitespace.
    # We do NOT correct spelling.
    # --------------------------------------------------------

    if isinstance(cleaned_data.get("department"), str):
        cleaned_data["department"] = re.sub(
            r"\s+",
            " ",
            cleaned_data["department"]
        ).strip()

    # --------------------------------------------------------
    # Eligibility rules
    # --------------------------------------------------------

    cleaned_data["eligibility_rules"] = clean_list(
        cleaned_data.get("eligibility_rules", [])
    )

    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------

    cleaned_data["documents_required"] = clean_list(
        cleaned_data.get("documents_required", [])
    )

    # --------------------------------------------------------
    # Application process
    # --------------------------------------------------------

    cleaned_data["application_process"] = clean_list(
        cleaned_data.get("application_process", [])
    )

    # --------------------------------------------------------
    # Source URL
    #
    # Do not modify it unnecessarily.
    # --------------------------------------------------------

    if isinstance(cleaned_data.get("source_url"), str):
        cleaned_data["source_url"] = cleaned_data["source_url"].strip()

    return cleaned_data

# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find extracted JSON files
    # --------------------------------------------------------

    json_files = list(INPUT_DIR.glob("*.json"))

    print(f"Found {len(json_files)} extracted JSON files.")

    cleaned_count = 0
    failed_count = 0

    # ========================================================
    # PROCESS FILES
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
            # Clean record
            # ------------------------------------------------

            cleaned_data = clean_record(data)

            # ------------------------------------------------
            # Output path
            # ------------------------------------------------

            output_file = OUTPUT_DIR / json_file.name

            # ------------------------------------------------
            # Save cleaned JSON
            # ------------------------------------------------

            output_file.write_text(
                json.dumps(
                    cleaned_data,
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )

            cleaned_count += 1

            print(f"[CLEANED] {json_file.name}")

        except Exception as exc:
            failed_count += 1

            print(f"[ERROR] {json_file.name}")
            print(f"        {exc}")

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 50)
    print("Cleaning completed.")
    print("=" * 50)
    print(f"Input files  : {len(json_files)}")
    print(f"Cleaned      : {cleaned_count}")
    print(f"Failed       : {failed_count}")
    print("=" * 50)
    print()
    print("Cleaned files saved to:")
    print(OUTPUT_DIR)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()