"""Streamlit app for testing nutrition claim validation."""

import streamlit as st
from src.claim_extractor import extract_claim, analyze_paper
from src.evidence import get_evidence
from src.pubmedbert_relevance import rank_relevance
import pandas as pd

def get_score_description(component: str, score: float) -> str:
    """Return a description of what the score means for each component."""
    descriptions = {
        "Study Design": {
            1.0: "Meta-analysis/systematic review",
            0.9: "Randomized controlled trial",
            0.8: "Controlled clinical trial",
            0.7: "Cohort study",
            0.6: "Case-control study",
            0.5: "Cross-sectional study",
            0.4: "Case series/report",
            0.3: "Review article",
            0.2: "Opinion/commentary",
            0.1: "Other"
        },
        "Sample Size": {
            1.0: ">1000 participants",
            0.9: "500-1000 participants",
            0.8: "200-499 participants",
            0.7: "100-199 participants",
            0.6: "50-99 participants",
            0.5: "20-49 participants",
            0.4: "10-19 participants",
            0.3: "5-9 participants",
            0.2: "2-4 participants",
            0.1: "Single case"
        },
        "Directness": {
            1.0: "Directly measures the exact outcome",
            0.8: "Measures a closely related outcome",
            0.6: "Measures a surrogate outcome",
            0.4: "Indirect evidence",
            0.2: "Very indirect evidence"
        },
        "Statistical Significance": {
            1.0: "p < 0.001",
            0.9: "p < 0.01",
            0.8: "p < 0.05",
            0.6: "p < 0.1",
            0.4: "Not statistically significant",
            0.2: "No statistical analysis"
        },
        "Study Quality": {
            1.0: "High quality, well-controlled, minimal bias",
            0.8: "Good quality, some limitations",
            0.6: "Moderate quality, notable limitations",
            0.4: "Low quality, significant limitations",
            0.2: "Very low quality, major limitations"
        }
    }
    
    # Find the closest score description
    if component in descriptions:
        scores = sorted(descriptions[component].keys())
        closest_score = min(scores, key=lambda x: abs(x - score))
        return descriptions[component][closest_score]
    return "No description available"

def make_confidence_table(df):
    html = "<table style='width:100%; border-collapse:collapse;'>"
    html += "<tr><th style='background:#f0f4fa;'>Criteria</th><th>Description</th><th>Score</th></tr>"
    for _, row in df.iterrows():
        html += (
            f"<tr>"
            f"<td style='background:#f0f4fa;'>{row['Criteria']}</td>"
            f"<td>{row['Description']}</td>"
            f"<td style='text-align:center; font-weight:bold;'>{row['Score']}</td>"
            f"</tr>"
        )
    html += "</table>"
    return html

st.set_page_config(
    page_title="Nutrition Claim Validator",
    page_icon="🥑",
    layout="wide"
)

st.title("🥑 Nutrition Claim Validator")
st.markdown("""
This tool helps validate nutrition and health claims using scientific evidence from PubMed.
Paste a tweet or text containing a nutrition claim, and we'll analyze it for you.
""")

# Move example tweets above the text area
st.markdown("---")
st.markdown("### Example Claims")
example_tweets = [
    "Just learned that chia seeds are great for heart health!",
    "Studies show that turmeric reduces inflammation",
    "A plant-based diet is better for cardiovascular health"
]
cols = st.columns(len(example_tweets))
for i, tweet in enumerate(example_tweets):
    with cols[i]:
        if st.button(tweet, key=tweet):
            st.session_state["tweet"] = tweet
            st.experimental_rerun()

# Input text area
# Use st.session_state["tweet"] as the default value if set
text_value = st.session_state.get("tweet", "")
tweet = st.text_area(
    "Paste your tweet or text here:",
    height=100,
    value=text_value,
    placeholder="Example: 'Just learned that chia seeds are great for heart health!'"
)

# Use columns to group the controls on the same line
st.markdown("#### Filters")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    max_papers = st.slider(
        "Maximum number of papers to return",
        min_value=1,
        max_value=100,
        value=5,
        label_visibility="collapsed"
    )
with col2:
    human_only = st.checkbox("Humans only", value=True, help="Restrict results to human studies", label_visibility="collapsed")
with col3:
    pub_types = st.multiselect(
        "Publication types (optional)",
        options=["Clinical Trial", "Review", "Meta-Analysis", "Randomized Controlled Trial", "Case Reports"],
        label_visibility="collapsed"
    )
st.markdown(
    "<div style='display: flex; justify-content: space-between; margin-bottom: 0.5em;'>"
    "<span>Max papers</span>"
    "<span>Humans only</span>"
    "<span>Publication type(s)</span>"
    "</div>",
    unsafe_allow_html=True
)

if st.button("Analyze Claim"):
    if tweet:
        with st.spinner("Analyzing..."):
            try:
                # Extract claim
                claim_dict = extract_claim(tweet)
                print("Extracted claim:", claim_dict)
                
                if claim_dict and isinstance(claim_dict, dict):
                    subject = claim_dict.get("subject", "")
                    outcome = claim_dict.get("object", "")
                    st.success(f"✅ Found claim: '{claim_dict}'")
                    
                    # Fetch more papers than needed to allow for relevance filtering
                    fetch_count = min(max_papers * 3, 100)  # Start with fewer papers
                    evidence = get_evidence(
                        subject,
                        outcome,
                        max_results=fetch_count,
                        human_only=human_only,
                        publication_types=pub_types if pub_types else None
                    )
                    print("Evidence result:", evidence)
                    st.info(f"PubMed Query: {evidence['query']}")
                    
                    if evidence["valid"]:
                        st.markdown("### 📚 Scientific Evidence")
                        
                        # PubMedBERT pre-filter: rank and select top N papers
                        papers = evidence["evidence"]
                        abstracts = [paper["abstract"] for paper in papers]
                        top_k = max_papers
                        ranked = rank_relevance(subject + " " + outcome, abstracts, top_k=top_k)
                        top_abstracts = set(abs_text for abs_text, _ in ranked)
                        filtered_papers = [paper for paper in papers if paper["abstract"] in top_abstracts]
                        
                        # Track overall validity
                        supporting_papers = 0
                        contradicting_papers = 0
                        neutral_papers = 0
                        relevant_count = 0
                        
                        analyzed_papers = []
                        for i, paper in enumerate(filtered_papers, 1):
                            if relevant_count >= max_papers:
                                break
                            print("Paper:", paper)
                            analysis = analyze_paper(paper, subject + " " + outcome)
                            print("Analysis:", analysis)
                            if analysis["relevance"] == "NOT RELEVANT":
                                continue
                            relevant_count += 1
                            analyzed_papers.append((paper, analysis))
                            with st.expander(paper['title']):
                                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"
                                st.markdown(
                                    f"<h4 style='margin-bottom:0'><a href='{pubmed_url}' target='_blank'>{paper['title']}</a></h4>",
                                    unsafe_allow_html=True
                                )
                                # Update validity counts
                                if analysis["validity"] == "SUPPORTS":
                                    supporting_papers += 1
                                elif analysis["validity"] == "CONTRADICTS":
                                    contradicting_papers += 1
                                else:
                                    neutral_papers += 1
                                
                                # Display paper details
                                if paper["authors"]:
                                    author_lines = []
                                    for author in paper["authors"]:
                                        if isinstance(author, dict):
                                            author_line = f"{author.get('fore_name', '')} {author.get('last_name', '')}".strip()
                                            if author.get("initials"):
                                                author_line += f" ({author['initials']})"
                                            if author.get("affiliation"):
                                                author_line += f", *{author['affiliation']}*"
                                            if author.get("orcid"):
                                                author_line += f" [ORCID](https://orcid.org/{author['orcid']})"
                                            author_lines.append(author_line)
                                        else:
                                            author_lines.append(str(author))
                                    st.markdown(f"**Authors:** {', '.join(author_lines)}")
                                st.markdown(f"**Journal:** {paper['journal']} ({paper['publication_date']})")
                                st.markdown(f"**Abstract:** {paper['abstract']}")
                                
                                # Show new fields if present
                                if paper.get("methods"):
                                    st.markdown(f"**Methods:** {paper['methods']}")
                                if paper.get("results"):
                                    st.markdown(f"**Results:** {paper['results']}")
                                if paper.get("conclusions"):
                                    st.markdown(f"**Conclusions:** {paper['conclusions']}")
                                if paper.get("keywords"):
                                    st.markdown(f"**Keywords:** {', '.join(paper['keywords'])}")
                                if paper.get("grants") and len(paper["grants"]):
                                    st.markdown("**Grants/Funding:**")
                                    for grant in paper["grants"]:
                                        st.markdown(f"- {grant}")
                                
                                # Display analysis
                                st.markdown("### 📊 Analysis")
                                st.markdown(f"**Relevance:** {analysis['relevance']}")
                                
                                # Display confidence scores as a DataFrame
                                confidence_scores = analysis.get('confidence_scores', {})
                                if confidence_scores:
                                    df = pd.DataFrame([
                                        {
                                            "Criteria": component,
                                            "Description": get_score_description(component, score),
                                            "Score": round(score, 2)
                                        }
                                        for component, score in confidence_scores.items()
                                    ])
                                    st.markdown(make_confidence_table(df), unsafe_allow_html=True)
                                    # Display overall confidence
                                    st.markdown(f"**Overall Confidence:** `{analysis['overall_confidence']:.2f}`")
                                    st.markdown(f"<details><summary>How was this confidence score determined?</summary>{analysis.get('confidence_reason', 'N/A')}</details>", unsafe_allow_html=True)
                                else:
                                    st.markdown("No confidence scores available")
                                
                                st.markdown(f"**Summary:** {analysis['summary']}")
                                
                                # Color-code the validity
                                validity_color = {
                                    "SUPPORTS": "green",
                                    "CONTRADICTS": "red",
                                    "NEUTRAL": "orange"
                                }.get(analysis["validity"], "gray")
                                
                                st.markdown(f"**Validity:** :{validity_color}[{analysis['validity']}]")
                                st.markdown(f"**Reasoning:** {analysis['reasoning']}")
                        
                        # Display overall validity assessment
                        st.markdown("### 🎯 Overall Assessment")
                        st.markdown(f"""
                        - ✅ Supporting papers: {supporting_papers}
                        - ❌ Contradicting papers: {contradicting_papers}
                        - ⚖️ Neutral papers: {neutral_papers}
                        """)
                        
                        # Make a final decision
                        if supporting_papers > contradicting_papers:
                            st.success("This claim appears to be supported by the scientific literature.")
                        elif contradicting_papers > supporting_papers:
                            st.error("This claim appears to be contradicted by the scientific literature.")
                        else:
                            st.warning("The scientific evidence is inconclusive for this claim.")
                            
                        # Calculate truth score
                        truth_score = 0
                        weight_sum = 0
                        score_breakdown = []
                        for paper, analysis in analyzed_papers:
                            rel_weight = {"DIRECT": 1.0, "INDIRECT": 0.5, "CONTEXTUAL": 0.2}.get(analysis["relevance"], 0)
                            conf = analysis["overall_confidence"]
                            contrib = 0
                            if analysis["validity"] == "SUPPORTS":
                                contrib = rel_weight * conf
                            elif analysis["validity"] == "CONTRADICTS":
                                contrib = -rel_weight * conf
                            # NEUTRAL/N/A contribute 0
                            truth_score += contrib
                            weight_sum += rel_weight * conf
                            score_breakdown.append({
                                "title": paper["title"],
                                "pmid": paper.get("pmid"),
                                "relevance": analysis["relevance"],
                                "confidence": conf,
                                "validity": analysis["validity"],
                                "contribution": contrib
                            })
                        final_truth_score = truth_score / weight_sum if weight_sum else 0
                        
                        st.markdown("### 🧮 Truth Score")
                        st.markdown(f"**Truth Score:** `{final_truth_score:.2f}` (range: -1 to 1)")
                        
                        with st.expander("See score breakdown by paper"):
                            for item in score_breakdown:
                                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/"
                                st.markdown(
                                    f"- **[{' '.join(item['title'].split())}]({pubmed_url})** (PMID: {item['pmid']})<br>"
                                    f"  Relevance: `{item['relevance']}` | Confidence: `{item['confidence']}` | "
                                    f"Validity: `{item['validity']}` | Contribution: `{item['contribution']:.2f}`",
                                    unsafe_allow_html=True
                                )
                            
                        # Add "Load More" button if we have more papers to fetch
                        if len(analyzed_papers) < max_papers and len(evidence["evidence"]) >= fetch_count:
                            if st.button("Load More Papers"):
                                # Fetch next batch
                                next_batch = get_evidence(
                                    subject,
                                    outcome,
                                    max_results=fetch_count,
                                    human_only=human_only,
                                    publication_types=pub_types if pub_types else None
                                )
                                if next_batch["valid"]:
                                    st.experimental_rerun()
                        
                    else:
                        st.warning("❌ No scientific evidence found for this claim.")
                else:
                    st.info("ℹ️ No nutrition claim found in the text.")
            except Exception as e:
                print("Error at STEP_NAME:", e)
                raise
    else:
        st.warning("Please enter some text to analyze.") 