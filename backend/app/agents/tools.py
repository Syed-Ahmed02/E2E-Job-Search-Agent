from langchain.tools import tool
from langchain_exa import ExaSearchRetriever
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.document_loaders import S3FileLoader
from typing import Annotated
load_dotenv()

# EXA Search Retriever
retriever = ExaSearchRetriever(api_key=os.getenv("EXA_API_KEY"), k=3, highlights=True)
@tool
def exa_search(query: Annotated[str, "The query to execute to find key summary information."]):
    """Use Exa Search to find key summary information"""
    results = retriever.get_relevant_documents(query)
    return results

@tool
def website_scraper(url: Annotated[str, "The URL of the website to scrape"]):
    """Scrape a website for job postings and return the results in structured format"""
    # Website Scrappers
    
    # Returned Results in HTML
    loader = UnstructuredHTMLLoader(url)
    docs = loader.load()
    return docs


@tool
def retrieve_existing_jobs(query: Annotated[str, "The query to find existing jobs"]):
    """Retrieve existing jobs from the database"""
    # Database Query
    #todo: Edit this to use the correct database table and columns
    response = supabase.table("jobs").select("id, position_name, company, location, job_description").eq("query", query).execute()
    return response.data

@tool 
def retrieve_existing_resumes(user_id: Annotated[str, "The user ID of the resume to retrieve"]):
    """Retrieve existing resumes from the database"""
    # Database Query
    #todo: Edit this to use the correct database table and columns
    response = supabase.table("resumes").select("url").eq("user_id", user_id).execute()
    loader = S3FileLoader(response.data[0]['url'])
    docs = loader.load()
    return docs