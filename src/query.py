"""Module for building PubMed search queries from nutrition claims."""

from typing import List, Optional
from src.claim_extractor import extract_claim
from src.normalizer import normalize_term, normalize_claim_phrases
import re
from xml.etree import ElementTree

def build_pubmed_query_from_claim(
    claim: str,
    *,
    field: str = "TIAB",
    mesh_field: str = "MeSH Terms",
    human_only: bool = True,
    publication_types: Optional[List[str]] = None,
) -> str:
    """
    Build a PubMed search query dynamically from any claim text by:
    - Extracting subject and object (outcome) via SVO parser.
    - Using both MeSH terms and Title/Abstract fields for better precision.
    - Adding specific filters for clinical relevance.
    - Normalizing consumer health terms to UMLS concepts using phrase-first approach.
    """
    result = extract_claim(claim)
    subject = result.get("subject") if isinstance(result, dict) else None
    outcome = result.get("object") if isinstance(result, dict) else None

    if subject and outcome:
        # Get all normalized phrases for subject and outcome
        subject_norms = normalize_claim_phrases(subject)
        outcome_norms = normalize_claim_phrases(outcome)
        
        # Split outcome on 'and'/'or' and use OR logic
        outcome_terms = re.split(r"\band\b|\bor\b", outcome)
        outcome_terms = [o.strip() for o in outcome_terms if o.strip()]
        
        # Build subject clauses with both MeSH and Title/Abstract
        subject_clauses = [
            f'"{subject}"[{field}]',
            f'"{subject}"[{mesh_field}]'
        ]
        
        # Add normalized subject terms if available
        for norm in subject_norms:
            subject_clauses.extend([
                f'"{norm["standard_term"]}"[{field}]',
                f'"{norm["standard_term"]}"[{mesh_field}]'
            ])
        
        # Build outcome clauses with both MeSH and Title/Abstract
        outcome_clauses = []
        for term in outcome_terms:
            outcome_clauses.extend([
                f'"{term}"[{field}]',
                f'"{term}"[{mesh_field}]'
            ])
            # Add normalized outcome terms if available
            term_norms = normalize_claim_phrases(term)
            for norm in term_norms:
                outcome_clauses.extend([
                    f'"{norm["standard_term"]}"[{field}]',
                    f'"{norm["standard_term"]}"[{mesh_field}]'
                ])
        
        # Combine all clauses
        clauses = [
            f"({' OR '.join(subject_clauses)})",
            f"({' OR '.join(outcome_clauses)})"
        ]
    else:
        # Fallback: extract keywords, require at least two, use AND/OR logic
        stopwords = {"the", "and", "or", "with", "for", "that", "this", "are", "was", "has", "had", "have", "from", "per", "just", "ever", "show", "shows", "been", "will", "can", "may", "but", "not", "all", "any", "out", "our", "your", "their", "more", "less", "than", "each", "new", "best", "good", "bad", "great", "very", "much", "some", "most", "such", "also", "like", "get", "got", "make", "made", "use", "used", "using", "into", "over", "under", "about", "after", "before", "while", "when", "where", "which", "who", "whose", "whom", "because", "since", "until", "though", "although", "if", "then", "so", "too", "as", "on", "in", "by", "of", "to", "at", "is", "it", "an", "a"}
        words = re.findall(r"\b\w+\b", claim.lower())
        keywords = [w for w in words if len(w) > 3 and w not in stopwords]
        if len(keywords) >= 2:
            subject = keywords[0]
            outcome_terms = keywords[1:]
            subject_clauses = [
                f'"{subject}"[{field}]',
                f'"{subject}"[{mesh_field}]'
            ]
            outcome_clauses = []
            for term in outcome_terms:
                outcome_clauses.extend([
                    f'"{term}"[{field}]',
                    f'"{term}"[{mesh_field}]'
                ])
            clauses = [
                f"({' OR '.join(subject_clauses)})",
                f"({' OR '.join(outcome_clauses)})"
            ]
        elif keywords:
            clauses = [
                f'"{keywords[0]}"[{field}]',
                f'"{keywords[0]}"[{mesh_field}]'
            ]
        else:
            # Last resort: search for the whole claim
            term = claim.strip().replace('"', "'")
            clauses = [
                f'"{term}"[{field}]',
                f'"{term}"[{mesh_field}]'
            ]

    # Human filter
    if human_only:
        clauses.append(f"humans[{mesh_field}]")

    # Publication types filter - prioritize clinical trials and RCTs
    if publication_types:
        pt_clause = " OR ".join(f'{pt}[pt]' for pt in publication_types)
        clauses.append(f"({pt_clause})")
    else:
        # Default to clinical trials and RCTs if no types specified
        clauses.append("(Clinical Trial[pt] OR Randomized Controlled Trial[pt])")

    # Add filters for clinical relevance
    clauses.extend([
        "English[lang]",  # English language only
        "hasabstract",    # Must have an abstract
        "(" + " OR ".join([
            "Clinical Trial[pt]",
            "Randomized Controlled Trial[pt]",
            "Meta-Analysis[pt]",
            "Systematic Review[pt]",
            "Review[pt]"
        ]) + ")"
    ])

    query = " AND ".join(clauses)
    print("PubMed Query:", query)
    return query

def parse_pubmed_article(article):
    def get_text(path):
        elem = article.find(path)
        return elem.text if elem is not None else ""

    # Abstract sections
    abstract_sections = article.findall(".//Abstract/AbstractText")
    abstract = ""
    methods = ""
    results = ""
    conclusions = ""
    for section in abstract_sections:
        label = section.attrib.get("Label", "").lower()
        if label == "methods":
            methods = section.text or ""
        elif label == "results":
            results = section.text or ""
        elif label == "conclusions":
            conclusions = section.text or ""
        else:
            abstract += (section.text or "") + " "

    # Keywords
    keywords = [kw.text for kw in article.findall(".//KeywordList/Keyword") if kw.text]

    # Grants
    grants = []
    for grant in article.findall(".//GrantList/Grant"):
        grant_id = grant.findtext("GrantID", "").strip()
        agency = grant.findtext("Agency", "").strip()
        country = grant.findtext("Country", "").strip()
        grant_info = " / ".join(filter(None, [grant_id, agency, country]))
        if grant_info:
            grants.append(grant_info)

    # Authors (rich metadata)
    authors = []
    for author in article.findall(".//Author"):
        authors.append({
            "last_name": author.findtext("LastName", ""),
            "fore_name": author.findtext("ForeName", ""),
            "initials": author.findtext("Initials", ""),
            "affiliation": author.findtext(".//Affiliation", ""),
            "orcid": next((id_elem.text for id_elem in author.findall("Identifier") if id_elem.attrib.get("Source") == "ORCID"), None)
        })

    return {
        "title": get_text(".//ArticleTitle"),
        "abstract": abstract.strip(),
        "methods": methods,
        "results": results,
        "conclusions": conclusions,
        "keywords": keywords,
        "grants": grants,
        "authors": authors,
        # ...other fields as needed
    } 