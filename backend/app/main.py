import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
from exa_py import Exa

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")
if not EXA_API_KEY or not OPENROUTER_API_KEY:
    print("Error: EXA_API_KEY or OPENROUTER_API_KEY is not set")


exa = Exa(api_key = EXA_API_KEY)
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

app = FastAPI(title="Exa Recruiting API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

class SearchRequest(BaseModel):
   query: str

class LinkedinResult(BaseModel):
    url: str
    title: str

class SearchResponse(BaseModel):
    results: List[LinkedinResult]


@app.post("/search-for-jobs", response_model=List[LinkedinResult])
async def search_for_jobs(request: SearchRequest):
    
    query = f'{request.query}'

    try:
        search = exa.search(
            query=query,
            num_results=5,
            type="keyword",
            include_domains=["linkedin.com"]
        )
        results = [
            LinkedinResult(url=result.url, title=result.title)
            for result in search.results if "linkedin.com/in/" in result.url 
        ]
        return results[:10]  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exa search failed: {str(e)}")
    

