from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import os

# Initialize Groq (Llama) client
cached_llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7,
)

def search_jobs(country: str, role: str = None):
    """
    Search for jobs in a given country.
    If no role is provided, show all available job listings.
    """
    if role:
        role_info = f"for the role of {role}"
    else:
        role_info = "for any available roles"

    prompt = f"""
    You are a job search assistant. Find the most recent and relevant job openings in {country} {role_info}.
    Output them clearly in this format:

    - Job Title – Company Name – Location (if available)
    - Job Title – Company Name – Location (if available)
    - Job Title – Company Name – Location (if available)

    If no current openings are available, list major companies or organizations
    in {country} that are known to hire frequently, and the roles they often advertise.
    """

    messages = [
        SystemMessage(content="You are a helpful AI job search assistant."),
        HumanMessage(content=prompt)
    ]
    
    response = cached_llm.invoke(messages)
    return response.content

