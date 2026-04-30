"""
Resolve MCP server URLs from the Vertex AI Agent Registry.

Lookup is done by listing all servers and matching on displayName.

Uses direct httpx calls with the system cert bundle so that the Agent Gateway
TLS proxy (which installs its CA into /etc/ssl/certs at startup) is trusted.
The ADK AgentRegistry client uses httpx without explicit cert config and
therefore ignores SSL_CERT_FILE — bypassing it avoids SSL failures in Agent Engine.

When ENFORCE_MCP_REGISTRY=true (set in deployed environments), the registry
lookup is mandatory — env var fallback is disabled and any failure raises
immediately. This guarantees MCP tools are always discovered via Agent Registry.

When ENFORCE_MCP_REGISTRY is unset or false (local dev), falls back to
environment variables if the registry is unreachable or the server is not listed.

Usage:
    from agent_registry_lookup import get_mcp_url

    url = get_mcp_url("rfp-mcp-knowledge", fallback_env_var="KNOWLEDGE_MCP_URL")
"""

import logging
import os

import google.auth
import google.auth.transport.requests
import httpx

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGISTRY_LOCATION = os.getenv("AGENT_REGISTRY_LOCATION", os.getenv("GCP_REGION", "us-central1"))
REGISTRY_BASE = "https://agentregistry.googleapis.com/v1alpha"

# When true, env var fallback is disabled — registry must succeed.
ENFORCE_MCP_REGISTRY = os.getenv("ENFORCE_MCP_REGISTRY", "false").lower() == "true"

# System cert bundle includes Agent Gateway CA installed at container startup.
# httpx ignores SSL_CERT_FILE, so we pass the path explicitly.
_SYSTEM_CERTS = "/etc/ssl/certs/ca-certificates.crt"
_SSL_VERIFY: str | bool = _SYSTEM_CERTS if os.path.exists(_SYSTEM_CERTS) else True

# Module-level cache: displayName -> url, populated on first list call
_url_cache: dict[str, str] = {}
_cache_populated = False
_registry_error: Exception | None = None


def _get_access_token() -> str | None:
    """Return a Bearer token using Application Default Credentials."""
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token
    except Exception as exc:
        logger.warning("Agent Registry: could not obtain ADC token: %s", exc)
        return None


def _extract_url(server: dict) -> str | None:
    """Extract the first interface URL from a server record."""
    for iface in server.get("interfaces", []):
        url = iface.get("url")
        if url:
            return url
    for protocol in server.get("protocols", []):
        for iface in protocol.get("interfaces", []):
            url = iface.get("url")
            if url:
                return url
    return None


def _populate_cache() -> None:
    global _cache_populated, _registry_error
    if _cache_populated:
        return

    if not PROJECT_ID:
        logger.debug("GOOGLE_CLOUD_PROJECT not set — skipping Agent Registry lookup")
        _cache_populated = True
        return

    token = _get_access_token()
    if not token:
        _cache_populated = True
        return

    url = f"{REGISTRY_BASE}/projects/{PROJECT_ID}/locations/{REGISTRY_LOCATION}/mcpServers"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(verify=_SSL_VERIFY, timeout=10) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(
                f"API request failed with status {response.status_code}: {response.text}"
            )

        result = response.json()
        for server in result.get("mcpServers", []):
            display_name = server.get("displayName", "")
            server_url = _extract_url(server)
            if display_name and server_url:
                _url_cache[display_name] = server_url
                logger.info("Agent Registry: Cached %s → %s", display_name, server_url)
                print(f"Agent Registry: Cached {display_name} → {server_url}", flush=True)

        logger.info(
            "Agent Registry: %d server(s) loaded (project=%s, location=%s)",
            len(_url_cache), PROJECT_ID, REGISTRY_LOCATION,
        )
        print(
            f"Agent Registry: {len(_url_cache)} server(s) loaded "
            f"(project={PROJECT_ID}, location={REGISTRY_LOCATION})",
            flush=True,
        )

    except Exception as exc:
        _registry_error = exc
        logger.warning("Agent Registry list failed: %s", exc)
        print(f"Agent Registry list failed: {exc}", flush=True)

    _cache_populated = True


def get_mcp_url(server_id: str, fallback_env_var: str) -> str:
    """Return the URL for a registered MCP server.

    Matches on displayName (which equals the server_id set when registering).

    When ENFORCE_MCP_REGISTRY=true, raises immediately if the server is not in
    the registry — env var fallback is bypassed entirely.

    Args:
        server_id: The displayName used when registering (e.g. 'rfp-mcp-knowledge').
        fallback_env_var: Env var name used as fallback when enforcement is off.

    Returns:
        The resolved MCP server URL.

    Raises:
        RuntimeError: If ENFORCE_MCP_REGISTRY=true and the server is not in registry.
        ValueError: If neither registry nor env var provides a URL.
    """
    _populate_cache()

    if server_id in _url_cache:
        url = _url_cache[server_id]
        logger.info("Agent Registry: Resolved %s → %s (from registry)", server_id, url)
        print(f"Agent Registry: Resolved {server_id} → {url} (from registry)", flush=True)
        return url

    if ENFORCE_MCP_REGISTRY:
        cause = f": {_registry_error}" if _registry_error else " (server not listed)"
        raise RuntimeError(
            f"ENFORCE_MCP_REGISTRY is set but '{server_id}' was not found in "
            f"Agent Registry (location={REGISTRY_LOCATION}){cause}. "
            f"Ensure the server is registered and the Agent Engine SA has "
            f"roles/agentregistry.viewer on the project."
        )

    fallback = os.getenv(fallback_env_var)
    if fallback:
        logger.info(
            "Agent Registry: Resolved %s → %s (from env var %s)",
            server_id, fallback, fallback_env_var,
        )
        print(
            f"Agent Registry: Resolved {server_id} → {fallback} "
            f"(from env var {fallback_env_var})",
            flush=True,
        )
        return fallback

    raise ValueError(
        f"No URL found for MCP server '{server_id}'. "
        f"Register it in Agent Registry or set the {fallback_env_var} environment variable."
    )
