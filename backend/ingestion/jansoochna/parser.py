from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_page(html: str, page_url: str) -> dict:
    """
    Extract useful information from a Jan Soochna
    eligibility page.
    """

    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Get complete visible text
    text = soup.get_text(
        separator="\n",
        strip=True
    )

    # -----------------------------------------
    # Extract PDF and other useful links
    # -----------------------------------------

    links = []
    pdf_links = []

    for tag in soup.find_all("a", href=True):

        href = tag["href"].strip()

        if not href:
            continue

        absolute_url = urljoin(
            page_url,
            href
        )

        link_text = tag.get_text(
            " ",
            strip=True
        )

        link_data = {
            "text": link_text,
            "url": absolute_url
        }

        links.append(link_data)

        if ".pdf" in absolute_url.lower():
            pdf_links.append(link_data)

    # -----------------------------------------
    # Extract tables
    # -----------------------------------------

    tables = []

    for table in soup.find_all("table"):

        rows = []

        for tr in table.find_all("tr"):

            cells = tr.find_all(
                ["th", "td"]
            )

            row = [
                cell.get_text(
                    " ",
                    strip=True
                )
                for cell in cells
            ]

            if row:
                rows.append(row)

        if rows:
            tables.append(rows)

    return {
        "page_url": page_url,
        "text": text,
        "tables": tables,
        "links": links,
        "pdf_links": pdf_links,
    }