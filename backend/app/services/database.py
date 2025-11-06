from supabase import create_client, Client
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
# IMPORTANT: Use service key for backend operations to bypass RLS
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase_anon_key = os.getenv("SUPABASE_PUBLISHABLE_OR_ANON_KEY")

if not supabase_url:
    raise ValueError("SUPABASE_URL environment variable must be set")

# Prefer service key, but warn if not available
if supabase_service_key:
    supabase_key = supabase_service_key
    print("[INFO] Using SUPABASE_SERVICE_KEY (will bypass RLS)")
else:
    if supabase_anon_key:
        print("[WARNING] SUPABASE_SERVICE_KEY not set, using anon key. RLS policies may block inserts!")
        supabase_key = supabase_anon_key
    else:
        raise ValueError(
            "SUPABASE_SERVICE_KEY or SUPABASE_PUBLISHABLE_OR_ANON_KEY must be set. "
            "For backend operations, SUPABASE_SERVICE_KEY is recommended to bypass RLS."
        )

supabase: Client = create_client(supabase_url, supabase_key)


def save_chat_message(user_id: str, thread_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Save a chat message to the chat_history table.
    
    Args:
        user_id: UUID of the user
        thread_id: LangGraph thread ID
        role: 'user' or 'assistant'
        content: Message content
        metadata: Optional metadata dict
        
    Returns:
        Dict with the saved message data
    """
    try:
        data = {
            "user_id": user_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
        }
        
        if metadata:
            data["metadata"] = metadata
        
        print(f"[DEBUG] Inserting into chat_history: user_id={user_id}, thread_id={thread_id}, role={role}")
        response = supabase.table("chat_history").insert(data).execute()
        
        if not response.data:
            error_msg = f"Failed to save chat message - no data returned. Response: {response}"
            print(f"[ERROR] {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[DEBUG] Successfully inserted chat message with id: {response.data[0].get('id')}")
        return response.data[0]
    except Exception as e:
        print(f"[ERROR] Exception in save_chat_message: {e}")
        print(f"[ERROR] Data attempted: user_id={user_id}, thread_id={thread_id}, role={role}")
        raise


def save_user_job(user_id: str, job_title: str, company: str, location: str, 
                  match_rating: int, link: str) -> Dict:
    """
    Save a job to the user_jobs table.
    Note: user_jobs does NOT link to chat history (no thread_id).
    
    Args:
        user_id: UUID of the user
        job_title: Job title
        company: Company name
        location: Job location
        match_rating: Match rating (0-5)
        link: Job application link
        
    Returns:
        Dict with the saved job data
    """
    try:
        data = {
            "user_id": user_id,
            "job_title": job_title,
            "company": company,
            "location": location,
            "match_rating": match_rating,
            "link": link,
        }
        
        print(f"[DEBUG] Inserting into user_jobs: user_id={user_id}, job_title={job_title}, company={company}")
        response = supabase.table("user_jobs").insert(data).execute()
        
        if not response.data:
            error_msg = f"Failed to save user job - no data returned. Response: {response}"
            print(f"[ERROR] {error_msg}")
            raise ValueError(error_msg)
        
        print(f"[DEBUG] Successfully inserted job with id: {response.data[0].get('id')}")
        return response.data[0]
    except Exception as e:
        print(f"[ERROR] Exception in save_user_job: {e}")
        print(f"[ERROR] Data attempted: user_id={user_id}, job_title={job_title}, company={company}")
        raise


def get_user_skills(user_id: str) -> List[Dict]:
    """
    Fetch user skills with proficiency levels from the database.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of dicts with skill information including name, category, and proficiency_level
    """
    response = supabase.table("user_skills").select(
        """
        *,
        skills (
            id,
            name,
            category
        )
        """
    ).eq("user_id", user_id).execute()
    
    if not response.data:
        return []
    
    return response.data


def get_user_profile(user_id: str) -> Optional[Dict]:
    """
    Fetch user profile information.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        Dict with profile data or None if not found
    """
    response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    
    if not response.data:
        return None
    
    return response.data


def format_user_context(user_id: str) -> str:
    """
    Format user context string from profile and skills for use in agent prompts.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        Formatted context string with user info and skills
    """
    profile = get_user_profile(user_id)
    skills = get_user_skills(user_id)
    
    context_parts = []
    
    if profile:
        if profile.get("full_name"):
            context_parts.append(f"Name: {profile['full_name']}")
        if profile.get("linkedin_url"):
            context_parts.append(f"LinkedIn: {profile['linkedin_url']}")
    
    if skills:
        skill_list = []
        for user_skill in skills:
            skill_name = user_skill.get("skills", {}).get("name", "Unknown")
            proficiency = user_skill.get("proficiency_level", "Unknown")
            skill_list.append(f"{skill_name} ({proficiency})")
        
        if skill_list:
            context_parts.append(f"Skills: {', '.join(skill_list)}")
    
    if not context_parts:
        return "No user context available"
    
    return ". ".join(context_parts) + "."

