# 🥑 Nutrition-Claim Validator

Validate nutrition and health claims (e.g., "heart healthy", "lowers cortisol") against published scientific research from PubMed using advanced AI models.

---

## ✨ Why it matters
Misleading nutrition and health claims erode consumer trust.  
This tool provides a transparent, evidence-based validation for each claim:

1. **Extracts Claims** using FLAN-T5 to identify the main subject and effect
2. **Enriches Terms** using BioGPT to identify relevant biomedical terminology
3. **Searches PubMed** for relevant clinical trials and systematic reviews
4. **Analyzes the evidence** to determine if claims are supported by scientific research
5. **Publishes** the result as a Knowledge Asset on the OriginTrail DKG for anyone to query

---

## 🚀 Quick-start

```bash
# 1 · clone and enter
git clone https://github.com/your-handle/nutrition-claim-validator.git
cd nutrition-claim-validator

# 2 · create & activate env
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3 · set secrets
cp .env.example .env         # then add your keys
#   NCBI_EMAIL=your.email@example.com
#   NCBI_API_KEY=your_api_key_here  # optional
#   DKG_RPC_URL=https://...
#   WALLET_PRIVATE_KEY=...

# 4 · run the Streamlit demo
streamlit run app.py
```

## Features

1. **AI-Powered Claim Extraction**: Uses FLAN-T5 to identify the main subject and effect from health claims
2. **Biomedical Term Enrichment**: Leverages BioGPT to identify scientific names, active compounds, and medical terminology
3. **Scientific Evidence**: Searches PubMed for clinical trials and systematic reviews supporting or refuting claims
4. **Comprehensive Analysis**: Evaluates multiple studies to provide a balanced view of the evidence
5. **Transparent Results**: Shows detailed information about supporting research, including:
   - Study titles and authors
   - Publication dates and journals
   - Abstracts and key findings
6. **Rate Limited**: Respects PubMed's API guidelines to ensure reliable access

## Project Structure

- `models/`: Contains scripts for model training, testing, and data preparation
  - `test_t5_zero_shot.py`: Tests the FLAN-T5 model for claim extraction
  - `test_biogpt_only.py`: Tests the BioGPT model for biomedical term enrichment
  - `train_t5_claim_extractor.py`: Script for fine-tuning the FLAN-T5 model
  - `prepare_t5_data.py`: Prepares training data for the FLAN-T5 model
- `src/`: Core functionality for claim validation and evidence gathering
- `app.py`: Streamlit web interface for the validator

## Current Progress

- Successfully integrated FLAN-T5 for claim extraction
- Implemented BioGPT for enriching extracted terms with biomedical knowledge
- Facing memory issues with BioGPT on macOS, exploring solutions like using smaller models or running on CPU

## Future Work

- Resolve memory issues with BioGPT
- Improve the accuracy and robustness of claim extraction and term enrichment
- Expand the dataset for better model performance
- Enhance the evidence gathering and analysis pipeline
- Improve the user interface and experience

## Requirements

- Python 3.7+
- biopython>=1.81
- requests>=2.31.0
- python-dotenv>=1.0.0
- transformers>=4.30.0
- torch>=2.0.0
- streamlit>=1.22.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [NCBI PubMed](https://www.ncbi.nlm.nih.gov/home/develop/api/) for scientific literature access
- [OriginTrail DKG](https://docs.origintrail.io/build-with-dkg) for decentralized knowledge storage
- [Hugging Face](https://huggingface.co/) for providing the FLAN-T5 and BioGPT models
