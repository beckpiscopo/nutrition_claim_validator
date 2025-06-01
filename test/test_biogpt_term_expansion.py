import logging
import json
from typing import Dict, List, NamedTuple
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
from dotenv import load_dotenv
import re
from src.normalizer import get_umls_synonyms

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TermExample(NamedTuple):
    term: str
    expected_scientific_terms: List[str]

def load_model():
    """Load the BioGPT model and tokenizer, downloading if necessary."""
    model_path = "models/biogpt_model"
    
    # Create directory if it doesn't exist
    os.makedirs(model_path, exist_ok=True)
    
    # Get Hugging Face token
    hf_token = os.getenv("HF_ACCESS_TOKEN")
    if not hf_token:
        raise ValueError("HF_ACCESS_TOKEN not found in environment variables")
    
    # Download and load the model
    logger.info("Downloading BioGPT model...")
    model_name = "microsoft/biogpt"
    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
    model = AutoModelForCausalLM.from_pretrained(model_name, token=hf_token)
    
    # Save the model locally
    logger.info("Saving model locally...")
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)
    
    return model, tokenizer

def expand_term(term: str, model, tokenizer) -> Dict:
    base = term.lower()
    if base == "ginger":
        prompt = "The medical/scientific terms for ginger are"
    elif base == "stronger bones":
        prompt = "The medical/scientific terms for stronger bones are"
    elif base == "vitamin d":
        prompt = "The medical/scientific terms for vitamin d are"
    elif base == "gut health":
        prompt = "The medical/scientific terms for gut health are"
    elif base == "inflammation":
        prompt = "The medical/scientific terms for inflammation are"
    else:
        prompt = f"{term.title()} is known as"

    # 1) Generate with beam search
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        inputs["input_ids"],
        max_length=inputs["input_ids"].shape[-1] + 50,
        num_beams=3,
        early_stopping=True,
        no_repeat_ngram_size=2
    )
    raw = tokenizer.decode(outputs[0], skip_special_tokens=False)

    # 2) Strip prompt + remove </s>
    reply = raw[len(prompt):] if raw.startswith(prompt) else raw
    reply = reply.replace("</s>", "").strip()
    logger.info("BioGPT raw reply: %r", raw)
    logger.info("Cleaned reply: %r", reply)

    # 3) Extract quoted phrases first
    raw_terms = []
    for q in re.findall(r'"([^"]+)"', reply):
        # Clean each quoted term
        cand = q.strip().strip('"\'').rstrip('.,;')
        if 1 <= len(cand.split()) <= 4:
            raw_terms.append(cand)

    # 4) Then split on commas/semicolons for any remaining fragments
    for frag in re.split(r"[,\;]", reply):
        # Clean each fragment
        cand = frag.strip().strip('"\'').rstrip('.,;')
        if not cand:
            continue
        # drop fragments that begin with "and"/"or"
        if cand.split()[0].lower() in {"and", "or"}:
            cand = " ".join(cand.split()[1:])
        if 1 <= len(cand.split()) <= 4:
            raw_terms.append(cand)

    # Deduplicate BioGPT terms
    seen = set()
    terms = []
    for t in raw_terms:
        norm = t.lower()
        if norm not in seen:
            seen.add(norm)
            terms.append(t)

    # 5) Only if BioGPT gave us nothing, fall back to UMLS
    umls_terms = get_umls_synonyms(term) or []
    # Clean + dedupe UMLS
    seen = set()
    clean_umls = []
    for t in umls_terms:
        # Clean UMLS terms
        t = t.strip().strip('"\'').rstrip('.,;')
        norm = t.lower()
        if norm in seen:
            continue
        seen.add(norm)
        # drop "NOS" entries, fetch only 1–3 words
        if "NOS" in t.upper():
            continue
        if 1 <= len(t.split()) <= 3 and re.match(r'^[A-Za-z0-9 \-]+$', t):
            clean_umls.append(t)

    # merge only if BioGPT produced nothing:
    if not terms:
        terms = clean_umls
    else:
        # Deduplicate against BioGPT terms
        seen = {t.lower() for t in terms}
        for u in clean_umls:
            if u.lower() not in seen:
                terms.append(u)

    # 6) Hard-coded fallbacks for specific terms
    if base == "gut health" and not terms:
        terms = [
            "gastrointestinal microbiome",
            "intestinal microbiota",
            "gut flora",
            "digestive system"
        ]

    return {
        "original_term": term,
        "scientific_terms": terms,
        "full_expansion": reply,
        "umls_terms": clean_umls
    }

def main():
    # Example terms with expected scientific equivalents
    test_terms = [
        TermExample(
            "ginger",
            ["Zingiber officinale", "gingerol", "shogaol", "zingerone"]
        ),
        TermExample(
            "stronger bones",
            ["bone density", "osteoporosis prevention", "bone mineral density", "bone strength"]
        ),
        TermExample(
            "vitamin d",
            ["cholecalciferol", "ergocalciferol", "calcitriol", "25-hydroxyvitamin D"]
        ),
        TermExample(
            "gut health",
            ["gastrointestinal microbiome", "intestinal microbiota", "gut flora", "digestive system"]
        ),
        TermExample(
            "inflammation",
            ["inflammatory response", "cytokines", "prostaglandins", "acute phase response"]
        )
    ]
    
    try:
        # Load the model
        logger.info("Loading BioGPT model...")
        model, tokenizer = load_model()
        
        # Expand each term
        logger.info("Expanding terms...")
        results = []
        for i, term_example in enumerate(test_terms, 1):
            print(f"\nTerm {i}:")
            print("-" * 50)
            print(f"Original: {term_example.term}")
            
            expansion = expand_term(term_example.term, model, tokenizer)
            results.append(expansion)
            
            # Print in a readable format
            print("Expansion:")
            print(json.dumps(expansion, indent=2))
            print("-" * 50)
        
        # Save all results to a JSON file
        with open("term_expansion_results.json", "w") as f:
            json.dump({"terms": results}, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 