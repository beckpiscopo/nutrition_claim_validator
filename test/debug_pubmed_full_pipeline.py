import sys
import requests
from urllib.parse import urlencode
from claim_extractor import extract_claim, analyze_paper
from evidence import get_evidence, efetch
from query import build_pubmed_query_from_claim
from normalizer import normalize_term

DEFAULT_MAX_RELEVANT = 5


def print_normalized_terms(claim):
    """Print normalized terms for debugging."""
    result = extract_claim(claim)
    if isinstance(result, dict):
        subject = result.get("subject")
        outcome = result.get("object")
        if subject:
            norm = normalize_term(subject, context=claim)
            print(f"\nSubject term: '{subject}'")
            if norm:
                print(f"  Normalized to: '{norm['standard_term']}' (CUI: {norm['CUI']})")
            else:
                print("  No normalization found")
        if outcome:
            # Split outcome on 'and'/'or' and normalize each term
            outcome_terms = [o.strip() for o in outcome.split() if o.strip()]
            print(f"\nOutcome terms:")
            for term in outcome_terms:
                norm = normalize_term(term, context=claim)
                print(f"  '{term}'")
                if norm:
                    print(f"    Normalized to: '{norm['standard_term']}' (CUI: {norm['CUI']})")
                else:
                    print("    No normalization found")


def fetch_pmids(query, retmax=20):
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "tool": "debug-full-pipeline",
        "email": "your.email@example.com"
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data["esearchresult"]["idlist"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_pubmed_full_pipeline.py '<claim text>' [max_relevant]")
        sys.exit(1)
    
    # Check if this is a direct query test (starts with "test:")
    if sys.argv[1].startswith("test:"):
        query = sys.argv[1][5:]  # Remove "test:" prefix
        print(f"Direct query test: {query}")
    else:
        claim_text = sys.argv[1]
        # Extract claim
        claim = extract_claim(claim_text)
        print(f"Extracted claim: {claim}")
        if not claim:
            print("No claim extracted. Exiting.")
            sys.exit(0)
            
        # Print normalized terms
        print_normalized_terms(claim)
        
        # Build PubMed query
        query = build_pubmed_query_from_claim(claim, human_only=False)
    
    print(f"\nPubMed Query: {query}")
    
    max_relevant = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_RELEVANT

    # Fetch PMIDs
    pmids = fetch_pmids(query, retmax=max_relevant*10)
    print(f"PMIDs found: {pmids}")
    if not pmids:
        print("No PubMed results found.")
        sys.exit(0)

    # Fetch paper metadata
    papers = efetch(pmids)
    print(f"Fetched {len(papers)} papers from PubMed.")

    # Analyze each paper for relevance/validity
    relevant_count = 0
    for i, paper in enumerate(papers, 1):
        analysis = analyze_paper(paper, claim if 'claim' in locals() else query)
        print(f"\nPaper {i}: {paper['title']} (PMID: {paper.get('pmid')})")
        print(f"  Relevance: {analysis['relevance']}")
        print(f"  Confidence Scores:")
        for component, score in analysis.get('confidence_scores', {}).items():
            print(f"    - {component}: {score:.2f}")
        print(f"  Overall Confidence: {analysis['overall_confidence']:.2f}")
        print(f"  Summary: {analysis['summary']}")
        print(f"  Validity: {analysis['validity']}")
        print(f"  Reasoning: {analysis['reasoning']}")
        if analysis["relevance"] == "DIRECT":
            relevant_count += 1
        if relevant_count >= max_relevant:
            break

if __name__ == "__main__":
    main() 