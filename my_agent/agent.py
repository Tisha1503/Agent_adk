import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from my_agent.tools import get_preprocessing_steps, explain_concept

load_dotenv()

root_agent = Agent(
    name="smri_guide_agent",
    model=LiteLlm(
        model="openrouter/google/gemma-4-31b-it:free",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    instruction="""You are a helpful sMRI preprocessing guide for a neuroimaging research intern.

    two tools to use:

1. get_preprocessing_steps(modality) — use this when the user asks about preprocessing
   steps for a pipeline. Supported modalities: T1, VBM, FreeSurfer.

2. explain_concept(concept) — use this when the user asks what a term means.
   Supported concepts: agent, tool, skill, workflow, neuroclaw, smri, qc.

Always call the relevant tool first, then explain the result clearly and simply,
as if you are teaching a first-week intern.
""",
    tools=[get_preprocessing_steps, explain_concept],
)
