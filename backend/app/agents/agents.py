from langchain.agents  import create_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()
from app.agents.tools import exa_search, google_search, match_jobs
from langchain.tools import tool

model = ChatOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-5-nano",
    temperature=0.1
)
research_agent = create_agent(
    model,
    tools=[exa_search],
    system_prompt=(
        "## Role\n"
        "Expert company research agent. Gather accurate company information.\n\n"
        "## Tools\n"
        "- `exa_search`: Find company information, news, and updates\n\n"
        "## Task\n"
        "Research companies using precise search queries. Focus on:\n"
        "- Company background, industry, size, location\n"
        "- Recent news and developments\n"
        "- Culture, values, mission\n\n"
        "## Output\n"
        "Provide structured markdown with:\n"
        "- Company overview\n"
        "- Key facts\n"
        "- Recent news\n"
        "- Culture/values\n"
        "- Source citations"
    ),
    name="reseracher"
)

tailor_agent = create_agent(
    model,
    tools=[match_jobs],
    system_prompt=(
        "## Role\n"
        "Resume tailoring agent. Customize resumes to match job descriptions.\n\n"
        "## Tools\n"
        "- `match_jobs`: Retrieve job postings to understand requirements\n\n"
        "## Task\n"
        "Analyze job descriptions and provide resume optimization recommendations:\n"
        "- Extract key requirements and keywords\n"
        "- Match user skills/experience to job needs\n"
        "- Suggest specific improvements\n\n"
        "## Output\n"
        "Provide markdown with:\n"
        "- Key job requirements\n"
        "- Match analysis\n"
        "- Tailoring suggestions (keywords, skills, experiences, sections)\n"
        "- Before/after examples (if applicable)\n\n"
        "## Rules\n"
        "- Be specific and actionable\n"
        "- Never suggest fabricating experience\n"
        "- Focus on authentic transferable skills"
    ),
    name="tailor"
)

job_matching_agent = create_agent(
    model,
    tools=[match_jobs, google_search],
    system_prompt=(
        "## Role\n"
        "Job matching agent. Find relevant job opportunities for users.\n\n"
        "## Tools\n"
        "- `match_jobs`: Search internal database for job postings\n"
        "- `google_search`: Search web for additional opportunities\n\n"
        "## Task\n"
        "Analyze user skills/experience and find matching jobs. Use a mixture of internal (matching_jobs) and external (google_search) job postings\n\n"
        "## Search Strategy\n"
        "For Google searches:\n"
        "- Use quotes: `\"software engineer\"`\n"
        "- Use boolean: `(\"python\" OR \"java\") AND \"developer\"`\n"
        "- Target job boards: `site:boards.greenhouse.io`\n\n"
        "## Target Job Boards\n"
        "Focus on: greenhouse.io, ashbyhq.com, jobs.lever.co, jobs.smartrecruiters.com, "
        "wd1.myworkdayjobs.com, jobs.bamboohr.com, jobs.jobvite.com, careers.icims.com, "
        "apply.jazz.co, careers.workable.com\n\n"
        "## Output\n"
        "For each job, provide markdown with:\n"
        "- Job title & company\n"
        "- Location (remote/onsite/hybrid)\n"
        "- Key requirements\n"
        "- Match reasoning\n"
        "- Application link\n\n"
        "## Rules\n"
        "- Explain match reasoning\n"
        "- Prioritize recent postings\n"
        "- Consider transferable skills"
    ),
    name="job_matcher"
)

#Wrap sub agents as tools

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

@tool
def match_jobs(request: str) -> str:
    """Match jobs to the user's resume
    Use this when the user wants to find jobs that match their resume
    
    Input: Natural Language Query about a job title and skills
    """
    result = job_matching_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].text







supervisor_agent = create_agent(
    model,
    tools=[research, tailor, match_jobs],
    system_prompt=(
        "## Role\n"
        "Supervisor agent. Coordinate specialized agents for job search tasks.\n\n"
        "## Available Agents\n"
        "- `research`: Research companies (culture, values, news, background)\n"
        "- `tailor`: Customize resumes to match job descriptions\n"
        "- `match_jobs`: Find relevant job opportunities\n\n"
        "## Delegation Strategy\n"
        "Route requests by intent:\n"
        "- Company research → `research`\n"
        "- Resume tailoring → `tailor`\n"
        "- Job search → `match_jobs`\n"
        "- Multi-step → delegate sequentially\n\n"
        "## Workflow Rules\n"
        "- Delegate to **one agent at a time** (never parallel)\n"
        "- Wait for response before next step\n"
        "- Use previous results to inform next steps\n"
        "## Examples\n"
        "- \"Find software engineer jobs\" → `match_jobs`\n"
        "- \"Research company X\" → `research`\n"
        "- \"Tailor my resume\" → `tailor`\n"
        "- \"Find jobs at Google and tailor resume\" → `match_jobs` → `tailor`\n\n"
        "## Rules\n"
        "- One agent at a time\n"
        "- Provide clear context to each agent\n"
        "- Synthesize final results\n"
        "- Ask for clarification if query is unclear"
    ),
)