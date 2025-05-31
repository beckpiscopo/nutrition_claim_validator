# src/cache_test.py
from claim_extractor import llm_build_pubmed_query
import diskcache

cache = diskcache.Cache('.cache')
claim = "chia seeds support heart health"
print("Query:", llm_build_pubmed_query(claim))
print("Number of cached items:", len(cache))
print("Keys:", list(cache.iterkeys()))