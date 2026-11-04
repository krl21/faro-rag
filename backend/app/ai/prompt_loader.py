"""Load the LLM prompts from the ``.txt`` files in ``app/ai/prompts/``.

Prompts live in plain text files so they can be read and tuned without
touching code. Each file is read from disk once per process (``lru_cache``);
the modules that use a prompt load it into a module constant at import time.

Variable parts are written as ``$name`` (``string.Template``), because the
prompts contain JSON examples whose braces would clash with ``str.format``.
"""

from functools import cache
from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent / "prompts"
"""Folder with the prompt files, one subfolder per use (extraction, query, rag)."""


@cache
def load_prompt(name: str) -> Template:
    """Read a prompt file once and keep it in memory.

    Args:
        name: Path relative to ``app/ai/prompts/``, for example
            ``"extraction/classify_system.txt"``.

    Returns:
        The prompt as a template (the file's trailing newline is dropped).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    return Template(text.removesuffix("\n"))


def render(template: Template, **values: object) -> str:
    """Fill the ``$name`` placeholders of a prompt.

    Args:
        template: Prompt loaded with ``load_prompt``.
        **values: Value of each placeholder.

    Returns:
        The final text.

    Raises:
        KeyError: If a placeholder has no value, so a half-built prompt never
            reaches the LLM.
    """
    return template.substitute(**values)
