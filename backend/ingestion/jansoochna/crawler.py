import argparse
import hashlib
import json
import re
import time
from base64 import b64decode
from pathlib import Path
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from parser import parse_page


ELIGIBILITY_URL = (
    "https://jansoochna.rajasthan.gov.in/CMS/EligiblityRules"
)

BASE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "jansoochna"
    / "eligibility"
)

HTML_DIR = BASE_DIR / "html"
JSON_DIR = BASE_DIR / "metadata"
SNAPSHOT_DIR = BASE_DIR / "page_snapshots"
PDF_DIR = BASE_DIR / "official_pdfs"

COMMON_PDF_NAMES = {
    "website_policies.pdf",
    "jansoochna_user_manual_updated.pdf",
}


def safe_filename(value):
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value[:150]


def file_hash(content):
    return hashlib.sha256(content).hexdigest()


class JanSoochnaEligibilityCrawler:

    def __init__(self, headless=False):
        self.headless = headless
        
        self.driver = self.create_driver()
        self.wait = WebDriverWait(self.driver, 20)

        HTML_DIR.mkdir(parents=True, exist_ok=True)
        JSON_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        PDF_DIR.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        })

        self.downloaded_urls = {}
        self.downloaded_hashes = {}

    # ========================================================
    # DRIVER
    # ========================================================

    def create_driver(self):

        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--lang=en-US")

        return webdriver.Chrome(options=options)

    # ========================================================
    # OPEN PAGE
    # ========================================================

    def open_page(self):

        print("\nOpening Jan Soochna...")

        self.driver.get(ELIGIBILITY_URL)

        self.wait.until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "select")
            )
        )

        time.sleep(2)

    # ========================================================
    # FIND DEPARTMENT DROPDOWN
    # ========================================================

    def get_department_select(self):

        selects = self.driver.find_elements(
            By.TAG_NAME,
            "select"
        )

        for element in selects:

            try:

                select = Select(element)

                for option in select.options:

                    if (
                        "Choose Eligibility Department"
                        in option.text.strip()
                    ):
                        return element

            except Exception:
                continue

        raise RuntimeError(
            "Department dropdown not found."
        )

    # ========================================================
    # FIND SCHEME DROPDOWN
    # ========================================================

    def get_scheme_select(self):

        selects = self.driver.find_elements(
            By.TAG_NAME,
            "select"
        )

        for element in selects:

            try:

                select = Select(element)

                for option in select.options:

                    if (
                        "Choose Eligibility Scheme"
                        in option.text.strip()
                    ):
                        return element

            except Exception:
                continue

        raise RuntimeError(
            "Scheme dropdown not found."
        )

    # ========================================================
    # GET DEPARTMENTS
    # ========================================================

    def get_departments(self):

        element = self.get_department_select()

        select = Select(element)

        departments = []

        for option in select.options:

            name = option.text.strip()
            value = option.get_attribute("value")

            if not name:
                continue

            if "Choose Eligibility Department" in name:
                continue

            if not value:
                continue

            departments.append({
                "name": name,
                "value": value
            })

        return departments

    # ========================================================
    # GET SCHEMES
    # ========================================================

    def get_schemes(self, department_value):

        department_element = (
            self.get_department_select()
        )

        department_select = Select(
            department_element
        )

        department_select.select_by_value(
            department_value
        )

        time.sleep(2)

        scheme_element = (
            self.get_scheme_select()
        )

        scheme_select = Select(
            scheme_element
        )

        schemes = []

        for option in scheme_select.options:

            name = option.text.strip()
            value = option.get_attribute("value")

            if not name:
                continue

            if "Choose Eligibility Scheme" in name:
                continue

            if not value:
                continue

            schemes.append({
                "name": name,
                "value": value
            })

        return schemes

    # ========================================================
    # SELECT SCHEME
    # ========================================================

    def select_scheme(
        self,
        department_value,
        scheme_value
    ):

        department_element = (
            self.get_department_select()
        )

        Select(
            department_element
        ).select_by_value(
            department_value
        )

        time.sleep(1)

        scheme_element = (
            self.get_scheme_select()
        )

        Select(
            scheme_element
        ).select_by_value(
            scheme_value
        )

        time.sleep(3)

    # ========================================================
    # SAVE HTML
    # ========================================================

    def save_html(
        self,
        department_name,
        scheme_name,
        html
    ):

        folder = (
            HTML_DIR /
            safe_filename(department_name)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        path = (
            folder /
            f"{safe_filename(scheme_name)}.html"
        )

        path.write_text(
            html,
            encoding="utf-8"
        )

        return path

    # ========================================================
    # SAVE JSON
    # ========================================================

    def save_json(
        self,
        department_name,
        scheme_name,
        data
    ):

        folder = (
            JSON_DIR /
            safe_filename(department_name)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        path = (
            folder /
            f"{safe_filename(scheme_name)}.json"
        )

        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return path

    # ========================================================
    # SAVE PAGE SNAPSHOT
    # ========================================================

    def save_snapshot(
        self,
        department_name,
        scheme_name
    ):

        folder = (
            SNAPSHOT_DIR /
            safe_filename(department_name)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        path = (
            folder /
            f"{safe_filename(scheme_name)}_snapshot.pdf"
        )

        try:

            result = self.driver.execute_cdp_cmd(
                "Page.printToPDF",
                {
                    "printBackground": True
                }
            )

            pdf_data = b64decode(
                result["data"]
            )

            path.write_bytes(pdf_data)

            return path

        except Exception as error:

            print(
                f"Snapshot failed: {error}"
            )

            return None

    # ========================================================
    # COMMON PDF CHECK
    # ========================================================

    def is_common_pdf(self, url):

        filename = Path(
            urlparse(url).path
        ).name.lower()

        return filename in COMMON_PDF_NAMES

    # ========================================================
    # DOWNLOAD PDF
    # ========================================================

    def download_pdf(
        self,
        pdf_url,
        department_name,
        scheme_name,
        index
    ):

        if self.is_common_pdf(pdf_url):

            print(
                f"  Skipping common portal PDF: "
                f"{pdf_url}"
            )

            return {
                "status": "skipped",
                "reason": "common_portal_pdf",
                "url": pdf_url
            }

        if pdf_url in self.downloaded_urls:

            return {
                "status": "already_downloaded",
                "url": pdf_url,
                "local_path": (
                    self.downloaded_urls[pdf_url]
                )
            }

        folder = (
            PDF_DIR /
            safe_filename(department_name)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        filename = Path(
            urlparse(pdf_url).path
        ).name

        if not filename:
            filename = (
                f"{safe_filename(scheme_name)}"
                f"_document_{index}.pdf"
            )

        filename = safe_filename(filename)

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        path = folder / f"{index}_{filename}"

        try:

            print(
                f"  Downloading PDF {index}:"
            )
            print(
                f"  {pdf_url}"
            )

            # Copy browser cookies
            for cookie in self.driver.get_cookies():

                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"]
                )

            response = self.session.get(
                pdf_url,
                timeout=60
            )

            response.raise_for_status()

            content = response.content

            if not content.startswith(b"%PDF"):

                return {
                    "status": "failed",
                    "url": pdf_url,
                    "reason": "not_a_pdf"
                }

            sha256 = file_hash(content)

            if sha256 in self.downloaded_hashes:

                return {
                    "status": "duplicate_content",
                    "url": pdf_url,
                    "sha256": sha256,
                    "local_path": (
                        self.downloaded_hashes[sha256]
                    )
                }

            path.write_bytes(content)

            self.downloaded_urls[pdf_url] = str(path)
            self.downloaded_hashes[sha256] = str(path)

            print(
                f"  PDF saved: {path}"
            )

            return {
                "status": "downloaded",
                "url": pdf_url,
                "local_path": str(path),
                "sha256": sha256,
                "size_bytes": len(content)
            }

        except Exception as error:

            print(
                f"  PDF download failed: {error}"
            )

            return {
                "status": "failed",
                "url": pdf_url,
                "error": str(error)
            }

    # ========================================================
    # CRAWL ONE SCHEME
    # ========================================================

    def crawl_scheme(
        self,
        department,
        scheme
    ):

        print()
        print("-" * 70)
        print(
            f"Department: {department['name']}"
        )
        print(
            f"Scheme: {scheme['name']}"
        )
        print("-" * 70)

        try:

            self.select_scheme(
                department["value"],
                scheme["value"]
            )

            html = self.driver.page_source
            current_url = self.driver.current_url

            parsed = parse_page(
                html,
                current_url
            )

            # ----------------------------------------------
            # Save HTML
            # ----------------------------------------------

            html_path = self.save_html(
                department["name"],
                scheme["name"],
                html
            )

            # ----------------------------------------------
            # Process PDFs
            # ----------------------------------------------

            pdf_links = parsed.get(
                "pdf_links",
                []
            )

            downloaded_pdfs = []
            skipped_pdfs = []
            failed_pdfs = []

            print(
                f"PDF links found on page: "
                f"{len(pdf_links)}"
            )

            for index, pdf in enumerate(
                pdf_links,
                start=1
            ):

                result = self.download_pdf(
                    pdf["url"],
                    department["name"],
                    scheme["name"],
                    index
                )

                result["text"] = pdf.get(
                    "text",
                    ""
                )

                if result["status"] in {
                    "downloaded",
                    "already_downloaded",
                    "duplicate_content"
                }:

                    downloaded_pdfs.append(result)

                elif result["status"] == "skipped":

                    skipped_pdfs.append(result)

                else:

                    failed_pdfs.append(result)

            # ----------------------------------------------
            # Page snapshot
            # ----------------------------------------------

            snapshot_path = (
                self.save_snapshot(
                    department["name"],
                    scheme["name"]
                )
            )

            # ----------------------------------------------
            # Final raw record
            # ----------------------------------------------

            record = {

                "record_type":
                    "eligibility_scheme",

                "scheme_name":
                    scheme["name"],

                "scheme_value":
                    scheme["value"],

                "department_name":
                    department["name"],

                "department_value":
                    department["value"],

                "source": {

                    "portal":
                        "Jan Soochna Portal",

                    "eligibility_url":
                        ELIGIBILITY_URL,

                    "page_url":
                        current_url
                },

                "eligibility_text":
                    parsed.get(
                        "text",
                        ""
                    ),

                "tables":
                    parsed.get(
                        "tables",
                        []
                    ),

                "links":
                    parsed.get(
                        "links",
                        []
                    ),

                "pdf_links":
                    pdf_links,

                "downloaded_pdfs":
                    downloaded_pdfs,

                "skipped_pdfs":
                    skipped_pdfs,

                "failed_pdfs":
                    failed_pdfs,

                "raw_files": {

                    "html":
                        str(html_path),

                    "page_snapshot":
                        (
                            str(snapshot_path)
                            if snapshot_path
                            else None
                        )
                },

                "verification": {

                    "verified":
                        False
                }
            }

            # ----------------------------------------------
            # Save JSON
            # ----------------------------------------------

            json_path = self.save_json(
                department["name"],
                scheme["name"],
                record
            )

            print(
                f"HTML saved: {html_path}"
            )

            print(
                f"JSON saved: {json_path}"
            )

            print(
                f"Downloaded PDFs: "
                f"{len(downloaded_pdfs)}"
            )

            print(
                f"Skipped PDFs: "
                f"{len(skipped_pdfs)}"
            )

            print(
                f"Failed PDFs: "
                f"{len(failed_pdfs)}"
            )

            return True

        except Exception as error:

            print(
                f"ERROR: {error}"
            )

            return False

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
        department_limit=None,
        scheme_limit=None
    ):

        total = 0
        success = 0
        failed = 0

        try:

            self.open_page()

            departments = (
                self.get_departments()
            )

            print(
                f"\nFound "
                f"{len(departments)} departments."
            )

            if department_limit:
                departments = departments[
                    :department_limit
                ]

            for department in departments:

                print()
                print("=" * 70)
                print(
                    f"### Department: "
                    f"{department['name']}"
                )
                print("=" * 70)

                try:

                    schemes = (
                        self.get_schemes(
                            department["value"]
                        )
                    )

                except Exception as error:

                    print(
                        f"Could not load schemes: "
                        f"{error}"
                    )

                    continue

                print(
                    f"Found "
                    f"{len(schemes)} schemes."
                )

                if scheme_limit:
                    schemes = schemes[
                        :scheme_limit
                    ]

                for scheme in schemes:

                    total += 1

                    result = self.crawl_scheme(
                        department,
                        scheme
                    )

                    if result:
                        success += 1
                    else:
                        failed += 1

                    time.sleep(1)

            print()
            print("=" * 70)
            print("CRAWLING COMPLETED")
            print("=" * 70)

            print(
                f"Total schemes: {total}"
            )

            print(
                f"Successful: {success}"
            )

            print(
                f"Failed: {failed}"
            )

            print(
                f"Unique PDFs downloaded: "
                f"{len(self.downloaded_urls)}"
            )

            print("=" * 70)

        finally:

            self.driver.quit()


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Jan Soochna Eligibility "
            "Crawler"
        )
    )

    parser.add_argument(
        "--department-limit",
        type=int,
        default=None
    )

    parser.add_argument(
        "--scheme-limit",
        type=int,
        default=None
    )

    parser.add_argument(
        "--headless",
        action="store_true"
    )

    args = parser.parse_args()

    crawler = JanSoochnaEligibilityCrawler(
        headless=args.headless
    )

    crawler.run(
        department_limit=args.department_limit,
        scheme_limit=args.scheme_limit
    )


if __name__ == "__main__":
    main()