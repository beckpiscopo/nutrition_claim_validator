"""Module for building PubMed queries from nutrition claims."""

from typing import Optional, List
from src.normalizer import normalize_term, normalize_claim_phrases
from src.umls import cui_to_mesh  # assume you have or will implement this helper
from src.query import parse_pubmed_article
import requests

def build_pubmed_query_from_claim(
    subject: str,
    outcome: str,
    *,
    field: str = "TIAB",
    mesh_field: str = "MeSH Terms",
    human_only: bool = True,
    publication_types: Optional[List[str]] = None,
) -> str:
    """
    Build a dynamic PubMed query from subject and outcome terms.
    """
    def expand(term: str, context: str = "") -> List[str]:
        norm = normalize_term(term, context=context)
        terms = [norm["standard_term"]] if norm else []
        if norm and norm.get("CUI"):
            mesh = cui_to_mesh(norm["CUI"])
            if mesh:
                terms.append(mesh)
        # If normalization fails, try reducing the phrase
        if not terms:
            lower_term = term.lower()
            if any(kw in lower_term for kw in ["period cramping", "period pain", "menstrual pain", "menstrual cramps"]):
                terms.append("dysmenorrhea")
            else:
                for sep in [" from ", " of ", " in ", " due to "]:
                    if sep in term:
                        reduced = term.split(sep)[-1].strip()
                        norm2 = normalize_term(reduced, context=context)
                        if norm2:
                            terms.append(norm2["standard_term"])
                        else:
                            terms.append(reduced)
                        break
                else:
                    terms.append(term)
        return list(dict.fromkeys(terms))  # dedupe, preserve order

    subj_terms = expand(subject, context=subject + " " + outcome)
    out_terms = expand(outcome, context=subject + " " + outcome)

    subj_clause = " OR ".join(f'"{t}"[{field}]' for t in subj_terms)
    outcome_clause = " OR ".join(f'"{t}"[{field}]' for t in out_terms)

    clauses = [f"({subj_clause})", f"({outcome_clause})"]
    if human_only:
        clauses.append(f"humans[{mesh_field}]")
    if publication_types:
        pt_clause = " OR ".join(f'{pt}[pt]' for pt in publication_types)
        clauses.append(f"({pt_clause})")

    return " AND ".join(clauses)

def get_evidence(subject, outcome, max_results=5, human_only=True, publication_types=None):
    query = build_pubmed_query_from_claim(subject, outcome, human_only=human_only, publication_types=publication_types)
    print(f"PubMed Query: {query}")  # For logs
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "tool": "claim-validator",
        "email": "your.email@example.com"
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    resp = requests.get(url, params=params)
    pmids = resp.json()["esearchresult"]["idlist"]
    if not pmids:
        return {
            "valid": False,
            "evidence": [],
            "message": "No scientific evidence found",
            "query": query,
        }
    papers = efetch(pmids)
    return {
        "valid": True,
        "evidence": papers,
        "message": f"Found {len(papers)} results",
        "query": query,
    }

def efetch(pmids):
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": "claim-validator",
        "email": "your.email@example.com"
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    from xml.etree import ElementTree
    root = ElementTree.fromstring(resp.content)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        paper = parse_pubmed_article(article)
        paper["pmid"] = article.findtext(".//PMID", "")
        paper["authors"] = [author.findtext(".//LastName", "") + " " + author.findtext(".//ForeName", "") 
                            for author in article.findall(".//Author")]
        paper["publication_date"] = article.findtext(".//PubDate/Year", "")
        paper["journal"] = article.findtext(".//Journal/Title", "")
        papers.append(paper)
    return papers