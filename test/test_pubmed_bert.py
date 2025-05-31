from pubmed_bert import rank_abstracts

claim = "Ashwagandha reduces cortisol"
abstracts = [
    "Ashwagandha is an adaptogenic herb traditionally used to combat stress and anxiety.",
    "Vitamin D plays a crucial role in bone health and immune function.",
    "In a randomized trial, subjects taking ashwagandha showed significantly lower cortisol levels than placebo.",
    "Omega-3 fatty acids have been associated with reduced inflammation and heart disease risk."
]

top_results = rank_abstracts(claim, abstracts, top_k=3)

for i, (abstract, score) in enumerate(top_results, start=1):
    print(f"Rank {i}:")
    print(f"Score: {score:.4f}")
    print(f"Abstract: {abstract}\n")