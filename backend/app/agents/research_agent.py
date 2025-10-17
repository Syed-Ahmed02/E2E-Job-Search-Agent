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
# Define our retriever to use Exa Search, grabbing 3 results and parsing highlights from each result
load_dotenv()
retriever = ExaSearchRetriever(api_key=os.getenv("EXA_API_KEY"), k=3, highlights=True)

# Define core prompt template
generation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research assistant in charge of finding information about companies. You take in"),
    ("human", """
Please answer the following query based on the provided context. Please cite your sources at the end of your response.:

Query: {query}
---
{context}
"""
)])

# Use OpenAI for generation
llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple string parsing for trhe output
output_parser = StrOutputParser()

# Connect the chain, including parallel connection for query from user and context from Exa retriever chain in step 2.
chain = RunnableParallel({
    "query": RunnablePassthrough(),
    "context": retriever,
}) | generation_prompt | llm | output_parser


result = chain.invoke("tell me about the latest open ai news")

print(result)