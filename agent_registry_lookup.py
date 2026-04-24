"""
Resolve MCP server URLs from the Vertex AI Agent Registry.

The Agent Registry Console registers servers under location='global' and
assigns auto-generated UUID resource names. Lookup is therefore done by
listing all servers and matching on displayName.

Falls back to environment variables when:
  - Running locally without credentials
  - Agent Registry is unreachable
  - The server is not yet registered

Usage:
    from agent_registry_lookup import get_mcp_url

    url = get_mcp_url("rfp-mcp-knowledge", fallback_env_var="KNOWLEDGE_MCP_URL")
"""

import logging
import os

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

# Servers registered via the Console appear under 'global', not a region.
REGISTRY_LOCATION = "global"

# Module-level cache: displayName -> url, populated on first list call
_url_cache: dict[str, str] = {}
_cache_populated = False
_registry = None
_registry_init_attempted = False


def _get_registry():
    global _registry, _registry_init_attempted
    if _registry_init_attempted:
        return _registry
    _registry_init_attempted = True

    if not PROJECT_ID:
        logger.debug("GOOGLE_CLOUD_PROJECT not set — skipping Agent Registry lookup")
        return None

    try:
        from google.adk.integrations.agent_registry.agent_registry import AgentRegistry
        _registry = AgentRegistry(project_id=PROJECT_ID, location=REGISTRY_LOCATION)
        logger.info(
            "Agent Registry client initialised (project=%s, location=%s)",
            PROJECT_ID, REGISTRY_LOCATION,
        )
    except Exception as exc:
        logger.warning("Could not initialise AgentRegistry: %s", exc)

    return _registry


def _extract_url(server: dict) -> str | None:
    """Extract the first interface URL from a server record.

    The Console registers servers with a top-level 'interfaces' list.
    The REST API registers under 'protocols[].interfaces'.
    Handle both.
    """
    # Top-level interfaces (Console-registered)
    for iface in server.get("interfaces", []):
        url = iface.get("url")
        if url:
            return url

    # Nested under protocols (API-registered)
    for protocol in server.get("protocols", []):
        for iface in protocol.get("interfaces", []):
            url = iface.get("url")
            if url:
                return url

    return None


def _populate_cache():
    global _cache_populated
    if _cache_populated:
        return

    registry = _get_registry()
    if not registry:
        _cache_populated = True
        return

    try:
        result = registry.list_mcp_servers()
        for server in result.get("mcpServers", []):
            display_name = server.get("displayName", "")
            url = _extract_url(server)
            if display_name and url:
                _url_cache[display_name] = url
                logger.info("Cached %s → %s", display_name, url)
        _cache_populated = True
        logger.info("Agent Registry: %d server(s) loaded", len(_url_cache))
    except Exception as exc:
        logger.warning("Agent Registry list failed: %s", exc)
        _cache_populated = True  # Don't retry on every call


def get_mcp_url(server_id: str, fallback_env_var: str) -> str:
    """Return the URL for a registered MCP server.

    Matches on displayName (which equals the server_id we set when registering).
    Falls back to *fallback_env_var* if the registry is unreachable or the
    server is not listed.

    Args:
        server_id: The displayName used when registering (e.g. 'rfp-mcp-knowledge').
        fallback_env_var: Environment variable name to use as fallback URL.

    Returns:
        The resolved MCP server URL.

    Raises:
        ValueError: If neither Agent Registry nor the env var provides a URL.
    """
    _populate_cache()

    if server_id in _url_cache:
        logger.info("Resolved %s → %s (from Agent Registry)", server_id, _url_cache[server_id])
        return _url_cache[server_id]

    fallback = os.getenv(fallback_env_var)
    if fallback:
        logger.info(
            "Resolved %s → %s (from env var %s)", server_id, fallback, fallback_env_var
        )
        return fallback

    raise ValueError(
        f"No URL found for MCP server '{server_id}'. "
        f"Register it in Agent Registry or set the {fallback_env_var} environment variable."
    )
