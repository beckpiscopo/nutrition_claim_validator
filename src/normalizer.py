import json
from pathlib import Path
from typing import Optional, Dict, List
import re
import os
import requests
import diskcache
from dotenv import load_dotenv

from rapidfuzz import process

_LOOKUP_PATH = Path(__file__).parent.parent / "data" / "processed" / "chv_lookup.json"
with _LOOKUP_PATH.open(encoding="utf-8") as f:
    _CHV_LOOKUP: Dict[str, Dict[str,str]] = json.load(f)

# Terms that should only be normalized when they appear alone
_STANDALONE_TERMS = {
    "drinking": "alcohol consumption",  # Only normalize when it's just "drinking"
    # Add other terms that need context here
}

FUZZ_THRESHOLD = 95 # tweak as needed

load_dotenv()
UMLS_API_KEY = os.getenv("UMLS_API_KEY")
UMLS_CACHE = diskcache.Cache(".umls_cache")

def get_umls_auth_ticket(api_key):
    # Get a UMLS authentication ticket granting ticket (TGT)
    auth_url = "https://utslogin.nlm.nih.gov/cas/v1/api-key"
    resp = requests.post(auth_url, data={"apikey": api_key})
    tgt = resp.headers["location"]
    return tgt

def get_umls_service_ticket(tgt):
    # Get a single-use service ticket
    service = "http://umlsks.nlm.nih.gov"
    resp = requests.post(tgt, data={"service": service})
    return resp.text

def get_umls_synonyms(term):
    if not UMLS_API_KEY:
        raise ValueError("UMLS_API_KEY not set in .env")
    cache_key = f"umls_synonyms::{term.lower()}"
    if cache_key in UMLS_CACHE:
        return UMLS_CACHE[cache_key]

    # Step 1: Search for CUI
    search_url = "https://uts-ws.nlm.nih.gov/rest/search/current"
    params = {"string": term, "apiKey": UMLS_API_KEY}
    resp = requests.get(search_url, params=params)
    results = resp.json()
    items = results['result']['results']
    if not items:
        return []
    cui = items[0]['ui']

    # Step 2: Get synonyms/atoms for CUI
    syn_url = f"https://uts-ws.nlm.nih.gov/rest/content/current/CUI/{cui}/atoms"
    syn_resp = requests.get(syn_url, params={"apiKey": UMLS_API_KEY})
    syns = set()
    for atom in syn_resp.json()['result']:
        if atom.get('language') == 'ENG':
            name = atom['name']
            syns.add(name)
            if 'MeSH' in atom['rootSource']:
                syns.add(f"{name}[MeSH Terms]")
    syn_list = list(syns)
    UMLS_CACHE[cache_key] = syn_list
    return syn_list

def fuzzy_normalize(term: str) -> Optional[Dict[str,str]]:
    """
    Fuzzy match a term to the closest entry in the CHV lookup using rapidfuzz.
    Returns the normalized dict if the match score is above the threshold.
    """
    match = None
    score = 0
    # Find the closest CHV key and its score
    result = process.extractOne(term, _CHV_LOOKUP.keys(), score_cutoff=FUZZ_THRESHOLD)
    if result:
        match, score, _ = result
        if match:
            return _CHV_LOOKUP[match]
    return None

def normalize_term(term: str, context: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Normalize a term to its UMLS concept, being careful about context.
    
    Args:
        term (str): The term to normalize
        context (Optional[str]): The full context (e.g., the complete claim)
        
    Returns:
        Optional[Dict[str, str]]: Normalized term info or None if no mapping
    """
    term = term.strip().lower()
    
    # Check if this is a standalone term that needs context
    if term in _STANDALONE_TERMS:
        if context:
            # If we have context, check if the term appears alone
            # This is a simple heuristic - we could make it more sophisticated
            words = re.findall(r'\b\w+\b', context.lower())
            if term in words and len(words) > 1:
                # Term appears with other words, don't normalize
                return None
        # If no context or term appears alone, use the mapping
        result = {
            "standard_term": _STANDALONE_TERMS[term],
            "CUI": _CHV_LOOKUP.get(term, {}).get("CUI", "")
        }
        if result:
            with open("normalization_log.txt", "a") as log:
                log.write(f"TERM: {term} | CONTEXT: {context} | NORMALIZED: {result['standard_term']}\n")
        return result
    
    # 1. Try static lookup
    result = _CHV_LOOKUP.get(term)
    if result:
        with open("normalization_log.txt", "a") as log:
            log.write(f"TERM: {term} | CONTEXT: {context} | NORMALIZED: {result['standard_term']}\n")
        return result

    # 2. Try fuzzy match
    result = fuzzy_normalize(term)
    if result:
        with open("normalization_log.txt", "a") as log:
            log.write(f"TERM: {term} | CONTEXT: {context} | FUZZY_NORMALIZED: {result['standard_term']}\n")
        return result

    # 3. (Future) Try UMLS API here

    return None

def normalize_claim_phrases(claim: str, max_phrase_len: int = 5) -> List[Dict[str, str]]:
    """
    Normalize all possible phrases in the claim, preferring longer matches.
    Returns a list of dicts: {'original': ..., 'standard_term': ..., 'CUI': ...}
    """
    claim = claim.lower()
    words = claim.split()
    used = [False] * len(words)
    results = []

    for n in range(max_phrase_len, 0, -1):  # Try longer phrases first
        for i in range(len(words) - n + 1):
            if any(used[i:i+n]):
                continue  # Skip if any word in this span is already used
            phrase = " ".join(words[i:i+n])
            norm = _CHV_LOOKUP.get(phrase)
            if norm:
                results.append({
                    "original": phrase,
                    "standard_term": norm["standard_term"],
                    "CUI": norm["CUI"]
                })
                for j in range(i, i+n):
                    used[j] = True  # Mark these words as used

    # Optionally, normalize remaining single words
    for i, word in enumerate(words):
        if not used[i]:
            norm = _CHV_LOOKUP.get(word)
            if norm:
                results.append({
                    "original": word,
                    "standard_term": norm["standard_term"],
                    "CUI": norm["CUI"]
                })
                used[i] = True

    return results