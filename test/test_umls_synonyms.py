from src.normalizer import get_umls_synonyms

if __name__ == "__main__":
    term = "liver injury"
    synonyms = get_umls_synonyms(term)
    print(f"Synonyms for '{term}':")
    for syn in synonyms:
        print(f"- {syn}")

def get_umls_synonyms(term):
    syn_resp = get_umls_synonyms_api(term)
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