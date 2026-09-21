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
    / "extracted"
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
# VALIDATION HELPERS
# ============================================================

def add_warning(warnings, message):
    """
    Add a warning message to the warning list.
    """

    warnings.append(message)


# ============================================================
# VALIDATE ONE JSON RECORD
# ============================================================

def validate_record(data):
    """
    Validate one extracted scheme JSON record.

    This function DOES NOT modify the data.
    It only checks whether important information
    is present and whether anything looks suspicious.
    """

    warnings = []
    errors = []

    # --------------------------------------------------------
    # Basic metadata
    # --------------------------------------------------------

    scheme_name = data.get("scheme_name")
    scheme_id = data.get("scheme_id")
    department = data.get("department")
    source_file = data.get("source_file")
    source_url = data.get("source_url")

    # --------------------------------------------------------
    # Extracted content
    # --------------------------------------------------------

    eligibility_rules = data.get(
        "eligibility_rules",
        []
    )

    documents_required = data.get(
        "documents_required",
        []
    )

    application_process = data.get(
        "application_process",
        []
    )

    # --------------------------------------------------------
    # Scheme matching information
    # --------------------------------------------------------

    match_method = data.get(
        "scheme_match_method"
    )

    match_score = data.get(
        "scheme_match_score"
    )

    # ========================================================
    # REQUIRED METADATA CHECKS
    # ========================================================

    if not scheme_name:
        add_warning(
            warnings,
            "Missing scheme_name"
        )

    if not scheme_id:
        add_warning(
            warnings,
            "Missing scheme_id"
        )

    if not department:
        add_warning(
            warnings,
            "Missing department"
        )

    if not source_file:
        add_warning(
            warnings,
            "Missing source_file"
        )

    if not source_url:
        add_warning(
            warnings,
            "Missing source_url"
        )

    # ========================================================
    # SCHEME MATCH CHECK
    # ========================================================

    if match_method == "no_reliable_match":

        add_warning(
            warnings,
            "Scheme name could not be reliably matched to filename"
        )

    elif match_method == "scheme_select_not_found":

        add_warning(
            warnings,
            "Scheme dropdown was not found"
        )

    elif match_method == "no_scheme_candidates":

        add_warning(
            warnings,
            "No scheme candidates were found"
        )

    # --------------------------------------------------------
    # Low similarity score
    # --------------------------------------------------------

    if isinstance(match_score, (int, float)):

        if match_score < 0.70:

            add_warning(
                warnings,
                f"Low scheme match score: {match_score}"
            )

    # ========================================================
    # ELIGIBILITY RULES CHECK
    # ========================================================

    if not isinstance(
        eligibility_rules,
        list
    ):

        errors.append(
            "eligibility_rules is not a list"
        )

    elif len(eligibility_rules) == 0:

        add_warning(
            warnings,
            "No eligibility rules found"
        )

    # ========================================================
    # DOCUMENTS CHECK
    # ========================================================

    if not isinstance(
        documents_required,
        list
    ):

        errors.append(
            "documents_required is not a list"
        )

    elif len(documents_required) == 0:

        add_warning(
            warnings,
            "No documents required information found"
        )

    # ========================================================
    # APPLICATION PROCESS CHECK
    # ========================================================

    if not isinstance(
        application_process,
        list
    ):

        errors.append(
            "application_process is not a list"
        )

    elif len(application_process) == 0:

        add_warning(
            warnings,
            "No application process information found"
        )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    if errors:

        status = "ERROR"

    elif warnings:

        status = "WARNING"

    else:

        status = "VALID"

    return {
        "status": status,
        "warnings": warnings,
        "errors": errors,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Create report directory if it does not exist
    # --------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find extracted JSON files
    # --------------------------------------------------------

    json_files = list(
        INPUT_DIR.glob("*.json")
    )

    print(
        f"Found {len(json_files)} extracted JSON files."
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    valid_count = 0
    warning_count = 0
    error_count = 0

    records = []

    # ========================================================
    # PROCESS EACH JSON FILE
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
            # Validate record
            # ------------------------------------------------

            result = validate_record(
                data
            )

            # ------------------------------------------------
            # Create report record
            # ------------------------------------------------

            record = {

                "file": json_file.name,

                "scheme_name": data.get(
                    "scheme_name"
                ),

                "scheme_id": data.get(
                    "scheme_id"
                ),

                "department": data.get(
                    "department"
                ),

                "source_url": data.get(
                    "source_url"
                ),

                "scheme_match_score": data.get(
                    "scheme_match_score"
                ),

                "status": result[
                    "status"
                ],

                "warnings": result[
                    "warnings"
                ],

                "errors": result[
                    "errors"
                ],
            }

            records.append(
                record
            )

            # =================================================
            # PRINT RESULT
            # =================================================

            if result["status"] == "VALID":

                valid_count += 1

                print(
                    f"[VALID] {json_file.name}"
                )

            elif result["status"] == "WARNING":

                warning_count += 1

                print(
                    f"[WARNING] {json_file.name}"
                )

                for warning in result[
                    "warnings"
                ]:

                    print(
                        f"          - {warning}"
                    )

            else:

                error_count += 1

                print(
                    f"[ERROR] {json_file.name}"
                )

                for error in result[
                    "errors"
                ]:

                    print(
                        f"        - {error}"
                    )

        except Exception as exc:

            # ------------------------------------------------
            # JSON reading/parsing error
            # ------------------------------------------------

            error_count += 1

            print(
                f"[ERROR] {json_file.name}"
            )

            print(
                f"        - Could not read JSON: {exc}"
            )

            records.append(
                {
                    "file": json_file.name,
                    "scheme_name": None,
                    "scheme_id": None,
                    "department": None,
                    "source_url": None,
                    "scheme_match_score": None,
                    "status": "ERROR",
                    "warnings": [],
                    "errors": [
                        f"Could not read JSON: {exc}"
                    ],
                }
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "total_files": len(
            json_files
        ),

        "valid": valid_count,

        "warnings": warning_count,

        "errors": error_count,
    }

    # ========================================================
    # FINAL REPORT
    # ========================================================

    report = {

        "summary": summary,

        "records": records,
    }

    # ========================================================
    # SAVE REPORT
    # ========================================================

    report_file = (
        REPORT_DIR
        / "eligibility_quality_report.json"
    )

    report_file.write_text(

        json.dumps(
            report,
            ensure_ascii=False,
            indent=4
        ),

        encoding="utf-8"
    )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()

    print(
        "=" * 50
    )

    print(
        "Validation completed."
    )

    print(
        "=" * 50
    )

    print(
        f"Total files : {len(json_files)}"
    )

    print(
        f"Valid       : {valid_count}"
    )

    print(
        f"Warnings    : {warning_count}"
    )

    print(
        f"Errors      : {error_count}"
    )

    print(
        "=" * 50
    )

    print()

    print(
        "Report saved to:"
    )

    print(
        report_file
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()