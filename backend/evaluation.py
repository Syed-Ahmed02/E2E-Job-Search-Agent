import os
import pandas as pd
import numpy as np
from datasets import load_dataset
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Suppress warnings for cleaner output
    print("=== RAG Retrieval Quality Evaluation ===\n")

    # 1. Load and Prepare Dataset
    print("1. Loading dataset...")
    try:
        # Load the azrai99/job-dataset from HuggingFace
        dataset = load_dataset("azrai99/job-dataset", split="train")
        
        # Take a sample of 1000 jobs to keep processing fast
        # Shuffle first to get a random sample
        sampled_dataset = dataset.shuffle(seed=42).select(range(1000))
        
        print(f"   Loaded {len(sampled_dataset)} jobs from azrai99/job-dataset.")
        print(f"   Sample fields: {list(sampled_dataset[0].keys())}")
        
    except Exception as e:
        print(f"   Error loading dataset: {e}")
        # Fallback to dummy data if dataset fails
        sampled_dataset = [
            {"descriptions": "Senior Python Developer needed...", "job_title": "Python Developer", "company": "Tech Corp"},
            {"descriptions": "Marketing Manager for NYC firm...", "job_title": "Marketing Manager", "company": "Ad Agency"}
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

    # Create In-Memory ChromaDB Client for isolation
    client = chromadb.CloudClient(
        api_key=os.getenv("CHROMA_API_KEY"),
        tenant='361f16d2-3a10-4479-854c-519de88ae973',
        database='job_search_db'
        )
    # Create Vector Store
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        client=client,
        collection_name="evaluation_jobs"
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
    
    # Extract metadata fields
    job_title = retrieved_doc.metadata.get("job_title", "").lower()
    job_desc = retrieved_doc.page_content.lower()[:1000]  # Check first 1000 chars
    category = retrieved_doc.metadata.get("category", "").lower()
    subcategory = retrieved_doc.metadata.get("subcategory", "").lower()
    role = retrieved_doc.metadata.get("role", "").lower()
    location = retrieved_doc.metadata.get("location", "").lower()
    job_type = retrieved_doc.metadata.get("type", "").lower()
    
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

if __name__ == "__main__":
    main()

