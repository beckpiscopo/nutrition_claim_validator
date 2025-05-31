from src.pubmedbert_relevance import rank_relevance

if __name__ == "__main__":
    claim = "ginger reduces pain from period cramping"
    abstracts = [
        "Ginger has been shown to reduce symptoms of dysmenorrhea in several clinical trials.",
        "A randomized controlled trial found that ginger supplementation alleviated menstrual pain in young women.",
        "This study investigates the effects of turmeric on inflammation.",
        "The role of vitamin D in bone health is well established.",
        "Ginger is commonly used as a spice and has antioxidant properties."
    ]
    top_results = rank_relevance(claim, abstracts, top_k=3)
    print("Top relevant abstracts:")
    for i, (abstract, score) in enumerate(top_results, 1):
        print(f"{i}. Score: {score:.3f}\n   Abstract: {abstract}\n") 