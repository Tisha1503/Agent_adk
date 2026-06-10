import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

root_agent = Agent(
    name="my_first_agent",
    model=LiteLlm(
        model="openrouter/google/gemma-4-31b-it:free",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    instruction="You are a friendly assistant. Answer the user's questions concisely.",
)