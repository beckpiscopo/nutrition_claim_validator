import sys
import requests
from urllib.parse import urlencode
from claim_extractor import extract_claim

def build_debug_pubmed_query_from_claim(claim: str, field: str = "TIAB") -> str:
    result = extract_claim(claim)
    print("extract_claim output:", result)
    subject = result.get("subject") if isinstance(result, dict) else None
    outcome = result.get("object") if isinstance(result, dict) else None
    if not subject or not outcome:
        term = claim.strip().replace('"', "'")
        return f'"{term}"[{field}]'
    # Split outcome on 'and'/'or' and use OR logic for each outcome term
    import re
    outcome_terms = re.split(r"\\band\\b|\\bor\\b", outcome)
    outcome_terms = [o.strip() for o in outcome_terms if o.strip()]
    if outcome_terms:
        outcome_clause = " OR ".join([f'"{o}"[{field}]' for o in outcome_terms])
        query = f'"{subject}"[{field}] AND ({outcome_clause})'
    else:
        query = f'"{subject}"[{field}]'
    print("PubMed Query:", query)
    return query

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_pubmed_query.py '<claim text>'")
        sys.exit(1)
    claim = sys.argv[1]

    # Build the query string
    query = '"ashwagandha"[TIAB] AND ("cortisol"[TIAB] OR "stress"[TIAB])'
    print(f"Generated PubMed Query: {query}")

    # Build the ESearch URL
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 5,
        "tool": "debug-script",
        "email": "your.email@example.com"
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
    print(f"ESearch URL: {url}")

    # Make the API call
    resp = requests.get(url)
    print(f"HTTP Status: {resp.status_code}")
    print("Raw Response:")
    print(resp.text)

    # Optionally, print the list of PMIDs found
    try:
        data = resp.json()
        pmids = data["esearchresult"]["idlist"]
        print(f"PMIDs found: {pmids}")
    except Exception as e:
        print("Could not parse JSON response:", e)

if __name__ == "__main__":
    main()