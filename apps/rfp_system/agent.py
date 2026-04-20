import sys
import os
import certifi

# Fix SSL cert issue for Vertex AI calls in ADK server
os.environ['SSL_CERT_FILE'] = certifi.where()

# Add the root project directory to sys.path so the agents module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from agents.coordinator import coordinator as root_agent
