import os
import json
import pandas as pd
import numpy as np
from datasets import load_dataset
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import time

# Load environment variables
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def sanitize_metadata(metadata):
    """
    Sanitize metadata to ensure all values are valid ChromaDB types.
    ChromaDB accepts: str, int, float, bool, None
    Converts None to empty string and ensures all values are valid types.
    """
    sanitized = {}
    for key, value in metadata.items():
        if value is None:
            sanitized[key] = ""  # Convert None to empty string
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list):
            # Convert lists to comma-separated string
            sanitized[key] = ", ".join(str(v) for v in value if v is not None)
        elif isinstance(value, dict):
            # Convert dicts to JSON string
            sanitized[key] = json.dumps(value)
        else:
            # Convert any other type to string
            sanitized[key] = str(value) if value is not None else ""
    return sanitized

def create_vector_store_with_batching(client, documents, embeddings, collection_name, batch_size=100):
    """
    Create vector store with batched uploads to prevent timeouts.
    Uses incremental embedding and upload to handle large datasets.
    """
    print(f"\n   Starting batched upload of {len(documents)} documents...")
    print(f"   Batch size: {batch_size} documents per batch")
    
    # Create empty collection first
    try:
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": "Evaluation job dataset"}
        )
    except Exception as e:
        # Collection might already exist
        try:
            collection = client.get_collection(name=collection_name)
            print(f"   Using existing collection: {collection_name}")
        except:
            raise Exception(f"Failed to create or get collection: {e}")
    
    # Process documents in batches
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    print(f"   Processing {total_batches} batches...")
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(documents))
        batch_docs = documents[start_idx:end_idx]
        
        print(f"   Batch {batch_idx + 1}/{total_batches}: Processing documents {start_idx + 1}-{end_idx}...")
        
        # Prepare batch data
        batch_ids = [f"doc_{start_idx + i}" for i in range(len(batch_docs))]
        batch_texts = [doc.page_content for doc in batch_docs]
        # Sanitize metadata to ensure all values are valid ChromaDB types
        batch_metadatas = [sanitize_metadata(doc.metadata) for doc in batch_docs]
        
        # Generate embeddings for this batch
        try:
            batch_embeddings = embeddings.embed_documents(batch_texts)
        except Exception as e:
            print(f"      Error embedding batch {batch_idx + 1}: {e}")
            # Retry once
            time.sleep(2)
            try:
                batch_embeddings = embeddings.embed_documents(batch_texts)
            except Exception as e2:
                print(f"      Failed to embed batch {batch_idx + 1} after retry. Skipping...")
                continue
        
        # Upload batch to ChromaDB with retry logic
        max_retries = 3
        retry_delay = 5
        
        for retry in range(max_retries):
            try:
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas
                )
                print(f"      ✓ Uploaded batch {batch_idx + 1}/{total_batches} ({len(batch_docs)} documents)")
                break
            except Exception as e:
                if retry < max_retries - 1:
                    wait_time = retry_delay * (retry + 1)
                    print(f"      ⚠ Error uploading batch {batch_idx + 1} (attempt {retry + 1}/{max_retries}): {e}")
                    print(f"      Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"      ✗ Failed to upload batch {batch_idx + 1} after {max_retries} attempts: {e}")
                    raise
        
        # Small delay between batches to avoid rate limiting
        if batch_idx < total_batches - 1:
            time.sleep(0.5)
    
    print(f"\n   ✓ Successfully uploaded all {len(documents)} documents to ChromaDB Cloud!")
    
    # Create and return vector store
    vector_store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    
    return vector_store

def main():
    print("=== RAG Retrieval Quality Evaluation ===\n")

    # 1. Load and Prepare Dataset
    print("1. Loading dataset...")
    try:
        # Load the azrai99/job-dataset from HuggingFace (all ~60k jobs)
        dataset = load_dataset("azrai99/job-dataset", split="train")
        
        print(f"   Loaded {len(dataset)} jobs from azrai99/job-dataset.")
        print(f"   Dataset fields: {list(dataset[0].keys())}")
        print(f"   This may take several minutes to process all jobs...")
        
    except Exception as e:
        print(f"   Error loading dataset: {e}")
        raise  # Re-raise the error since we need the full dataset

    # 2. Initialize Embeddings and Vector Store
    print("\n2. Initializing Vector Store...")

    # Initialize Embeddings (matching production setup)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    # Prepare documents for ingestion
    print("   Processing and preparing documents for vector store...")
    documents = []
    total_items = len(dataset)
    for idx, item in enumerate(dataset):
        if (idx + 1) % 5000 == 0:
            print(f"   Processed {idx + 1}/{total_items} documents...")
        # Extract fields based on azrai99/job-dataset structure
        content = item.get("descriptions", "") or item.get("description", "")
        title = item.get("job_title", "") or item.get("title", "")
        company = item.get("company", "") or item.get("company_name", "")
        location = item.get("location", "")
        category = item.get("category", "")
        subcategory = item.get("subcategory", "")
        role = item.get("role", "")
        job_type = item.get("type", "")
        
        if content:
            doc = Document(
                page_content=content,
                metadata={
                    "job_title": title,
                    "company": company,
                    "location": location,
                    "category": category,
                    "subcategory": subcategory,
                    "role": role,
                    "type": job_type
                }
            )
            documents.append(doc)

    print(f"   Prepared {len(documents)} documents for ingestion.")

    # Connect to ChromaDB Cloud
    chroma_api_key = os.getenv("CHROMA_API_KEY")
    if not chroma_api_key:
        raise ValueError("CHROMA_API_KEY environment variable must be set in .env file")
    
    print("   Connecting to ChromaDB Cloud...")
    client = chromadb.CloudClient(
        api_key=chroma_api_key,
        tenant='361f16d2-3a10-4479-854c-519de88ae973',
        database='job_search_db'
        )
    
    # Create or get collection
    collection_name = "evaluation_jobs"
    print(f"   Using collection: {collection_name}")
    
    # Check if collection exists and get count
    try:
        existing_collection = client.get_collection(name=collection_name)
        existing_count = existing_collection.count()
        print(f"   Found existing collection with {existing_count} documents.")
        
        if existing_count == len(documents):
            print("   Collection already has all documents. Using existing collection.")
            vector_store = Chroma(
        client=client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
        else:
            print(f"   Collection has {existing_count} documents, need {len(documents)}. Will recreate for clean evaluation.")
            # Delete and recreate for clean evaluation
            try:
                client.delete_collection(name=collection_name)
                print("   Deleted existing collection for fresh evaluation.")
            except Exception as del_e:
                print(f"   Warning: Could not delete collection: {del_e}")
            vector_store = create_vector_store_with_batching(
                client, documents, embeddings, collection_name
            )
    except chromadb.errors.NotFoundError:
        # Collection doesn't exist - create it
        print("   Collection doesn't exist. Creating new collection with batched upload...")
        vector_store = create_vector_store_with_batching(
            client, documents, embeddings, collection_name
        )
    except Exception as e:
        print(f"   Error checking collection: {e}")
        print("   Attempting to create new collection with batched upload...")
        vector_store = create_vector_store_with_batching(
            client, documents, embeddings, collection_name
    )

    print("   Vector Store initialized and populated.")

    # 3. Define Comprehensive Synthetic User Personas/Queries
    # These queries test various aspects: experience levels, industries, locations, skills, job types
    synthetic_queries = [
        # Technology & Software Development
        "Senior Python Developer with Flask and AWS cloud experience",
        "Junior Software Engineer with React and JavaScript skills",
        "Full Stack Developer with Node.js and MongoDB experience",
        "DevOps Engineer with Kubernetes, Docker, and CI/CD pipeline expertise",
        "Data Scientist specializing in machine learning and TensorFlow",
        
        # Business & Management
        "Project Manager for construction and infrastructure projects",
        "Account Executive with B2B sales experience in technology sector",
        "Business Analyst with data analysis and SQL skills",
        "Operations Manager for supply chain and logistics",
        "Product Manager with agile methodology experience",
        
        # Finance & Accounting
        "Accountant with CPA certification and financial reporting experience",
        "Financial Analyst with Excel and financial modeling skills",
        "Accounts Executive for accounts payable and receivable management",
        "Audit Assistant with accounting degree and audit experience",
        
        # Sales & Marketing
        "Sales Representative for medical devices and healthcare products",
        "Marketing Manager with digital marketing and social media experience",
        "Business Development Executive for B2B client acquisition",
        "Customer Relationship Manager with account management skills",
        
        # Supply Chain & Procurement
        "Procurement Executive with contract management and supplier relations",
        "Supply Chain Planner with inventory management and forecasting",
        "Logistics Coordinator for warehouse and distribution operations",
        "Purchasing Officer with vendor management experience",
        
        # Human Resources & Administration
        "Human Resources Specialist for recruitment and employee relations",
        "HR Executive with talent acquisition and onboarding experience",
        "Administrative Assistant with office management skills",
        "Executive Assistant with calendar management and travel coordination",
        
        # Engineering & Manufacturing
        "Mechanical Engineer with CAD design and manufacturing experience",
        "Quality Assurance Engineer with testing and quality control",
        "Production Supervisor for manufacturing operations",
        
        # Customer Service & Support
        "Customer Support Agent bilingual in English and Spanish",
        "Customer Service Representative with call center experience",
        "Technical Support Specialist with troubleshooting skills",
        
        # Location-Specific Queries (Malaysia-focused based on dataset)
        "Software Developer position in Kuala Lumpur",
        "Sales Manager job in Selangor",
        "Accountant role in Petaling Jaya",
        
        # Job Type Specific
        "Full-time Marketing Executive position",
        "Contract-based Project Manager role",
        "Part-time Customer Service position",
        
        # Multi-Criteria Complex Queries
        "Senior Data Analyst with Python, SQL, and Tableau experience in Kuala Lumpur",
        "Junior Account Executive with sales experience and own transport in Klang",
        "Procurement Manager with supply chain experience and contract negotiation skills",
        "HR Manager with recruitment experience for tech startup in Malaysia",
        "Supply Chain Planning role with inventory management and S&OP experience"
    ]

    print(f"\n3. Defined {len(synthetic_queries)} comprehensive synthetic queries for evaluation.")
    print("   Query categories: Technology, Business, Finance, Sales, Supply Chain, HR, Engineering, Customer Service, Location-specific, Job Type-specific, Multi-criteria")

    # 4. Run Evaluation Experiment
    results = []
    K = 10
    K_LARGE = 50  # For better recall evaluation

    print(f"\n4. Running evaluation with K={K} (and K={K_LARGE} for recall)...")

    for query_idx, query in enumerate(synthetic_queries, 1):
        print(f"   Processing query {query_idx}/{len(synthetic_queries)}: '{query}'...")
        
        # Retrieve Documents (retrieve more for better recall calculation)
        retrieved_docs = vector_store.similarity_search(query, k=K_LARGE)
        
        # Determine Relevance (Ground Truth) for top K_LARGE
        relevance_mask = [is_relevant(query, doc) for doc in retrieved_docs]
        
        # Calculate Total Relevant in Dataset (for Recall)
        # Note: This scans all documents - with 60k jobs this may take a few minutes per query
        print(f"      Calculating total relevant jobs in dataset (scanning {len(documents)} documents)...")
        total_relevant = 0
        for doc_idx, doc in enumerate(documents):
            if (doc_idx + 1) % 10000 == 0:
                print(f"         Scanned {doc_idx + 1}/{len(documents)} documents...")
            if is_relevant(query, doc):
                total_relevant += 1
        print(f"      Found {total_relevant} relevant jobs in dataset.")
        
        # Calculate metrics at different K values
        p_at_10 = calculate_precision_at_k(relevance_mask, 10)
        r_at_10 = calculate_recall_at_k(relevance_mask, total_relevant, 10)
        r_at_50 = calculate_recall_at_k(relevance_mask, total_relevant, 50)
        
        # Calculate MRR (Mean Reciprocal Rank) - position of first relevant result
        mrr = 0.0
        for rank, is_rel in enumerate(relevance_mask, 1):
            if is_rel:
                mrr = 1.0 / rank
                break
        
        # Calculate NDCG@10 (simplified - treating relevance as binary)
        # NDCG = DCG / IDCG, where DCG = sum(rel_i / log2(i+1))
        dcg = sum((1.0 if rel else 0.0) / np.log2(i + 2) for i, rel in enumerate(relevance_mask[:10]))
        # IDCG: ideal case where all top 10 are relevant
        idcg = sum(1.0 / np.log2(i + 2) for i in range(min(10, total_relevant)))
        ndcg_at_10 = dcg / idcg if idcg > 0 else 0.0
        
        results.append({
            "Query": query,
            "Precision@10": p_at_10,
            "Recall@10": r_at_10,
            "Recall@50": r_at_50,
            "MRR": mrr,
            "NDCG@10": ndcg_at_10,
            "Total Relevant Found (top 10)": sum(relevance_mask[:10]),
            "Total Relevant Found (top 50)": sum(relevance_mask[:50]),
            "Total Relevant Exist": total_relevant,
            "Top Match": retrieved_docs[0].metadata.get("job_title", "N/A") if retrieved_docs else "N/A"
        })

    # 5. Results and Visualization
    df_results = pd.DataFrame(results)

    # Calculate Averages
    avg_precision = df_results["Precision@10"].mean()
    avg_recall_10 = df_results["Recall@10"].mean()
    avg_recall_50 = df_results["Recall@50"].mean()
    avg_mrr = df_results["MRR"].mean()
    avg_ndcg = df_results["NDCG@10"].mean()

    print("\n" + "="*70)
    print("RETRIEVAL EVALUATION RESULTS")
    print("="*70)
    print(f"Average Precision@10:     {avg_precision:.4f} ({avg_precision*100:.2f}%)")
    print(f"Average Recall@10:        {avg_recall_10:.4f} ({avg_recall_10*100:.2f}%)")
    print(f"Average Recall@50:        {avg_recall_50:.4f} ({avg_recall_50*100:.2f}%)")
    print(f"Average MRR:              {avg_mrr:.4f}")
    print(f"Average NDCG@10:          {avg_ndcg:.4f}")
    print("-"*70)
    
    # Additional statistics
    print("\nAdditional Statistics:")
    print(f"Queries with Perfect Precision@10: {sum(df_results['Precision@10'] == 1.0)}/{len(df_results)}")
    print(f"Queries with Zero Precision@10:    {sum(df_results['Precision@10'] == 0.0)}/{len(df_results)}")
    print(f"Median Precision@10:               {df_results['Precision@10'].median():.4f}")
    print(f"Median Recall@50:                  {df_results['Recall@50'].median():.4f}")
    
    # Category analysis (if we can infer categories from queries)
    print("\n" + "-"*70)
    print("Performance by Query Type:")
    print("-"*70)
    
    # Group by query characteristics
    tech_queries = df_results[df_results['Query'].str.contains('Developer|Engineer|Scientist|Software|Data|DevOps', case=False, na=False)]
    business_queries = df_results[df_results['Query'].str.contains('Manager|Executive|Analyst|Business|Sales|Marketing', case=False, na=False)]
    location_queries = df_results[df_results['Query'].str.contains('Kuala Lumpur|Selangor|Petaling|Klang|Malaysia', case=False, na=False)]
    
    if len(tech_queries) > 0:
        print(f"\nTechnology/Engineering Queries ({len(tech_queries)} queries):")
        print(f"  Avg Precision@10: {tech_queries['Precision@10'].mean():.4f}")
        print(f"  Avg Recall@50:    {tech_queries['Recall@50'].mean():.4f}")
        print(f"  Avg MRR:          {tech_queries['MRR'].mean():.4f}")
    
    if len(business_queries) > 0:
        print(f"\nBusiness/Management Queries ({len(business_queries)} queries):")
        print(f"  Avg Precision@10: {business_queries['Precision@10'].mean():.4f}")
        print(f"  Avg Recall@50:    {business_queries['Recall@50'].mean():.4f}")
        print(f"  Avg MRR:          {business_queries['MRR'].mean():.4f}")
    
    if len(location_queries) > 0:
        print(f"\nLocation-Specific Queries ({len(location_queries)} queries):")
        print(f"  Avg Precision@10: {location_queries['Precision@10'].mean():.4f}")
        print(f"  Avg Recall@50:    {location_queries['Recall@50'].mean():.4f}")
        print(f"  Avg MRR:          {location_queries['MRR'].mean():.4f}")

    # Display DataFrame
    pd.set_option('display.max_colwidth', 40)
    pd.set_option('display.width', 1200)
    print("\n" + "="*70)
    print("Detailed Query Performance:")
    print("="*70)
    display_cols = ["Query", "Precision@10", "Recall@10", "Recall@50", "MRR", "NDCG@10", 
                    "Total Relevant Found (top 10)", "Total Relevant Exist"]
    print(df_results[display_cols].to_string(index=False))
    
    # 6. Generate Visualizations
    print("\n" + "="*70)
    print("Generating visualizations...")
    print("="*70)
    
    # Create output directory for charts
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    # Add query categories for better visualization
    df_results['Category'] = df_results['Query'].apply(categorize_query)
    
    # 1. Precision@10 and Recall@50 Comparison Bar Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    x_pos = np.arange(len(df_results))
    width = 0.35
    
    ax1.bar(x_pos, df_results['Precision@10'], width, label='Precision@10', alpha=0.8)
    ax1.axhline(y=avg_precision, color='r', linestyle='--', label=f'Average: {avg_precision:.3f}')
    ax1.set_xlabel('Query Index', fontsize=12)
    ax1.set_ylabel('Precision@10', fontsize=12)
    ax1.set_title('Precision@10 by Query', fontsize=14, fontweight='bold')
    ax1.set_xticks(x_pos[::5])  # Show every 5th query
    ax1.set_xticklabels([f'Q{i+1}' for i in x_pos[::5]], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1.1])
    
    ax2.bar(x_pos, df_results['Recall@50'], width, label='Recall@50', alpha=0.8, color='orange')
    ax2.axhline(y=avg_recall_50, color='r', linestyle='--', label=f'Average: {avg_recall_50:.3f}')
    ax2.set_xlabel('Query Index', fontsize=12)
    ax2.set_ylabel('Recall@50', fontsize=12)
    ax2.set_title('Recall@50 by Query', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos[::5])
    ax2.set_xticklabels([f'Q{i+1}' for i in x_pos[::5]], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'precision_recall_comparison.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'precision_recall_comparison.png'}")
    plt.close()
    
    # 2. MRR and NDCG@10 Comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    ax1.bar(x_pos, df_results['MRR'], width, label='MRR', alpha=0.8, color='green')
    ax1.axhline(y=avg_mrr, color='r', linestyle='--', label=f'Average: {avg_mrr:.3f}')
    ax1.set_xlabel('Query Index', fontsize=12)
    ax1.set_ylabel('MRR', fontsize=12)
    ax1.set_title('Mean Reciprocal Rank (MRR) by Query', fontsize=14, fontweight='bold')
    ax1.set_xticks(x_pos[::5])
    ax1.set_xticklabels([f'Q{i+1}' for i in x_pos[::5]], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1.1])
    
    ax2.bar(x_pos, df_results['NDCG@10'], width, label='NDCG@10', alpha=0.8, color='purple')
    ax2.axhline(y=avg_ndcg, color='r', linestyle='--', label=f'Average: {avg_ndcg:.3f}')
    ax2.set_xlabel('Query Index', fontsize=12)
    ax2.set_ylabel('NDCG@10', fontsize=12)
    ax2.set_title('NDCG@10 by Query', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos[::5])
    ax2.set_xticklabels([f'Q{i+1}' for i in x_pos[::5]], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1.1])
    
    plt.tight_layout()
    plt.savefig(output_dir / 'mrr_ndcg_comparison.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'mrr_ndcg_comparison.png'}")
    plt.close()
    
    # 3. Precision vs Recall Scatter Plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    scatter = ax.scatter(df_results['Recall@50'], df_results['Precision@10'], 
                        c=df_results['MRR'], s=100, alpha=0.6, cmap='viridis')
    ax.set_xlabel('Recall@50', fontsize=12)
    ax.set_ylabel('Precision@10', fontsize=12)
    ax.set_title('Precision@10 vs Recall@50 (colored by MRR)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('MRR', fontsize=12)
    
    # Add average lines
    ax.axhline(y=avg_precision, color='r', linestyle='--', alpha=0.5, label=f'Avg Precision: {avg_precision:.3f}')
    ax.axvline(x=avg_recall_50, color='r', linestyle='--', alpha=0.5, label=f'Avg Recall: {avg_recall_50:.3f}')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_dir / 'precision_vs_recall_scatter.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'precision_vs_recall_scatter.png'}")
    plt.close()
    
    # 4. Category-wise Performance Comparison
    if df_results['Category'].nunique() > 1:
        category_metrics = df_results.groupby('Category').agg({
            'Precision@10': 'mean',
            'Recall@50': 'mean',
            'MRR': 'mean',
            'NDCG@10': 'mean'
        }).round(4)
        
        fig, ax = plt.subplots(figsize=(14, 8))
        x = np.arange(len(category_metrics))
        width = 0.2
        
        ax.bar(x - 1.5*width, category_metrics['Precision@10'], width, label='Precision@10', alpha=0.8)
        ax.bar(x - 0.5*width, category_metrics['Recall@50'], width, label='Recall@50', alpha=0.8)
        ax.bar(x + 0.5*width, category_metrics['MRR'], width, label='MRR', alpha=0.8)
        ax.bar(x + 1.5*width, category_metrics['NDCG@10'], width, label='NDCG@10', alpha=0.8)
        
        ax.set_xlabel('Query Category', fontsize=12)
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Average Performance Metrics by Query Category', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(category_metrics.index, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim([0, 1.1])
        
        plt.tight_layout()
        plt.savefig(output_dir / 'category_performance.png', dpi=300, bbox_inches='tight')
        print(f"   Saved: {output_dir / 'category_performance.png'}")
        plt.close()
    
    # 5. Distribution of Metrics (Histograms)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    axes[0, 0].hist(df_results['Precision@10'], bins=20, alpha=0.7, color='blue', edgecolor='black')
    axes[0, 0].axvline(avg_precision, color='r', linestyle='--', linewidth=2, label=f'Mean: {avg_precision:.3f}')
    axes[0, 0].set_xlabel('Precision@10', fontsize=12)
    axes[0, 0].set_ylabel('Frequency', fontsize=12)
    axes[0, 0].set_title('Distribution of Precision@10', fontsize=13, fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].hist(df_results['Recall@50'], bins=20, alpha=0.7, color='orange', edgecolor='black')
    axes[0, 1].axvline(avg_recall_50, color='r', linestyle='--', linewidth=2, label=f'Mean: {avg_recall_50:.3f}')
    axes[0, 1].set_xlabel('Recall@50', fontsize=12)
    axes[0, 1].set_ylabel('Frequency', fontsize=12)
    axes[0, 1].set_title('Distribution of Recall@50', fontsize=13, fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[1, 0].hist(df_results['MRR'], bins=20, alpha=0.7, color='green', edgecolor='black')
    axes[1, 0].axvline(avg_mrr, color='r', linestyle='--', linewidth=2, label=f'Mean: {avg_mrr:.3f}')
    axes[1, 0].set_xlabel('MRR', fontsize=12)
    axes[1, 0].set_ylabel('Frequency', fontsize=12)
    axes[1, 0].set_title('Distribution of MRR', fontsize=13, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].hist(df_results['NDCG@10'], bins=20, alpha=0.7, color='purple', edgecolor='black')
    axes[1, 1].axvline(avg_ndcg, color='r', linestyle='--', linewidth=2, label=f'Mean: {avg_ndcg:.3f}')
    axes[1, 1].set_xlabel('NDCG@10', fontsize=12)
    axes[1, 1].set_ylabel('Frequency', fontsize=12)
    axes[1, 1].set_title('Distribution of NDCG@10', fontsize=13, fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'metric_distributions.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'metric_distributions.png'}")
    plt.close()
    
    # 6. Correlation Heatmap
    metric_cols = ['Precision@10', 'Recall@10', 'Recall@50', 'MRR', 'NDCG@10']
    corr_matrix = df_results[metric_cols].corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title('Correlation Matrix of Evaluation Metrics', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'correlation_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'correlation_heatmap.png'}")
    plt.close()
    
    # 7. Summary Statistics Table Visualization
    summary_stats = pd.DataFrame({
        'Metric': ['Precision@10', 'Recall@10', 'Recall@50', 'MRR', 'NDCG@10'],
        'Mean': [avg_precision, avg_recall_10, avg_recall_50, avg_mrr, avg_ndcg],
        'Median': [
            df_results['Precision@10'].median(),
            df_results['Recall@10'].median(),
            df_results['Recall@50'].median(),
            df_results['MRR'].median(),
            df_results['NDCG@10'].median()
        ],
        'Std Dev': [
            df_results['Precision@10'].std(),
            df_results['Recall@10'].std(),
            df_results['Recall@50'].std(),
            df_results['MRR'].std(),
            df_results['NDCG@10'].std()
        ],
        'Min': [
            df_results['Precision@10'].min(),
            df_results['Recall@10'].min(),
            df_results['Recall@50'].min(),
            df_results['MRR'].min(),
            df_results['NDCG@10'].min()
        ],
        'Max': [
            df_results['Precision@10'].max(),
            df_results['Recall@10'].max(),
            df_results['Recall@50'].max(),
            df_results['MRR'].max(),
            df_results['NDCG@10'].max()
        ]
    })
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=summary_stats.round(4).values,
                     colLabels=summary_stats.columns,
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # Style the header
    for i in range(len(summary_stats.columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Summary Statistics of Evaluation Metrics', fontsize=14, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'summary_statistics.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'summary_statistics.png'}")
    plt.close()
    
    # 8. Top and Bottom Performing Queries
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # Top 10 by Precision@10
    top_queries = df_results.nlargest(10, 'Precision@10')
    ax1.barh(range(len(top_queries)), top_queries['Precision@10'], alpha=0.8, color='green')
    ax1.set_yticks(range(len(top_queries)))
    ax1.set_yticklabels([f"Q{i+1}" for i in top_queries.index], fontsize=9)
    ax1.set_xlabel('Precision@10', fontsize=12)
    ax1.set_title('Top 10 Queries by Precision@10', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.set_xlim([0, 1.1])
    
    # Bottom 10 by Precision@10
    bottom_queries = df_results.nsmallest(10, 'Precision@10')
    ax2.barh(range(len(bottom_queries)), bottom_queries['Precision@10'], alpha=0.8, color='red')
    ax2.set_yticks(range(len(bottom_queries)))
    ax2.set_yticklabels([f"Q{i+1}" for i in bottom_queries.index], fontsize=9)
    ax2.set_xlabel('Precision@10', fontsize=12)
    ax2.set_title('Bottom 10 Queries by Precision@10', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.set_xlim([0, 1.1])
    
    plt.tight_layout()
    plt.savefig(output_dir / 'top_bottom_queries.png', dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir / 'top_bottom_queries.png'}")
    plt.close()
    
    # Save results to CSV
    df_results.to_csv(output_dir / 'evaluation_results.csv', index=False)
    print(f"   Saved: {output_dir / 'evaluation_results.csv'}")
    
    print(f"\n✓ All visualizations saved to '{output_dir}/' directory")
    print(f"✓ Total files generated: 8 charts + 1 CSV file")

# --- Helper Functions ---

def extract_keywords(query):
    """Enhanced keyword extraction from query (removes stopwords, handles common job search terms)"""
    stopwords = {
        "with", "and", "in", "for", "the", "a", "an", "of", "to", "experience", 
        "specializing", "skills", "position", "role", "job", "based", "own"
    }
    # Remove punctuation and split
    words = query.lower().replace(",", "").replace(".", "").replace("-", " ").split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords

def is_relevant(query, retrieved_doc):
    """
    Enhanced heuristic to determine if a retrieved document is relevant to the query.
    Checks title, description, category, subcategory, role, and location.
    """
    keywords = extract_keywords(query)
    
    # Extract metadata fields (handle None values)
    job_title = (retrieved_doc.metadata.get("job_title") or "").lower()
    job_desc = retrieved_doc.page_content.lower()[:1000]  # Check first 1000 chars
    category = (retrieved_doc.metadata.get("category") or "").lower()
    subcategory = (retrieved_doc.metadata.get("subcategory") or "").lower()
    role = (retrieved_doc.metadata.get("role") or "").lower()
    location = (retrieved_doc.metadata.get("location") or "").lower()
    job_type = (retrieved_doc.metadata.get("type") or "").lower()
    
    # Combine all text fields for matching
    all_text = f"{job_title} {category} {subcategory} {role} {location} {job_type} {job_desc}"
    
    # 1. Title Match (Highest Confidence - exact role match)
    title_matches = sum(1 for k in keywords if k in job_title)
    if title_matches >= 2:  # At least 2 keywords in title
        return True
    if title_matches == 1 and len(keywords) <= 3:  # Single keyword match for short queries
        return True
    
    # 2. Role/Category Match (High Confidence)
    role_matches = sum(1 for k in keywords if k in role or k in subcategory)
    if role_matches >= 2:
        return True
    
    # 3. Location Match (if location is specified in query)
    location_keywords = [k for k in keywords if any(loc in k for loc in ["kuala", "lumpur", "selangor", "klang", "malaysia", "petaling", "jaya"])]
    if location_keywords and any(loc in all_text for loc in location_keywords):
        location_match = True
    else:
        location_match = len(location_keywords) == 0  # No location requirement
    
    # 4. Description Match (Secondary - requires multiple keyword matches)
    desc_matches = sum(1 for k in keywords if k in job_desc)
    
    # 5. Job Type Match (if specified)
    type_keywords = [k for k in keywords if k in ["full", "time", "contract", "temp", "part"]]
    type_match = len(type_keywords) == 0 or any(t in job_type for t in type_keywords)
    
    # Combined scoring: Require multiple matches across different fields
    total_matches = title_matches + role_matches + desc_matches
    
    # Relevance criteria:
    # - At least 3 total keyword matches AND location/type compatibility
    # - OR at least 2 matches in title/role (high confidence fields)
    if total_matches >= 3 and location_match and type_match:
        return True
    if (title_matches + role_matches) >= 2 and location_match:
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

def categorize_query(query):
    """Categorize query into a category for analysis."""
    query_lower = query.lower()
    
    if any(term in query_lower for term in ['developer', 'engineer', 'scientist', 'software', 'data', 'devops', 'python', 'javascript', 'react', 'node', 'tensorflow']):
        return 'Technology'
    elif any(term in query_lower for term in ['manager', 'executive', 'analyst', 'business', 'sales', 'marketing', 'product']):
        return 'Business/Management'
    elif any(term in query_lower for term in ['accountant', 'financial', 'audit', 'accounts', 'cpa']):
        return 'Finance/Accounting'
    elif any(term in query_lower for term in ['procurement', 'supply chain', 'logistics', 'purchasing', 'inventory']):
        return 'Supply Chain'
    elif any(term in query_lower for term in ['hr', 'human resources', 'recruitment', 'talent', 'administrative', 'executive assistant']):
        return 'HR/Administration'
    elif any(term in query_lower for term in ['customer', 'support', 'service', 'representative']):
        return 'Customer Service'
    elif any(term in query_lower for term in ['kuala lumpur', 'selangor', 'petaling', 'klang', 'malaysia']):
        return 'Location-Specific'
    elif any(term in query_lower for term in ['full-time', 'contract', 'part-time', 'temp']):
        return 'Job Type-Specific'
    else:
        return 'Other'

if __name__ == "__main__":
    main()

