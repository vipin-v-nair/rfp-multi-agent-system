from google.adk.agents import SequentialAgent
from agents.intake import intake_agent
from agents.evidence import evidence_agent
from agents.solution import solution_agent
from agents.governance import governance_agent
from agents.editor import editor_agent

coordinator = SequentialAgent(
    name="Coordinator",
    sub_agents=[intake_agent, evidence_agent, solution_agent, governance_agent, editor_agent]
)
