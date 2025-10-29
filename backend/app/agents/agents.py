# load the environment variables
import os
from dotenv import load_dotenv
from langchain_exa import ExaSearchRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.agents import create_agent
from app.agents.tools import exa_search, website_scraper, retrieve_existing_jobs, retrieve_existing_resumes
from langgraph.checkpoint.memory import InMemorySaver
# Define our retriever to use Exa Search, grabbing 3 results and parsing highlights from each result
load_dotenv()
retriever = ExaSearchRetriever(api_key=os.getenv("EXA_API_KEY"), k=3, highlights=True)


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=os.getenv("OPENAI_API_KEY"))

research_agent = create_agent(
    llm=llm,
    tools=[exa_search,website_scraper],
    prompt=(
        "You are a research agent. You are given a query and you need to find the most relevant information on a certain company."
        "You will use the following tools to find the information:"
        "1. exa_search: to search for information on the company"
        "2. website_scraper: to scrape the company's website for information"
    ),
    name="reseracher"
)

tailor_agent = create_agent(
    llm=llm,
    tools=[retrieve_existing_jobs, retrieve_existing_resumes],
    prompt=(
        "You are a tailor agent, given a user query you need to tailor their resume to the job description."
        "You will use the following tools to tailor the information:"
        "1. retrieve_existing_jobs: to retrieve existing jobs for the user"
        "2. retrieve_existing_resumes: to retrieve existing resumes for the user"
    ),
    name="tailor"
)

job_matching_agent = create_agent(
    llm=llm,
    tools=[retrieve_existing_jobs, website_scraper],
    prompt=(
        "You are a job matching agent, given a user query you need to find the most relevant jobs for the user."
        "You will use the following tools to find the jobs:"
        "1. retrieve_existing_jobs: to retrieve existing jobs for the user"
        "2. website_scraper: to scrape the company's website for information"
    ),
    name="job_matcher"
)

config = {"configurable": {"thread_id": "1", "user_id": "1"}}
checkpointer = InMemorySaver()

#
@tool 
def match_jobs():
    """Match jobs to the user's resume"""


supervisor = create_agent(
    agents=[research_agent, tailor_agent, job_matching_agent],
    llm=llm,
    prompt=(
        "You are a supervisor, you are given a user query and you need to delegate the task to the appropriate agent."
        "You will use the following agents to delegate the task:"
        "1. research_agent: to research the company"
        "2. tailor_agent: to tailor the resume to the job description"
        "3. job_matching_agent: to find the most relevant jobs for the user"
        "Assign work to one agent at a time, do not call agents in parallel"
    ),
    add_handoff_back_messages=True,
    output_mode="full_history"
).compile(checkpointer=checkpointer)