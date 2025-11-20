import os
import pandas as pd
import numpy as np
from datasets import load_dataset
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def main():
    print("=== RAG Retrieval Quality Evaluation ===\n")

    # 1. Load and Prepare Dataset
    print("1. Loading dataset...")
    try:
        dataset = load_dataset("jacob-hugging-face/job-descriptions", split="train")
        
        # Take a sample of 1000 jobs to keep processing fast
        # Shuffle first to get a random sample
        sampled_dataset = dataset.shuffle(seed=42).select(range(1000))
        
        print(f"   Loaded {len(sampled_dataset)} jobs.")
        
    except Exception as e:
        print(f"   Error loading dataset: {e}")
        # Fallback to dummy data if dataset fails
        sampled_dataset = [
            {"job_description": "Senior Python Developer needed...", "position_title": "Python Developer", "company_name": "Tech Corp"},
            {"job_description": "Marketing Manager for NYC firm...", "position_title": "Marketing Manager", "company_name": "Ad Agency"}
        ]

    # 2. Initialize Embeddings and Vector Store
    print("\n2. Initializing Vector Store...")

    # Initialize Embeddings (matching production setup)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    # Prepare documents for ingestion
    documents = []
    for item in sampled_dataset:
        # Extract fields, handling potential missing keys
        content = item.get("job_description", "") or item.get("description", "")
        title = item.get("position_title", "") or item.get("title", "") or item.get("job_title", "")
        company = item.get("company_name", "") or item.get("company", "")
        
        if content:
            doc = Document(
                page_content=content,
                metadata={
                    "job_title": title,
                    "company": company
                }
            )
            documents.append(doc)

    print(f"   Prepared {len(documents)} documents for ingestion.")

    # Create In-Memory ChromaDB Client for isolation
    client = chromadb.EphemeralClient()

    # Create Vector Store
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        client=client,
        collection_name="evaluation_jobs"
    )

    print("   Vector Store initialized and populated.")

    # 3. Define Synthetic User Personas/Queries
    synthetic_queries = [
        "Senior Python Developer with Flask and AWS experience",
        "Junior Marketing Manager in New York",
        "Data Scientist specializing in NLP and TensorFlow",
        "Project Manager for construction projects",
        "Sales Representative for medical devices",
        "DevOps Engineer with Kubernetes and CI/CD skills",
        "Graphic Designer with Adobe Creative Suite experience",
        "Accountant with CPA certification",
        "Human Resources Specialist for tech startup",
        "Customer Support Agent bilingual Spanish"
    ]

    print(f"\n3. Defined {len(synthetic_queries)} synthetic queries for evaluation.")

    # 4. Run Evaluation Experiment
    results = []
    K = 10

    print(f"\n4. Running evaluation with K={K}...")

    for query in synthetic_queries:
        print(f"   Processing: '{query}'...")
        # Retrieve Documents
        retrieved_docs = vector_store.similarity_search(query, k=K)
        
        # Determine Relevance (Ground Truth)
        relevance_mask = [is_relevant(query, doc) for doc in retrieved_docs]
        
        # Calculate Total Relevant in Dataset (for Recall)
        total_relevant = 0
        for doc in documents:
            if is_relevant(query, doc):
                total_relevant += 1
                
        # Calculate Metrics
        p_at_k = calculate_precision_at_k(relevance_mask, K)
        r_at_k = calculate_recall_at_k(relevance_mask, total_relevant, K)
        
        results.append({
            "Query": query,
            "Precision@10": p_at_k,
            "Recall@10": r_at_k,
            "Total Relevant Found": sum(relevance_mask),
            "Total Relevant Exist": total_relevant,
            "Top Match": retrieved_docs[0].metadata.get("job_title", "N/A")
        })

    # 5. Results and Visualization
    df_results = pd.DataFrame(results)

    # Calculate Averages
    avg_precision = df_results["Precision@10"].mean()
    avg_recall = df_results["Recall@10"].mean()

    print("\n" + "="*60)
    print("RETRIEVAL EVALUATION RESULTS")
    print("="*60)
    print(f"Average Precision@{K}: {avg_precision:.4f}")
    print(f"Average Recall@{K}:    {avg_recall:.4f}")
    print("-"*60)

    # Display DataFrame
    pd.set_option('display.max_colwidth', 50)
    pd.set_option('display.width', 1000)
    print("\nDetailed Query Performance:")
    print(df_results[["Query", "Precision@10", "Recall@10", "Total Relevant Found", "Total Relevant Exist"]])

# --- Helper Functions ---

def extract_keywords(query):
    """Simple keyword extraction from query (removes stopwords)"""
    stopwords = {"with", "and", "in", "for", "the", "a", "an", "of", "to", "experience", "specializing", "skills"}
    words = query.lower().replace(",", "").split()
    keywords = [w for w in words if w not in stopwords]
    return keywords

def is_relevant(query, retrieved_doc):
    """
    Heuristic to determine if a retrieved document is relevant to the query.
    """
    keywords = extract_keywords(query)
    
    job_title = retrieved_doc.metadata.get("job_title", "").lower()
    job_desc = retrieved_doc.page_content.lower()[:500] # Check first 500 chars of desc too
    
    # 1. Title Match (High Confidence)
    for keyword in keywords:
        if keyword in job_title:
            return True
            
    # 2. Description Match (Secondary)
    matches = sum(1 for k in keywords if k in job_desc)
    if matches >= 2:  # Require at least 2 keyword matches in description
        return True
        
    return False

def calculate_precision_at_k(relevant_docs, k):
    """Calculate Precision@K."""
    if k == 0: return 0.0
    relevant_in_k = relevant_docs[:k]
    return sum(relevant_in_k) / k

def calculate_recall_at_k(relevant_docs, total_relevant_in_dataset, k):
    """Calculate Recall@K."""
    if total_relevant_in_dataset == 0: return 0.0
    relevant_in_k = relevant_docs[:k]
    return sum(relevant_in_k) / total_relevant_in_dataset

if __name__ == "__main__":
    main()

