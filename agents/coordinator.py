from google.adk.agents import SequentialAgent
from agents.document_ingestion import document_ingestion_agent
from agents.intake import intake_agent
from agents.evidence import evidence_agent
from agents.solution import solution_agent
from agents.governance import governance_agent
from agents.editor import editor_agent

coordinator = SequentialAgent(
    name="Coordinator",
    sub_agents=[document_ingestion_agent, intake_agent, evidence_agent, solution_agent, governance_agent, editor_agent]
)
