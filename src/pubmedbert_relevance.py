from typing import List, Tuple
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

# Load PubMedBERT model and tokenizer
_tokenizer = AutoTokenizer.from_pretrained("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract")
_model = AutoModel.from_pretrained("microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract")


def embed(text: str) -> np.ndarray:
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = _model(**inputs)
    # Mean pooling
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

def rank_relevance(claim: str, abstracts: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Rank abstracts based on semantic similarity to the claim using PubMedBERT.
    Returns the top_k abstracts and their similarity scores.
    """
    claim_vec = embed(claim)
    scores = []
    for abs_text in abstracts:
        abs_vec = embed(abs_text)
        sim = np.dot(claim_vec, abs_vec) / (np.linalg.norm(claim_vec) * np.linalg.norm(abs_vec))
        scores.append((abs_text, float(sim)))
    ranked = sorted(scores, key=lambda x: x[1], reverse=True)
    return ranked[:top_k] 