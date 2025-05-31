import pytest
from src.normalizer import normalize_term, normalize_claim_phrases

def test_normalize_known_terms():
    # Direct matches
    assert normalize_term("period pain") is not None
    assert normalize_term("menstrual cramps") is not None
    assert normalize_term("dysmenorrhea") is not None
    # Fuzzy match
    assert normalize_term("menstral cramps") is not None
    # Should map to dysmenorrhea or menstrual pain
    for phrase in ["period cramping", "period pain", "menstrual cramps", "menstral cramps"]:
        result = normalize_term(phrase)
        print(f"normalize_term('{phrase}') -> {result}")
        assert result is not None
        assert result["standard_term"] in ["dysmenorrhea", "menstrual pain", "menstrual cramps"]

def test_normalize_claim_phrases():
    claim = "ginger reduces pain from period cramps"
    results = normalize_claim_phrases(claim)
    print(f"normalize_claim_phrases('{claim}') -> {results}")
    # Should find at least one mapping to dysmenorrhea or menstrual pain
    assert any(r["standard_term"] in ["dysmenorrhea", "menstrual pain", "menstrual cramps"] for r in results)

def test_normalize_unknown_term():
    assert normalize_term("completely unknown term") is None

def test_normalize_whitespace_and_case():
    result = normalize_term("  PeRioD PaiN ")
    print(f"normalize_term('  PeRioD PaiN ') -> {result}")
    assert result is not None
    assert result["standard_term"] in ["dysmenorrhea", "menstrual pain", "menstrual cramps"]