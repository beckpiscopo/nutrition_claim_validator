

"""Embed and rank PubMed abstracts for relevance using PubMedBERT."""

from typing import List, Tuple
from sentence_transformers import SentenceTransformer, util

# Load PubMedBERT model
model = SentenceTransformer("pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb")

def rank_abstracts(claim: str, abstracts: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Rank abstracts based on semantic similarity to the claim.

    Args:
        claim (str): The health or nutrition claim.
        abstracts (List[str]): List of paper abstracts.
        top_k (int): Number of top abstracts to return.

    Returns:
        List[Tuple[str, float]]: Top abstracts and their similarity scores.
    """
    # Encode claim and abstracts
    claim_embedding = model.encode(claim, convert_to_tensor=True)
    abstract_embeddings = model.encode(abstracts, convert_to_tensor=True)

    # Compute cosine similarities
    cosine_scores = util.cos_sim(claim_embedding, abstract_embeddings)[0]

    # Pair abstracts with scores and sort
    scored_abstracts = list(zip(abstracts, cosine_scores.tolist()))
    ranked = sorted(scored_abstracts, key=lambda x: x[1], reverse=True)

    return ranked[:top_k]