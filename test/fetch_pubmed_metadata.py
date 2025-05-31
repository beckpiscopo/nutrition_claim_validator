import sys
import requests
from xml.etree import ElementTree

def fetch_pubmed_xml(pmid):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.content

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
        "pmid": get_text(".//PMID"),
        "title": get_text(".//ArticleTitle"),
        "journal": get_text(".//Journal/Title"),
        "publication_date": get_text(".//PubDate/Year"),
        "abstract": abstract.strip(),
        "methods": methods,
        "results": results,
        "conclusions": conclusions,
        "keywords": keywords,
        "grants": grants,
        "authors": authors,
    }

def print_article_metadata(metadata):
    print(f"PMID: {metadata['pmid']}")
    print(f"Title: {metadata['title']}")
    print(f"Journal: {metadata['journal']}")
    print(f"Publication Date: {metadata['publication_date']}")
    print(f"Abstract: {metadata['abstract']}")
    if metadata['methods']:
        print(f"Methods: {metadata['methods']}")
    if metadata['results']:
        print(f"Results: {metadata['results']}")
    if metadata['conclusions']:
        print(f"Conclusions: {metadata['conclusions']}")
    if metadata['keywords']:
        print(f"Keywords: {', '.join(metadata['keywords'])}")
    if metadata['grants']:
        print("Grants/Funding:")
        for grant in metadata['grants']:
            print(f"  - {grant}")
    print("Authors:")
    for author in metadata['authors']:
        line = f"  - {author['fore_name']} {author['last_name']}".strip()
        if author.get("initials"):
            line += f" ({author['initials']})"
        if author.get("affiliation"):
            line += f", {author['affiliation']}"
        if author.get("orcid"):
            line += f" [ORCID: {author['orcid']}]"
        print(line)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fetch_pubmed_metadata.py <PMID>")
        sys.exit(1)
    pmid = sys.argv[1]
    xml = fetch_pubmed_xml(pmid)
    root = ElementTree.fromstring(xml)
    article = root.find(".//PubmedArticle")
    if article is None:
        print("No article found for this PMID.")
        sys.exit(1)
    metadata = parse_pubmed_article(article)
    print_article_metadata(metadata)
