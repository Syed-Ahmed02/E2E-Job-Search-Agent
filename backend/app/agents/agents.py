from langchain.agents import create_agent, structured_output
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import json
import re
import uuid
from typing import Annotated, Sequence, TypedDict, List
load_dotenv()
from app.agents.tools import exa_search, google_search, match_jobs
from langchain.tools import tool
from langchain.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, push_ui_message, ui_message_reducer
from langchain_core.messages.utils import trim_messages, count_tokens_approximately  


model = ChatOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model="x-ai/grok-4-fast",
    temperature=0.1
)

class Job(BaseModel):
    job_title: str
    company: str
    location: str
    match_rating: int
    link: str

class JobsList(BaseModel):
    """List of jobs matching the user's criteria"""
    jobs: List[Job]
    


RESEARCHER_PROMPT = """## Role
Expert company research agent. Gather accurate company information.

## Tools
- `exa_search`: Find company information, news, and updates

## Task
Research companies using precise search queries. Focus on:
- Company background, industry, size, location
- Recent news and developments
- Culture, values, mission

## Stopping Conditions
**CRITICAL**: Stop and return results when:
- You have gathered sufficient information about the company (2-3 tool calls maximum)
- You have enough information to provide a comprehensive overview
- DO NOT make more than 3 tool calls total
- After gathering information, immediately format and return the response

## Output
Provide structured markdown with:
- Company overview
- Key facts
- Recent news
- Culture/values
- Source citations"""

TAILOR_PROMPT = """## Role
Resume tailoring agent. Customize resumes to match job descriptions.

## Tools
- `match_jobs`: Retrieve job postings to understand requirements

## Task
Analyze job descriptions and provide resume optimization recommendations:
- Extract key requirements and keywords
- Match user skills/experience to job needs
- Suggest specific improvements

## Stopping Conditions
**CRITICAL**: Stop and return results when:
- You have retrieved the job posting(s) needed (1-2 tool calls maximum)
- You have enough information to provide tailoring recommendations
- DO NOT make more than 2 tool calls total
- After retrieving job information, immediately analyze and return recommendations

## Output
Provide markdown with:
- Key job requirements
- Match analysis
- Tailoring suggestions (keywords, skills, experiences, sections)
- Before/after examples (if applicable)

## Rules
- Be specific and actionable
- Never suggest fabricating experience
- Focus on authentic transferable skills"""

JOB_MATCHING_PROMPT = """## Role
Job matching agent finding relevant opportunities for users.

## User Context
{user_context}

## Tools
- `match_jobs`: Search internal database for job postings
- `google_search`: Search web for additional opportunities
- `exa_search`: Search company information, news, and updates

## Task
Find matching jobs using user skills and preferences. Use both internal (match_jobs) and external (google_search) sources.
Use exa search to find which website that company uses for job postings, and then search that website for job postings using the google search tool.
Rate each job match 0-5 (5 = high match).

## Search Strategy
Exa Search: Use this when the user wants to search for a specific company, find which website that company uses for job postings, 
and then search that website for job postings using the google search tool.
Example: "Search for jobs at Google" should first use exa search to find which website Google uses for job postings, and since it uses "https://www.google.com/about/careers/applications/jobs/" it should then search that website for job postings using the google search tool. 

Google searches:
- Use quotes: `"software engineer"`
- Boolean: `("python" OR "java") AND "developer"`
- Target boards: `site:boards.greenhouse.io`

## Target Job Boards
greenhouse.io, ashbyhq.com, jobs.lever.co, jobs.smartrecruiters.com, 
wd1.myworkdayjobs.com, jobs.bamboohr.com, jobs.jobvite.com, careers.icims.com, 
apply.jazz.co, careers.workable.com

## Output Format
**CRITICAL**: Return structured JSON array for each job:
[
  {{
    "job_title": "string",
    "company": "string",
    "location": "string",
    "match_rating": 0-5,
    "link": "string"
  }}
]Include brief reasoning for match_rating after the JSON.

## Stopping Conditions
**CRITICAL**: Stop and return results when:
- You have found 5-10 relevant job postings
- You have completed your search strategy (exa search → google search pattern)
- You have gathered sufficient information to rate and format jobs
- DO NOT call tools repeatedly if you already have enough results
- DO NOT make more than 5 tool calls total
- After calling tools and getting results, immediately format and return the JSON response

## Rules
- Prioritize recent postings
- Consider transferable skills
- Explain match reasoning
- Always return valid JSON matching JobData schema
- If the user asks to search for jobs at a specific company, use exa search to find which website that company uses for job postings, 
and then search that website for job postings using the google search tool.
- Always call one tool at a time
- **STOP after 5 tool calls maximum** - format and return results immediately
"""

SUPERVISOR_PROMPT = """## Role
Supervisor agent coordinating specialized agents for job search tasks.

## User Context
{user_context}

## Available Agents
- `research`: Research companies (culture, values, news, background)
- `tailor`: Customize resumes to match job descriptions
- `match_jobs`: Find relevant job opportunities

## Delegation Strategy
Route by intent:
- Company research → `research`
- Resume tailoring → `tailor`
- Job search → `match_jobs`
- Multi-step → delegate sequentially

## Query Clarification
**CRITICAL**: If the query lacks essential details, ask follow-up questions BEFORE delegating:
- Vague job titles (e.g., "swe jobs", "find me jobs") → Ask: "Do you have any specifications like location, salary range, seniority level, remote/hybrid preferences, or specific companies?"
- Missing location → Ask about preferred locations
- Missing experience level → Ask about seniority (entry, mid, senior)
- Ambiguous requests → Ask clarifying questions

## Workflow Rules
- Ask clarifying questions FIRST if query is unclear
- Delegate to **one agent at a time** (never parallel)
- Wait for response before next step
- Use previous results to inform next steps
- Include user context when delegating (name, skills, target role)

## Examples
- "Find software engineer jobs" → Ask: "Any location/salary/seniority preferences?"
- "Find SWE jobs in SF, $150k+, senior level" → `match_jobs`
- "Research Google" → `research`
- "Tailor my resume for job X" → `tailor`

## Stopping Conditions
**CRITICAL**: Stop and return final response when:
- The delegated agent has completed its task and returned results
- You have sufficient information to answer the user's query
- DO NOT delegate to the same agent repeatedly
- DO NOT call tools more than 5 times total
- After receiving results from an agent, synthesize and return the final answer immediately

## Rules
- Always clarify vague queries before delegating
- Provide clear context to each agent (include user skills and target role)
- Synthesize final results
- Be conversational and helpful
- Always use only one agent at a time
- **STOP after receiving results from agents** - do not continue tool calling unnecessarily
"""



research_agent = create_agent(
    model,
    tools=[exa_search],
    system_prompt=RESEARCHER_PROMPT,
    name="reseracher",
)

tailor_agent = create_agent(
    model,
    tools=[match_jobs],
    system_prompt=TAILOR_PROMPT,
    name="tailor",
)

job_matching_agent = create_agent(
    model,
    tools=[match_jobs, google_search,exa_search],
    system_prompt=JOB_MATCHING_PROMPT.format(user_context="No user context available"),
    response_format=ToolStrategy(JobsList),
    name="job_matcher",
)

@tool
def research(request: str) -> str:
    """Research a company
    Use this when the user wants to research a company
    
    Input: Natural Language Query about a company
    """
    result = research_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].text

@tool
def tailor(request: str) -> str:
    """Tailor a resume
    Use this when the user wants to tailor their resume to a specific job description
    
    Input: Natural Language Query about a job description
    """
    result = tailor_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].text

def extract_jobs_from_response(text: str) -> List[dict]:
    """Extract job objects from agent response text"""
    jobs = []
    try:
        # Try to find JSON array in the response
        json_match = re.search(r'\[[\s\S]*?\]', text)
        if json_match:
            jobs_data = json.loads(json_match.group())
            if isinstance(jobs_data, list):
                jobs = jobs_data
    except Exception:
        pass
    
    # If no JSON found, try to parse structured output
    if not jobs:
        try:
            # Try to extract individual job objects
            job_pattern = r'\{[^{}]*"job_title"[^{}]*\}'
            matches = re.findall(job_pattern, text, re.DOTALL)
            for match in matches:
                try:
                    job = json.loads(match)
                    jobs.append(job)
                except:
                    pass
        except Exception:
            pass
    
    return jobs

@tool
def match_jobs(request: str) -> str:
    """Match jobs to the user's resume
    Use this when the user wants to find jobs that match their resume
    
    Input: Natural Language Query about a job title and skills
    """
    result = job_matching_agent.invoke({"messages": [{"role": "user", "content": request}]})
    
    # Extract structured response if available
    structured_response = result.get("structured_response")
    if structured_response:
        # If we have JobsList, include it in the response text as JSON
        if isinstance(structured_response, JobsList):
            jobs_json = json.dumps([job.dict() for job in structured_response.jobs], indent=2)
            text_response = result["messages"][-1].text
            # Append the JSON to make it extractable
            return f"{text_response}\n\n{jobs_json}"
        elif isinstance(structured_response, dict) and 'jobs' in structured_response:
            jobs_json = json.dumps(structured_response['jobs'], indent=2)
            text_response = result["messages"][-1].text
            return f"{text_response}\n\n{jobs_json}"
    
    return result["messages"][-1].text


# Create base supervisor agent - this will stream tool calls properly
_base_supervisor_agent = create_agent(
    model,
    tools=[research, tailor, match_jobs],
    system_prompt=SUPERVISOR_PROMPT.format(user_context="No user context available"),
)

# Define state with UI support for the wrapper graph
class AgentState(TypedDict):
    messages: Annotated[Sequence[AIMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

async def add_ui_messages_node(state: AgentState):
    """Post-processing node that adds UI messages for jobs without blocking streaming"""
    # Get all messages to find the last AI message and any tool messages
    messages = state.get("messages", [])
    if not messages:
        return state
    
    last_message = messages[-1]
    jobs = []
    
    # Check if this is a response from match_jobs tool call
    # First, try to find jobs in tool messages from match_jobs
    for msg in reversed(messages):
        if hasattr(msg, 'name') and msg.name == "match_jobs":
            # Extract jobs from tool result
            if hasattr(msg, 'content'):
                content = msg.content
                # Handle both string and list content types
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)
                elif not isinstance(content, str):
                    content = str(content)
                jobs = extract_jobs_from_response(content)
                if jobs:
                    # Associate UI message with the last AI message that uses this tool result
                    break
    
    # If not found in tool messages, try to extract from the last AI message
    if not jobs and isinstance(last_message, AIMessage):
        message_text = last_message.content
        # Handle both string and list content types
        if isinstance(message_text, list):
            message_text = " ".join(str(item) for item in message_text)
        elif not isinstance(message_text, str):
            message_text = str(message_text)
        jobs = extract_jobs_from_response(message_text)
    
    # If jobs were found, push UI message with proper message association
    if jobs and isinstance(last_message, AIMessage):
        # push_ui_message automatically sets metadata when message is provided
        # The message parameter ensures the UI message is associated with the AI message
        push_ui_message(
            "jobs_table",
            {"jobs": jobs},
            message=last_message
        )
    
    # Return state unchanged (UI messages are added via push_ui_message)
    return state

def should_add_ui(state: AgentState) -> str:
    """Conditional function to determine if we should add UI messages"""
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    jobs = []
    
    # Check tool messages first (they contain the actual job data)
    for msg in reversed(messages):
        if hasattr(msg, 'name') and msg.name == "match_jobs":
            if hasattr(msg, 'content'):
                content = msg.content
                # Handle both string and list content types
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)
                elif not isinstance(content, str):
                    content = str(content)
                jobs = extract_jobs_from_response(content)
                if jobs:
                    return "add_ui"
    
    # Also check the last AI message
    if isinstance(last_message, AIMessage):
        content = last_message.content
        # Handle both string and list content types
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        elif not isinstance(content, str):
            content = str(content)
        jobs = extract_jobs_from_response(content)
        if jobs:
            return "add_ui"
    
    return "end"

# Create a wrapper graph that uses the base agent and adds UI support
# This allows streaming while still supporting UI messages
workflow = StateGraph(AgentState)

def supervisor_node(state: AgentState):
    """Wrapper node that trims messages before calling supervisor to prevent context length errors"""
    messages = state.get("messages", [])
    
    # Trim messages if they exist to stay well under the 128k token limit
    # Keep 100k tokens to leave room for response and function calls
    if messages:
        trimmed_messages = trim_messages(
            messages,
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=100000,  # Leave 28k tokens for response and overhead
            start_on="human",
            end_on=("human", "tool"),
        )
        # Create trimmed state preserving UI
        trimmed_state = {
            "messages": trimmed_messages,
            "ui": state.get("ui", [])
        }
    else:
        trimmed_state = state
    
    # Call the supervisor agent with trimmed messages and recursion limit config
    config = {"recursion_limit": 25}  # Set explicit recursion limit
    result = _base_supervisor_agent.invoke(trimmed_state, config=config)
    
    # Preserve UI state in result
    if "ui" in state:
        result["ui"] = state["ui"]
    
    return result

# Add the supervisor node with trimming - this will stream tool calls
workflow.add_node("supervisor", supervisor_node)

# Add UI message node
workflow.add_node("add_ui", add_ui_messages_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Add conditional edge: after supervisor, check if we need UI messages
workflow.add_conditional_edges(
    "supervisor",
    should_add_ui,
    {
        "add_ui": "add_ui",
        "end": END
    }
)

# After adding UI, end
workflow.add_edge("add_ui", END)

# Compile with recursion limit and checkpoint for state management
supervisor_agent = workflow.compile(
   
)

