import json
from pathlib import Path
from typing import Optional, Dict, List
import re
import os
import requests
import diskcache
from dotenv import load_dotenv

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

def normalize_term(term: str, context: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Normalize a term using UMLS API.
    
    Args:
        term (str): The term to normalize
        context (Optional[str]): The full context (e.g., the complete claim)
        
    Returns:
        Optional[Dict[str, str]]: Normalized term info or None if no mapping
    """
    term = term.strip().lower()
    
    # Get UMLS synonyms
    synonyms = get_umls_synonyms(term)
    if not synonyms:
        return None
        
    # Use the first synonym as the standard term
    result = {
        "standard_term": synonyms[0],
        "synonyms": synonyms
    }
    
    with open("normalization_log.txt", "a") as log:
        log.write(f"TERM: {term} | CONTEXT: {context} | NORMALIZED: {result['standard_term']}\n")
    
    return result

def normalize_claim_phrases(claim: str, max_phrase_len: int = 5) -> List[Dict[str, str]]:
    """
    Normalize all possible phrases in the claim using UMLS API.
    Returns a list of dicts: {'original': ..., 'standard_term': ..., 'synonyms': [...]}
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
            synonyms = get_umls_synonyms(phrase)
            if synonyms:
                results.append({
                    "original": phrase,
                    "standard_term": synonyms[0],
                    "synonyms": synonyms
                })
                for j in range(i, i+n):
                    used[j] = True  # Mark these words as used

    # Optionally, normalize remaining single words
    for i, word in enumerate(words):
        if not used[i]:
            synonyms = get_umls_synonyms(word)
            if synonyms:
                results.append({
                    "original": word,
                    "standard_term": synonyms[0],
                    "synonyms": synonyms
                })
                used[i] = True

    return results