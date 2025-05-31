

"""Quick smoke‑test for PubMed E‑utilities connectivity.

Run from project root:
    python -m src.pubmed_validator
"""

import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()  # Loads NCBI_API_KEY from .env if present

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def esearch(term: str, *, retmax: int = 5):
    """Return a list of PubMed IDs that match the search term."""
    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": retmax,
        "tool": "claim-validator",
        "email": "your.email@example.com",  # replace with your real email
    }
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key

    resp = requests.get(f"{BASE}/esearch.fcgi", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["esearchresult"]["idlist"]


def main() -> None:
    query = '"chia seeds"[Title/Abstract] AND omega-3'
    ids = esearch(query)
    print(f"Success! PubMed returned {len(ids)} IDs: {ids}")


if __name__ == "__main__":
    main()