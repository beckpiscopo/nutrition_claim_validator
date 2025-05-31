from normalizer import normalize_term

test_terms = [
    "menstrual cramps",    # exact
    "menstral cramps",     # typo
    "upset stomack",       # typo
    "period pain",         # not in lookup, see what happens
    "cramps",              # synonym, see what happens
    "completely unknown"   # no match
]

for term in test_terms:
    result = normalize_term(term)
    print(f"Input: {term} -> {result}")