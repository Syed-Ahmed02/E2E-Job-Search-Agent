from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
import os
from typing import List, Dict, Optional
import numpy as np

model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using HuggingFace model"""
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def embed_job(job_id: str) -> None:
    """Generate and store embedding for a job"""
    # Fetch job
    response = supabase.table("jobs").select("*").eq("id", job_id).execute()
    
    if not response.data:
        raise ValueError(f"Job {job_id} not found")
    
    job = response.data[0]
    
    # Combine relevant fields for embedding
    text_to_embed = f"""
    Position: {job['position_name']}
    Company: {job['company']}
    Location: {job.get('location', '')}
    Description: {job['job_description']}
    """.strip()
    
    # Generate embedding
    embedding = generate_embedding(text_to_embed)
    
    # Store embedding
    supabase.table("jobs").update({
        "embedding": embedding
    }).eq("id", job_id).execute()
    
    print(f"✅ Embedded job: {job['position_name']} at {job['company']}")
    
    
    
def embed_resume(resume_id: str) -> None:
    """Generate and store embedding for a resume"""
    # Fetch resume
    response = supabase.table("resumes").select("*").eq(
        "id", resume_id
    ).execute()
    
    if not response.data:
        raise ValueError(f"Resume {resume_id} not found")
    
    resume = response.data[0]
    
    # Combine profile fields
    text_to_embed = f"""
    Profile: {resume.get('profile', '')}
    LinkedIn: {resume.get('linkedin', '')}
    Skills: {resume.get('skills', '')}
    Experience: {resume.get('experience', '')}
    """.strip()
    
    # Generate embedding
    embedding = generate_embedding(text_to_embed)
    
    # Store embedding
    supabase.table("resumes").update({
        "embedding": embedding
    }).eq("id", resume_id).execute()
    
    print(f"✅ Embedded resume: {resume_id}")
    
def batch_embed_jobs() -> None:
    """Embed all jobs that don't have embeddings"""
    response = supabase.table("jobs").select("id").is_(
        "embedding", "null"
    ).execute()
    
    jobs_to_embed = response.data
    print(f"📊 Found {len(jobs_to_embed)} jobs to embed")
    
    for idx, job in enumerate(jobs_to_embed, 1):
        try:
            embed_job(job['id'])
            print(f"Progress: {idx}/{len(jobs_to_embed)}")
        except Exception as e:
            print(f"❌ Error embedding job {job['id']}: {e}")


def batch_embed_resumes() -> None:
    """Embed all resumes that don't have embeddings"""
    response = supabase.table("resumes").select("id").is_(
        "embedding", "null"
    ).execute()
    
    resumes_to_embed = response.data
    print(f"📊 Found {len(resumes_to_embed)} resumes to embed")
    
    for idx, resume in enumerate(resumes_to_embed, 1):
        try:
            embed_resume(resume['id'])
            print(f"Progress: {idx}/{len(resumes_to_embed)}")
        except Exception as e:
            print(f"❌ Error embedding resume {resume['id']}: {e}")
            
def find_matching_jobs(
    resume_id: str,
    match_threshold: float = 0.5,
    limit: int = 10
) -> List[Dict]:
    """Find jobs matching a resume"""
    # Get resume embedding
    response = supabase.table("resumes").select(
        "embedding"
    ).eq("id", resume_id).execute()
    
    if not response.data or not response.data[0].get('embedding'):
        raise ValueError(
            f"Resume {resume_id} not found or has no embedding"
        )
    
    resume_embedding = response.data[0]['embedding']
    
    # Call RPC function
    matches = supabase.rpc(
        "match_jobs",
        {
            "query_embedding": resume_embedding,
            "match_threshold": match_threshold,
            "match_count": limit
        }
    ).execute()
    
    # Format results
    results = []
    for match in matches.data:
        similarity = match['similarity']
        match_score = round(similarity * 100)
        
        results.append({
            "job": {
                "id": match['id'],
                "position_name": match['position_name'],
                "company": match['company'],
                "location": match['location'],
                "job_description": match['job_description']
            },
            "similarity": similarity,
            "match_score": match_score,
            "match_quality": get_match_quality(match_score)
        })
    
    return results


def find_matching_resumes(
    job_id: str,
    match_threshold: float = 0.5,
    limit: int = 10
) -> List[Dict]:
    """Find resumes matching a job posting"""
    # Get job embedding
    response = supabase.table("jobs").select(
        "embedding"
    ).eq("id", job_id).execute()
    
    if not response.data or not response.data[0].get('embedding'):
        raise ValueError(f"Job {job_id} not found or has no embedding")
    
    job_embedding = response.data[0]['embedding']
    
    # Call RPC function
    matches = supabase.rpc(
        "match_resumes",
        {
            "query_embedding": job_embedding,
            "match_threshold": match_threshold,
            "match_count": limit
        }
    ).execute()
    
    # Format results
    results = []
    for match in matches.data:
        similarity = match['similarity']
        match_score = round(similarity * 100)
        
        results.append({
            "resume": {
                "id": match['id'],
                "profile": match.get('profile', ''),
                "skills": match.get('skills', '')
            },
            "similarity": similarity,
            "match_score": match_score,
            "match_quality": get_match_quality(match_score)
        })
    
    return results


def get_match_quality(score: int) -> str:
    """Get match quality label based on score"""
    if score >= 80:
        return "🟢 Excellent"
    elif score >= 65:
        return "🟡 Good"
    elif score >= 50:
        return "🟠 Fair"
    else:
        return "🔴 Poor"


def display_job_matches(matches: List[Dict]) -> None:
    """Pretty print job matches"""
    print("\n🎯 Job Matches:\n")
    
    for idx, match in enumerate(matches, 1):
        job = match['job']
        print(f"{idx}. {job['position_name']} at {job['company']}")
        print(f"   Match Score: {match['match_score']}% "
              f"{match['match_quality']}")
        print(f"   Location: {job['location']}")
        print()


# Example usage
if __name__ == "__main__":
    # Embed all jobs and resumes
    batch_embed_jobs()
    batch_embed_resumes()
    
    # Find matches for a specific resume
    resume_id = "your-resume-id-here"
    matches = find_matching_jobs(resume_id, match_threshold=0.5, limit=20)
    display_job_matches(matches)