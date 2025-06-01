import requests
import logging
import json
from typing import Dict, List, Tuple, NamedTuple
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Hugging Face API token from environment
HF_ACCESS_TOKEN = os.getenv("HF_ACCESS_TOKEN")
if not HF_ACCESS_TOKEN:
    raise ValueError("HF_ACCESS_TOKEN not found in environment variables")

# API configuration
API_URL = "https://api-inference.huggingface.co/models/bigscience/mt0-base"
headers = {"Authorization": f"Bearer {HF_ACCESS_TOKEN}"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaimExample(NamedTuple):
    claim: str
    expected_terms: List[str]

def analyze_claim(text: str) -> Dict:
    """Analyze a health claim to identify key terms using Hugging Face Inference API."""
    try:
        # Simple prompt for term extraction
        prompt = f"Extract subject and object: {text}"
        
        # Make API request
        data = {"inputs": prompt}
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        terms_text = result[0]["generated_text"]
        
        # Clean up the terms
        terms = []
        for term in terms_text.split(","):
            term = term.strip()
            # Remove any numbering or bullet points
            term = term.lstrip("0123456789.-() ")
            if term and term not in terms:  # Avoid duplicates
                terms.append(term)
        
        return {
            "original_claim": text,
            "key_terms": terms,
            "full_analysis": terms_text
        }
    except Exception as e:
        logger.error(f"Error analyzing claim: {e}")
        raise

def main():
    # Example claims with expected outputs
    test_claims = [
        ClaimExample(
            "Vitamin C helps with immune system function",
            ["Vitamin C", "immune system"]
        ),
        ClaimExample(
            "Regular consumption of green tea may reduce the risk of heart disease",
            ["green tea", "heart disease"]
        ),
        ClaimExample(
            "Studies suggest that omega-3 fatty acids can improve cognitive function in older adults",
            ["omega-3 fatty acids", "cognitive function"]
        ),
        ClaimExample(
            "Probiotics have been shown to support digestive health",
            ["probiotics", "digestive health"]
        ),
        ClaimExample(
            "Daily meditation practice is associated with reduced stress levels",
            ["meditation", "stress"]
        )
    ]
    
    try:
        # Analyze each claim
        logger.info("Analyzing claims...")
        results = []
        for i, claim_example in enumerate(test_claims, 1):
            print(f"\nClaim {i}:")
            print("-" * 50)
            print(f"Original: {claim_example.claim}")
            
            analysis = analyze_claim(claim_example.claim)
            results.append(analysis)
            
            # Print in a readable format
            print("Analysis:")
            print(json.dumps(analysis, indent=2))
            print("-" * 50)
        
        # Save all results to a JSON file
        with open("claim_analysis_results.json", "w") as f:
            json.dump({"claims": results}, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 