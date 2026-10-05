from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urldefrag
import json
import re
import time

import requests
from bs4 import BeautifulSoup

START_URLS = [
    "https://support.cchifirm.ca/en/content/cch_ifirm/web_api/api_about_cch_ifirm_tax_web_api.htm",
    "https://support.cchifirm.ca/en/content/cch_ifirm/web_api/api_about_cch_ifirm_common_api.htm",
]

ALLOWED_PREFIX = (
    "https://support.cchifirm.ca/en/content/cch_ifirm/web_api/"
)

OUTPUT_DIR = Path("cch_ifirm_docs")
OUTPUT_DIR.mkdir(exist_ok=True)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Internal-RLB-Documentation-Indexer/1.0"
    }
)

visited = set()
queue = deque(START_URLS)


def sanitize_filename(url: str) -> str:
    name = url.split("/")[-1]

    if not name:
        name = "index"

    name = name.replace(".htm", "")
    name = name.replace(".html", "")

    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def extract_endpoints(text: str):
    pattern = r"/api/partner/1\.0/[^\s\)\]\}\,;]+"
    return sorted(set(re.findall(pattern, text)))


while queue:
    url = queue.popleft()

    url, _ = urldefrag(url)

    if url in visited:
        continue

    if not url.startswith(ALLOWED_PREFIX):
        continue

    print(f"Scraping: {url}")

    visited.add(url)

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"ERROR: {url}")
        print(e)
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    title = (
        soup.title.get_text(strip=True)
        if soup.title
        else "Untitled"
    )

    text = soup.get_text("\n", strip=True)

    endpoints = extract_endpoints(text)

    document = {
        "title": title,
        "url": url,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "content": text,
    }

    output_file = (
        OUTPUT_DIR /
        f"{sanitize_filename(url)}.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            document,
            f,
            indent=2,
            ensure_ascii=False
        )

    for link in soup.find_all("a", href=True):
        next_url = urljoin(url, link["href"])
        next_url, _ = urldefrag(next_url)

        if (
            next_url.startswith(ALLOWED_PREFIX)
            and next_url not in visited
        ):
            queue.append(next_url)

    time.sleep(0.5)

print()
print(f"Finished.")
print(f"Pages scraped: {len(visited)}")
print(f"Output folder: {OUTPUT_DIR.resolve()}")