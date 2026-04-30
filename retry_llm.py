"""
Shared Gemini model instance with exponential backoff retry for 429 errors.

gemini_pro is used in place of the "gemini-2.5-pro" string in LlmAgent
definitions so that all agents share the same retry configuration.
"""

from google.adk.models.google_llm import Gemini
from google.genai import types

gemini_pro = Gemini(
    model="gemini-2.5-pro",
    retry_options=types.HttpRetryOptions(
        http_status_codes=[429],
        attempts=6,
        initial_delay=10.0,
        max_delay=120.0,
        exp_base=2.0,
        jitter=1.0,
    ),
)
