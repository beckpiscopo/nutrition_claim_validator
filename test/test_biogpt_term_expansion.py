import logging
import json
from typing import Dict, List, NamedTuple
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
from dotenv import load_dotenv

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
    """Expand a health-related term into its medical/scientific equivalents using BioGPT model."""
    try:
        # Use a natural prompt for each term
        if term.lower() == "ginger":
            prompt = "Ginger is also known as"
        elif term.lower() == "stronger bones":
            prompt = "Scientific terms for stronger bones include"
        elif term.lower() == "vitamin d":
            prompt = "Vitamin D is also called"
        elif term.lower() == "gut health":
            prompt = "Gut health is related to"
        elif term.lower() == "inflammation":
            prompt = "Inflammation involves"
        else:
            prompt = f"Scientific terms for {term} include"

        # Tokenize and generate
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(
            inputs["input_ids"],
            max_length=32 + len(inputs["input_ids"][0]),
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            top_p=0.95,
            repetition_penalty=1.1
        )

        # Decode the output
        expanded_terms_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove the prompt from the response
        expanded_terms_text = expanded_terms_text[len(prompt):].strip()
        # Split on common delimiters
        terms = [t.strip().lstrip('0123456789.-() ') for t in expanded_terms_text.split(',') if t.strip()]

        return {
            "original_term": term,
            "scientific_terms": terms,
            "full_expansion": expanded_terms_text
        }
    except Exception as e:
        logger.error(f"Error expanding term: {e}")
        raise

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