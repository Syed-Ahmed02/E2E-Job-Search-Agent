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
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, push_ui_message, ui_message_reducer  


model = ChatOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-5-nano",
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

## Task
Find matching jobs using user skills and preferences. Use both internal (match_jobs) and external (google_search) sources.
Rate each job match 0-5 (5 = high match).

## Search Strategy
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

## Rules
- Prioritize recent postings
- Consider transferable skills
- Explain match reasoning
- Always return valid JSON matching JobData schema"""

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

## Rules
- Always clarify vague queries before delegating
- Provide clear context to each agent (include user skills and target role)
- Synthesize final results
- Be conversational and helpful"""



research_agent = create_agent(
    model,
    tools=[exa_search],
    system_prompt=RESEARCHER_PROMPT,
    name="reseracher"
)

tailor_agent = create_agent(
    model,
    tools=[match_jobs],
    system_prompt=TAILOR_PROMPT,
    name="tailor"
)

job_matching_agent = create_agent(
    model,
    tools=[match_jobs, google_search],
    system_prompt=JOB_MATCHING_PROMPT.format(user_context="No user context available"),
    response_format=ToolStrategy(JobsList),
    name="job_matcher"
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


# Create base supervisor agent
_base_supervisor_agent = create_agent(
    model,
    tools=[research, tailor, match_jobs],
    system_prompt=SUPERVISOR_PROMPT.format(user_context="No user context available"),
)

# Define state with UI support
class AgentState(TypedDict):
    messages: Annotated[Sequence[AIMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

async def supervisor_node(state: AgentState):
    """Supervisor node that processes messages and adds UI for jobs"""
    # Invoke the base supervisor agent
    result = await _base_supervisor_agent.ainvoke(state)
    
    # Get the last message
    last_message = result["messages"][-1]
    
    # Check if this is a response from match_jobs tool call
    # Look for job data in the message content
    if isinstance(last_message, AIMessage):
        message_text = last_message.content
        jobs = []
        
        # Check if there's a structured_response in the result (from ToolStrategy)
        if "structured_response" in result:
            structured_response = result["structured_response"]
            if isinstance(structured_response, JobsList):
                jobs = [job.dict() if hasattr(job, 'dict') else job for job in structured_response.jobs]
            elif isinstance(structured_response, dict) and 'jobs' in structured_response:
                jobs_list = structured_response['jobs']
                jobs = [job.dict() if hasattr(job, 'dict') else job for job in jobs_list]
            elif isinstance(structured_response, list):
                jobs = [job.dict() if hasattr(job, 'dict') else job for job in structured_response]
        
        # Check tool calls for structured output from job_matching_agent
        if not jobs and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            # Look for match_jobs tool call
            for tool_call in last_message.tool_calls:
                if tool_call.get('name') == 'match_jobs':
                    # The tool returns text, but we need to check if job_matching_agent was invoked
                    # and extract from its response. Since match_jobs tool just returns text,
                    # we'll extract from the message content or tool response
                    pass
        
        # Check if message has response_metadata with structured output (ProviderStrategy)
        if not jobs and hasattr(last_message, 'response_metadata') and last_message.response_metadata:
            structured_output = last_message.response_metadata.get('structured_output')
            if structured_output:
                # Handle JobsList structured output
                if isinstance(structured_output, JobsList):
                    jobs = [job.dict() if hasattr(job, 'dict') else job for job in structured_output.jobs]
                elif isinstance(structured_output, dict) and 'jobs' in structured_output:
                    jobs = [job.dict() if hasattr(job, 'dict') else job for job in structured_output['jobs']]
                elif isinstance(structured_output, list):
                    jobs = [job.dict() if hasattr(job, 'dict') else job for job in structured_output]
        
        # If no structured output, try to extract from text
        if not jobs:
            jobs = extract_jobs_from_response(message_text)
        
        # If jobs were found, push UI message
        if jobs:
            # Use existing message ID or create new one
            message_id = last_message.id if hasattr(last_message, 'id') and last_message.id else str(uuid.uuid4())
            
            # Create AI message with ID
            ai_message = AIMessage(
                id=message_id,
                content=message_text,
            )
            
            # Push UI message with jobs
            push_ui_message(
                "jobs_table",
                {"jobs": jobs},
                message=ai_message
            )
            
            return {"messages": [ai_message]}
    
    return result

# Create the graph with UI support
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.set_entry_point("supervisor")

supervisor_agent = workflow.compile()

