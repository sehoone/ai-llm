"""This file contains the prompts for the agent."""

import os
from datetime import datetime

from src.common.config import settings


def load_system_prompt(**kwargs):
    """Load and render the system prompt.

    The template is rendered with ``str.format``, but the prompt body contains
    literal braces (e.g. JavaScript/JSON code examples). To let prose and code use
    ``{`` / ``}`` freely, every brace is escaped first and only the known
    placeholders are re-opened before formatting.
    """
    values = {
        "agent_name": settings.PROJECT_NAME + " Agent",
        "current_date_and_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **kwargs,
    }
    # Placeholders that must be interpolated (restored after brace-escaping).
    placeholders = {"agent_name", "current_date_and_time", "long_term_memory"} | set(kwargs)

    with open(os.path.join(os.path.dirname(__file__), "system.md"), "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("{", "{{").replace("}", "}}")
    for key in placeholders:
        text = text.replace("{{" + key + "}}", "{" + key + "}")

    return text.format(**values)
