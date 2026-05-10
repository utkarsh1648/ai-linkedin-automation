"""
Prompt Loader Utility
---------------------
Loads prompt templates from .txt files in the `prompts/` directory.
If a file is missing, falls back to the hardcoded default string provided.

Usage:
    from utils.prompt_loader import load_prompt

    my_prompt = load_prompt("select_top_trending", fallback=DEFAULT_TEXT)
"""

import os

# Resolve the prompts/ directory relative to this project root
_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(name: str, fallback: str = "") -> str:
    """
    Load a prompt template from `prompts/<name>.txt`.

    Args:
        name:     Filename without extension (e.g. "select_top_trending").
        fallback: Default prompt string returned if the file doesn't exist.

    Returns:
        The prompt string (stripped of leading/trailing whitespace).
    """
    file_path = os.path.join(_PROMPTS_DIR, f"{name}.txt")
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return fallback.strip()
