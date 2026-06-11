# Neuro Claw Agent — Week 1

A simple Google ADK agent built as part of **Week 1** of a neuroimaging research internship.
The goal of this week was to understand the NeuroClaw project, learn basic ADK agent programming,
and build a simple local tool that an agent can call.

---

## What this project does

The agent (`smri_guide_agent`) answers questions about sMRI preprocessing pipelines and
NeuroClaw / ADK concepts. It does this by calling two local Python tools — plain functions
defined in `tools.py` — rather than relying solely on the LLM's built-in knowledge.

This demonstrates the core ADK pattern: **agent → decides to call tool → tool runs locally → agent explains result**.

---

## Project structure

```
Neuro_claw_agent/
├── my_agent/
│   ├── __init__.py     # re-exports root_agent so ADK can discover it
│   ├── agent.py        # defines the ADK agent and registers the tools
│   └── tools.py        # two local tool functions
├── .env                # OPENROUTER_API_KEY (not committed)
├── .gitignore
└── README.md
```

---

## The two local tools

### `get_preprocessing_steps(modality)`
Returns the standard preprocessing steps for a given sMRI pipeline.

| Modality | Pipeline |
|---|---|
| `T1` | T1-weighted sMRI (skull strip → bias correct → segment → register → smooth) |
| `VBM` | Voxel-Based Morphometry (T1 pipeline + modulation + GLM + stats) |
| `FreeSurfer` | Cortical reconstruction (8-step surface pipeline, ~6–12 h/subject) |

### `explain_concept(concept)`
Explains a key term from the NeuroClaw paper or the Google ADK framework.

| Concept | |
|---|---|
| `agent` | Autonomous program that perceives inputs and calls tools to reach a goal |
| `tool` | Plain Python function the agent can invoke |
| `skill` | Higher-level capability that bundles multiple tools |
| `workflow` | Full end-to-end execution plan with branching, checkpointing, and verification |
| `neuroclaw` | CUHK-AIM project that wraps FSL/FreeSurfer/ANTs as agent-callable tools |
| `smri` | Structural MRI — T1-weighted brain anatomy used for morphological analysis |
| `qc` | Quality Control — checking each preprocessing step before the next begins |

---

## Setup

**Requirements:** Python 3.10+, Google ADK, `python-dotenv`, `litellm`

```bash
pip install google-adk python-dotenv litellm
```

Create a `.env` file in `my_agent/`:

```
OPENROUTER_API_KEY=your_key_here
```

---

## Running the agent

```bash
# Interactive web UI
adk web

# CLI
adk run my_agent
```

Then ask things like:
- *"What are the FreeSurfer preprocessing steps?"*
- *"Explain what a tool is in the context of NeuroClaw."*
- *"What does QC mean in neuroimaging?"*

---

## Week 1 context

| Question | Covered by |
|---|---|
| What problem does NeuroClaw solve? | `explain_concept("neuroclaw")` tool |
| What is an agent / tool / skill / workflow? | `explain_concept(...)` tool |
| What are the sMRI preprocessing steps? | `get_preprocessing_steps(...)` tool |
| How does an agent call a local tool? | `agent.py` + `tools.py` together |

The key insight from Week 1: NeuroClaw automates broad neuroimaging workflows but does not
explain its decisions, guide users through parameters, or reason about QC failures.
Our sMRI-focused project addresses exactly that gap.
