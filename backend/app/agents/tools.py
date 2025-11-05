from langchain.tools import tool
from langchain_exa import ExaSearchRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
from dotenv import load_dotenv
from typing import Annotated
import chromadb
import requests
import time
from threading import Lock
from collections import deque
load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID") 
CHROME_API_KEY = os.getenv("CHROME_API_KEY")
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

exa_retriever = ExaSearchRetriever(api_key=EXA_API_KEY, k=1, highlights=True)
client = chromadb.CloudClient(
  api_key=CHROMA_API_KEY,
  tenant='361f16d2-3a10-4479-854c-519de88ae973',
  database='job_search_db'
)
embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
vector_store = Chroma(
    client=client,
    collection_name="skills_jobs",
    embedding_function=embeddings
)
chroma_retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k":1})
# Rate limiter class
class ExaRateLimiter:
    def __init__(self, max_requests: int = 5, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()
        self.lock = Lock()
    
    def acquire(self):
        """Wait if necessary to stay within rate limit"""
        with self.lock:
            now = time.time()
            while self.request_times and self.request_times[0] < now - self.time_window:
                self.request_times.popleft()
            
            # If we're at the limit, wait until we can make another request
            if len(self.request_times) >= self.max_requests:
                sleep_time = self.request_times[0] + self.time_window - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()
                    while self.request_times and self.request_times[0] < now - self.time_window:
                        self.request_times.popleft()
            
            # Record this request time
            self.request_times.append(now)

# Create rate limiter instance
exa_rate_limiter = ExaRateLimiter(max_requests=5, time_window=1.0)

# Then modify your exa_search tool:
@tool
def exa_search(query: Annotated[str, "The query to execute to find key summary information."]):
    """Use Exa Search to find key summary information"""
    exa_rate_limiter.acquire()  # Rate limit before API call
    results = exa_retriever.invoke(query)
    return results



@tool
def google_search(query: Annotated[str, "The boolean search query to execute to find key summary information."]):
    """Given a google boolean search query, return the top 10 results

    
    """
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        # Optional: restrict to last month -> d = days, w = weeks, m = months, y = years
        "num": 10,             # 1..10 per page
        "safe": "off",
        "lr": "lang_en",       # optional language
    }
    resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()  
    
    results = [
    {
        "title": item.get("title"),
        "link": item.get("link"),
        "snippet": item.get("snippet"),
        "displayLink": item.get("displayLink"),
    }
        for item in data.get("items", [])
    ]
    
    return results

@tool
def match_jobs(query:Annotated[str,"The skills and job title the user wants to search for"]):
    """retrieve relevant jobs to help the user query"""
    results = chroma_retriever.invoke(query)
    return results


