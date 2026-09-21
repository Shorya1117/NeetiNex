import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "jansoochna"
    / "eligibility"
    / "html"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "jansoochna"
    / "eligibility"
    / "extracted"
)


def clean_inline_text(text):
    """
    Normalize basic whitespace in extracted text.

    This function does NOT correct spelling,
    grammar, or government-source wording.
    """

    if not text:
        return ""

    return " ".join(text.split()).strip()


def normalize_for_matching(text):
    """
    Normalize text only for comparing a filename
    with a scheme name.

    This does not modify the actual stored value.
    """

    if not text:
        return ""

    text = text.lower()

    # Replace separators with spaces.
    text = re.sub(r"[_\-]+", " ", text)

    # Remove non-alphanumeric characters.
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_scheme_name(soup, html_file):
    """
    Identify the scheme represented by the HTML file.

    Jan Soochna pages can contain multiple schemes in
    the Scheme_Id dropdown. Therefore, we cannot simply
    take the first option.

    The filename is used as a matching signal.

    Returns:
        scheme_name
        scheme_id
        scheme_match_method
        scheme_match_score
    """

    scheme_select = soup.find(
        "select",
        {"id": "Scheme_Id"}
    )

    if not scheme_select:

        return {
            "scheme_name": None,
            "scheme_id": None,
            "scheme_match_method": "scheme_select_not_found",
            "scheme_match_score": 0.0,
        }

    options = scheme_select.find_all("option")

    filename_stem = html_file.stem

    normalized_filename = normalize_for_matching(
        filename_stem
    )

    candidates = []

    for option in options:

        value = option.get("value")

        if not value:
            continue

        scheme_name = clean_inline_text(
            option.get_text(
                " ",
                strip=True
            )
        )

        if not scheme_name:
            continue

        # Ignore placeholder option.
        if scheme_name.lower().startswith("choose"):
            continue

        normalized_scheme = normalize_for_matching(
            scheme_name
        )

        if not normalized_scheme:
            continue

        score = SequenceMatcher(
            None,
            normalized_filename,
            normalized_scheme
        ).ratio()

        candidates.append(
            {
                "scheme_name": scheme_name,
                "scheme_id": value,
                "score": score,
            }
        )

    if not candidates:

        return {
            "scheme_name": None,
            "scheme_id": None,
            "scheme_match_method": "no_scheme_candidates",
            "scheme_match_score": 0.0,
        }

    # Highest similarity first.
    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    best = candidates[0]

    # Strong match.
    if best["score"] >= 0.70:

        return {
            "scheme_name": best["scheme_name"],
            "scheme_id": best["scheme_id"],
            "scheme_match_method": "filename_match",
            "scheme_match_score": round(
                best["score"],
                4
            ),
        }

    # Weak match.
    # Do not guess the scheme.
    return {
        "scheme_name": None,
        "scheme_id": None,
        "scheme_match_method": "no_reliable_match",
        "scheme_match_score": round(
            best["score"],
            4
        ),
    }


def extract_eligibility_rules(section):
    """
    Extract eligibility rules from TblRules.
    """

    table = section.find(
        "table",
        {"id": "TblRules"}
    )

    if not table:
        return []

    tbody = table.find("tbody")

    if not tbody:
        return []

    rules = []

    for row in tbody.find_all("tr"):

        cells = row.find_all("td")

        if len(cells) < 2:
            continue

        content_cell = cells[1]

        # Jan Soochna generally uses <li> for rules.
        list_items = content_cell.find_all("li")

        if list_items:

            for item in list_items:

                text = clean_inline_text(
                    item.get_text(
                        " ",
                        strip=True
                    )
                )

                if text:
                    rules.append(text)

        else:

            # Fallback if <li> tags are not present.
            text = clean_inline_text(
                content_cell.get_text(
                    " ",
                    strip=True
                )
            )

            if text:
                rules.append(text)

    return rules


def extract_documents(section):
    """
    Extract required documents from TblDocuments.
    """

    table = section.find(
        "table",
        {"id": "TblDocuments"}
    )

    if not table:
        return []

    tbody = table.find("tbody")

    if not tbody:
        return []

    documents = []

    for row in tbody.find_all("tr"):

        cells = row.find_all("td")

        if len(cells) < 2:
            continue

        content_cell = cells[1]

        # get_text with newline helps preserve <br> separation.
        text = content_cell.get_text(
            "\n",
            strip=True
        )

        for line in text.split("\n"):

            line = clean_inline_text(line)

            if line:
                documents.append(line)

    return documents


def extract_application_process(section):
    """
    Extract application procedure.

    The Jan Soochna page uses the same table id
    'TblProcess' for both:
        1. Application process
        2. Scheme URL

    Therefore, the first TblProcess table is treated
    as the application-process table.
    """

    tables = section.find_all(
        "table",
        {"id": "TblProcess"}
    )

    if not tables:
        return []

    process_table = tables[0]

    tbody = process_table.find("tbody")

    if not tbody:
        return []

    process = []

    for row in tbody.find_all("tr"):

        cells = row.find_all("td")

        if len(cells) < 2:
            continue

        text = clean_inline_text(
            cells[1].get_text(
                " ",
                strip=True
            )
        )

        if text:
            process.append(text)

    return process


def extract_scheme_url(section):
    """
    Extract the official scheme URL.

    The URL section uses the second TblProcess table.
    First preference is the actual href attribute.
    """

    tables = section.find_all(
        "table",
        {"id": "TblProcess"}
    )

    if len(tables) < 2:
        return None

    url_table = tables[-1]

    # First try actual href values.
    for link in url_table.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        ).strip()

        if (
            href.startswith("http://")
            or href.startswith("https://")
        ):

            return href

    # Fallback: inspect visible text.
    text = url_table.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"https?://[^\s<>\"']+",
        text
    )

    if match:

        return match.group(0).rstrip(
            ".,);"
        )

    return None


def extract_html_file(html_file):
    """
    Extract structured information from one HTML file.
    """

    html = html_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # We only want the actual eligibility content.
    section = soup.select_one(
        "section.eligiblityrules"
    )

    if not section:

        return None

    # Department comes from crawler directory structure.
    department = html_file.parent.name

    scheme_info = extract_scheme_name(
        soup,
        html_file
    )

    eligibility_rules = (
        extract_eligibility_rules(section)
    )

    documents = extract_documents(
        section
    )

    application_process = (
        extract_application_process(section)
    )

    scheme_url = extract_scheme_url(
        section
    )

    result = {
        "scheme_name": scheme_info[
            "scheme_name"
        ],

        "scheme_id": scheme_info[
            "scheme_id"
        ],

        "scheme_match_method": scheme_info[
            "scheme_match_method"
        ],

        "scheme_match_score": scheme_info[
            "scheme_match_score"
        ],

        "department": department,

        "source_type": "jansoochna_eligibility",

        "source_file": html_file.name,

        "source_path": str(
            html_file.relative_to(
                BASE_DIR
            )
        ),

        "source_url": scheme_url,

        "eligibility_rules": (
            eligibility_rules
        ),

        "documents_required": (
            documents
        ),

        "application_process": (
            application_process
        ),
    }

    return result


def main():
    """
    Process all HTML files recursively.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    html_files = list(
        RAW_DIR.rglob("*.html")
    )

    print(
        f"Found {len(html_files)} HTML files."
    )

    successful = 0
    skipped = 0
    failed = 0

    for html_file in html_files:

        try:

            data = extract_html_file(
                html_file
            )

            if data is None:

                print(
                    f"[SKIPPED] "
                    f"{html_file.name} "
                    f"- eligibility section not found"
                )

                skipped += 1

                continue

            output_file = (
                OUTPUT_DIR
                / f"{html_file.stem}.json"
            )

            output_file.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )

            successful += 1

            print(
                f"[OK] {html_file.name}"
            )

        except Exception as exc:

            failed += 1

            print(
                f"[ERROR] {html_file.name}"
            )

            print(
                f"        {exc}"
            )

    print()
    print("=" * 50)
    print("Extraction completed.")
    print("=" * 50)
    print(
        f"Total HTML files : {len(html_files)}"
    )
    print(
        f"Successful       : {successful}"
    )
    print(
        f"Skipped          : {skipped}"
    )
    print(
        f"Failed           : {failed}"
    )
    print("=" * 50)


if __name__ == "__main__":
    main()