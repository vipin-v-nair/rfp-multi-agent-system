from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.constants import VERSION_0_9
from typing import List

def get_schema_manager() -> A2uiSchemaManager:
    """Initializes and returns the A2UI Schema Manager using default catalogs."""
    print("A2UI: Initializing Schema Manager")
    return A2uiSchemaManager(
        version=VERSION_0_9,
        catalogs=[BasicCatalog.get_config(version=VERSION_0_9)]
    )

def generate_ui_instruction(role: str, workflow: str, ui_desc: str, allowed_components: List[str]) -> str:
    """Generates system instruction enriched with A2UI schema and examples."""
    sm = get_schema_manager()
    prompt = sm.generate_system_prompt(
        role_description=role,
        workflow_description=workflow,
        ui_description=ui_desc,
        include_schema=True,
        include_examples=True,
        allowed_components=allowed_components
    )
    # Post-process to avoid ADK state injection conflicts with literal braces
    prompt = prompt.replace("{expression}", "[expression]")
    return prompt
