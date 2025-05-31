"""Extract nutrition claims from tweets using LLM."""

from typing import Dict, Optional
import os
from dotenv import load_dotenv
import openai
import diskcache
import json

load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize diskcache
cache = diskcache.Cache('.cache')

SYSTEM_PROMPT = """You are a nutrition claim extractor. Your job is to:
1. Identify if a tweet contains a nutrition or health claim.
2. Extract the specific claim in a standardized format.
3. If a claim is found, return a JSON object with "subject" (the main intervention or thing being claimed) and "object" (the main outcome or effect).
4. If no claim is found, return null.

Examples:
Tweet: "Just learned that chia seeds are great for heart health!"
Output: {"subject": "chia seeds", "object": "heart health"}

Tweet: "Studies show that turmeric reduces inflammation"
Output: {"subject": "turmeric", "object": "inflammation"}

Tweet: "This new protein shake has 30g of protein per serving"
Output: null

Tweet: "Just had the best smoothie ever!"
Output: null
"""

PAPER_ANALYSIS_PROMPT = """
You are a scientific paper analyzer. Your job is to:
1. Read the paper's title and abstract
2. Classify the paper's relevance to the claim as one of:
   - DIRECT: The paper studies the specific subject and outcome in the claim.
   - INDIRECT: The paper studies a related subject or outcome, but not both.
   - CONTEXTUAL: The paper provides background information but does not address the claim directly.
   - NOT RELEVANT: The paper is not relevant to the claim.
3. Score each component of the paper's quality (0-1 scale):
   a) Study Design (0-1):
      - 1.0: Meta-analysis/systematic review
      - 0.9: Randomized controlled trial
      - 0.8: Controlled clinical trial
      - 0.7: Cohort study
      - 0.6: Case-control study
      - 0.5: Cross-sectional study
      - 0.4: Case series/report
      - 0.3: Review article
      - 0.2: Opinion/commentary
      - 0.1: Other
   
   b) Sample Size (0-1):
      - 1.0: >1000 participants
      - 0.9: 500-1000 participants
      - 0.8: 200-499 participants
      - 0.7: 100-199 participants
      - 0.6: 50-99 participants
      - 0.5: 20-49 participants
      - 0.4: 10-19 participants
      - 0.3: 5-9 participants
      - 0.2: 2-4 participants
      - 0.1: Single case
   
   c) Directness (0-1):
      - 1.0: Directly measures the exact outcome in the claim
      - 0.8: Measures a closely related outcome
      - 0.6: Measures a surrogate outcome
      - 0.4: Indirect evidence
      - 0.2: Very indirect evidence
   
   d) Statistical Significance (0-1):
      - 1.0: p < 0.001
      - 0.9: p < 0.01
      - 0.8: p < 0.05
      - 0.6: p < 0.1
      - 0.4: Not statistically significant
      - 0.2: No statistical analysis
   
   e) Study Quality (0-1):
      - 1.0: High quality, well-controlled, minimal bias
      - 0.8: Good quality, some limitations
      - 0.6: Moderate quality, notable limitations
      - 0.4: Low quality, significant limitations
      - 0.2: Very low quality, major limitations

4. Calculate the overall confidence score as the weighted average:
   - Study Design: 30%
   - Sample Size: 20%
   - Directness: 25%
   - Statistical Significance: 15%
   - Study Quality: 10%

5. If relevant, provide a concise summary of the key findings.
6. Determine if the paper supports, contradicts, or is neutral regarding the claim.
7. Explain your reasoning.

Format your response as:
RELEVANCE: [DIRECT/INDIRECT/CONTEXTUAL/NOT RELEVANT]
CONFIDENCE_SCORES:
- Study Design: [0-1]
- Sample Size: [0-1]
- Directness: [0-1]
- Statistical Significance: [0-1]
- Study Quality: [0-1]
OVERALL_CONFIDENCE: [0-1]
CONFIDENCE_REASON: [1-2 sentences justifying the overall confidence score]
SUMMARY: [2-3 sentences summarizing the key findings, or 'N/A' if not relevant]
VALIDITY: [SUPPORTS/CONTRADICTS/NEUTRAL/N/A]
REASONING: [1-2 sentences explaining why]

IMPORTANT: Each confidence score must be on its own line starting with "- " and must include both the component name and score separated by a colon.
"""

def extract_claim(tweet: str) -> Optional[dict]:
    """
    Extract a nutrition claim from a tweet using GPT-4, returning subject/object as a dict.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Tweet: {tweet}\nOutput:"}
            ],
            temperature=0.1,  # Low temperature for more consistent outputs
            max_tokens=100
        )
        claim = response.choices[0].message.content.strip()
        if claim.lower() in ["null", "none", "no claim", ""]:
            return None
        try:
            return json.loads(claim)
        except Exception:
            return None
    except Exception as e:
        print(f"Error extracting claim: {e}")
        return None

def analyze_paper(paper: Dict, claim: str) -> Dict:
    pmid = paper.get('pmid', '')
    cache_key = f"llm_analysis::{claim}::{pmid}"
    if cache_key in cache:
        print(f"[CACHE HIT] {cache_key}")
        return cache[cache_key]
    print(f"[CACHE MISS] {cache_key}")
    try:
        paper_text = f"Title: {paper['title']}\nAbstract: {paper['abstract']}"
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": PAPER_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Claim: {claim}\n\nPaper:\n{paper_text}"}
            ],
            temperature=0.1
        )
        analysis = response.choices[0].message.content.strip()
        
        # Parse the analysis
        relevance = ""
        confidence_scores = {}
        overall_confidence = 0.0
        confidence_reason = ""
        summary = ""
        validity = ""
        reasoning = ""
        
        in_confidence_scores = False
        for line in analysis.split('\n'):
            line = line.strip()
            if line.startswith('RELEVANCE:'):
                relevance = line.replace('RELEVANCE:', '').strip()
            elif line.startswith('CONFIDENCE_SCORES:'):
                in_confidence_scores = True
            elif line.startswith('OVERALL_CONFIDENCE:'):
                in_confidence_scores = False
                try:
                    overall_confidence = float(line.replace('OVERALL_CONFIDENCE:', '').strip())
                except Exception:
                    overall_confidence = 0.0
            elif in_confidence_scores and line.startswith('- '):
                # Parse confidence score line
                try:
                    component, score = line.replace('- ', '').split(':')
                    confidence_scores[component.strip()] = float(score.strip())
                except Exception:
                    continue
            elif line.startswith('CONFIDENCE_REASON:'):
                confidence_reason = line.replace('CONFIDENCE_REASON:', '').strip()
            elif line.startswith('SUMMARY:'):
                summary = line.replace('SUMMARY:', '').strip()
            elif line.startswith('VALIDITY:'):
                validity = line.replace('VALIDITY:', '').strip()
            elif line.startswith('REASONING:'):
                reasoning = line.replace('REASONING:', '').strip()
        
        result = {
            "relevance": relevance,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_confidence,
            "confidence_reason": confidence_reason,
            "summary": summary,
            "validity": validity,
            "reasoning": reasoning
        }
        cache[cache_key] = result
        print(f"[CACHE WRITE] {cache_key}")
        return result
        
    except Exception as e:
        print(f"Error analyzing paper: {e}")
        return {
            "relevance": "NOT RELEVANT",
            "confidence_scores": {},
            "overall_confidence": 0.0,
            "confidence_reason": "Error analyzing paper",
            "summary": "Error analyzing paper",
            "validity": "UNKNOWN",
            "reasoning": str(e)
        }

def llm_build_pubmed_query(claim: str) -> str:
    cache_key = f"llm_query::{claim}"
    if cache_key in cache:
        print(f"[CACHE HIT] {cache_key}")
        return cache[cache_key]
    print(f"[CACHE MISS] {cache_key}")
    QUERY_PROMPT = '''
You are an expert biomedical information scientist. Given the following health or nutrition claim, generate a PubMed query that will return only papers that are directly relevant to the claim.
- Use phrase searching where appropriate (e.g., "skin elasticity").
- Require that all key concepts (intervention and outcome) are present in the paper.
- Use strict AND logic.
- Only include synonyms if they are truly equivalent and would not broaden the search to indirect evidence.
- Output only the PubMed query, nothing else.

Claim: {claim}
PubMed Query:
'''
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a biomedical information retrieval expert."},
                {"role": "user", "content": QUERY_PROMPT.format(claim=claim)}
            ],
            temperature=0.1,
            max_tokens=200
        )
        query = response.choices[0].message.content.strip()
        cache[cache_key] = query
        print(f"[CACHE WRITE] {cache_key}")
        return query
    except Exception as e:
        print(f"Error building PubMed query with LLM: {e}")
        return ""

def main():
    """Test the claim extractor with example tweets."""
    test_tweets = [
        "Just learned that chia seeds are great for heart health!",
        "This new protein shake has 30g of protein per serving",
        "Studies show that turmeric reduces inflammation",
        "Just had the best smoothie ever!"
    ]
    
    for tweet in test_tweets:
        claim = extract_claim(tweet)
        print("Input tweet:", tweet)
        print("Extracted claim:", claim)

    # Calculate truth score
    score = 0
    weight_sum = 0
    for paper in analyzed_papers:
        if paper["relevance"] == "NOT RELEVANT":
            continue
        rel_weight = {"DIRECT": 1.0, "INDIRECT": 0.5, "CONTEXTUAL": 0.2}.get(paper["relevance"], 0)
        conf = paper["overall_confidence"]
        if paper["validity"] == "SUPPORTS":
            score += rel_weight * conf
        elif paper["validity"] == "CONTRADICTS":
            score -= rel_weight * conf
        weight_sum += rel_weight * conf
    truth_score = score / weight_sum if weight_sum else 0

if __name__ == "__main__":
    main() 