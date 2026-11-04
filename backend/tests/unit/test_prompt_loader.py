"""Prompts come from .txt files, are read once and never reach the LLM half-built."""

import re
from pathlib import Path
from string import Template

import pytest

from app.ai import prompt_loader
from app.ai.prompt_loader import PROMPTS_DIR, load_prompt, render

PROMPT_FILES = sorted(p.relative_to(PROMPTS_DIR).as_posix() for p in PROMPTS_DIR.rglob("*.txt"))


def test_there_are_prompt_files_for_each_use():
    folders = {name.split("/")[0] for name in PROMPT_FILES}
    assert folders == {"extraction", "query", "rag"}


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_every_prompt_file_loads(name):
    template = load_prompt(name)
    assert isinstance(template, Template)
    assert template.template.strip()
    assert not template.template.endswith("\n")


def test_every_prompt_file_is_loaded_by_the_code(monkeypatch):
    import importlib

    from app.ai.extraction import prompts as extraction
    from app.ai.query import prompts as query
    from app.ai.rag import prompt_builder

    loaded: list[str] = []
    original = prompt_loader.load_prompt

    def recording(name: str):
        loaded.append(name)
        return original(name)

    monkeypatch.setattr(prompt_loader, "load_prompt", recording)
    modules = (extraction, query, prompt_builder)
    try:
        for module in modules:
            importlib.reload(module)  # Re-runs the module-level loading.
    finally:
        monkeypatch.undo()
        for module in modules:
            importlib.reload(module)
    assert sorted(set(loaded)) == PROMPT_FILES


def test_a_file_is_read_from_disk_only_once(monkeypatch):
    load_prompt.cache_clear()
    reads = []
    original = Path.read_text

    def counting_read(self, *args, **kwargs):
        reads.append(self.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read)
    first = load_prompt("rag/fragment.txt")
    second = load_prompt("rag/fragment.txt")
    assert first is second
    assert reads == ["fragment.txt"]


def test_render_fills_the_placeholders():
    text = render(Template('Hola $nombre, {"json": true}'), nombre="Ana")
    assert text == 'Hola Ana, {"json": true}'


def test_render_fails_when_a_placeholder_is_missing():
    with pytest.raises(KeyError):
        render(load_prompt("rag/answer_user.txt"), context="x")


def test_values_are_not_reinterpreted_as_placeholders():
    text = render(load_prompt("rag/answer_user.txt"), context="$question", question="¿qué?")
    assert "$question" in text


def test_unknown_prompt_file_fails():
    with pytest.raises(FileNotFoundError):
        load_prompt("no/existe.txt")


def test_modules_load_their_prompts_at_import():
    from app.ai.extraction import prompts as extraction
    from app.ai.query import prompts as query
    from app.ai.rag import prompt_builder
    from app.domain.enums import DocumentInput

    assert "Reglas de seguridad" in extraction._CLASSIFY_SYSTEM[DocumentInput.PDF]
    assert "filtros de búsqueda" in query.QUERY_SYSTEM
    assert "NO_EVIDENCE" in prompt_builder.ANSWER_SYSTEM
    assert "$" not in prompt_builder.ANSWER_SYSTEM


def test_rendered_prompts_have_no_leftover_placeholders():
    from datetime import date

    from app.ai.extraction.prompts import build_classification_messages, build_extraction_messages
    from app.ai.query.prompts import build_query_messages
    from app.domain.dtos import LLMDocument
    from app.domain.enums import DocumentInput, DocumentType

    document = LLMDocument(pdf=b"%PDF", filename="p.pdf", text="[Página 1]\nx", page_count=1)
    messages = [
        *build_classification_messages(document, DocumentInput.TEXT, 100),
        *build_extraction_messages(DocumentType.POLICY, document, DocumentInput.PDF),
        *build_query_messages("hola", [], date(2026, 11, 4), "America/Toronto"),
    ]
    for message in messages:
        assert not re.search(r"\$[a-z_]+", message.content), message.content[:80]


def test_loader_module_exposes_the_prompts_folder():
    assert prompt_loader.PROMPTS_DIR.name == "prompts"
    assert (prompt_loader.PROMPTS_DIR / "extraction" / "classify_system_pdf.txt").exists()


def _block(name: str, first_line: str) -> str:
    """Return the paragraph of a prompt file that starts with ``first_line``."""
    text = load_prompt(name).template
    start = text.index(first_line)
    end = text.find("\n\n", start)
    return text[start : end if end != -1 else len(text)]


@pytest.mark.parametrize("mode", ["pdf", "text"])
def test_security_rules_are_the_same_in_every_prompt_of_a_mode(mode):
    names = [n for n in PROMPT_FILES if "_system_" in n and n.endswith(f"_{mode}.txt")]
    assert len(names) == 3  # classification + policy + invoice.
    blocks = {_block(n, "Reglas de seguridad:") for n in names}
    assert len(blocks) == 1, "the security rules differ between files of the same mode"


@pytest.mark.parametrize("first_line", ["Campos comunes", "Para cada campo devuelve"])
def test_shared_extraction_blocks_are_the_same_in_every_file(first_line):
    names = [n for n in PROMPT_FILES if n.startswith("extraction/extract_system_")]
    assert len(names) == 4
    assert len({_block(n, first_line) for n in names}) == 1


def test_each_message_file_is_complete():
    # The code never joins prompt pieces: only these value placeholders exist.
    allowed = {
        "text",
        "error",
        "today",
        "timezone",
        "history",
        "question",
        "role",
        "content",
        "no_evidence_token",
        "context",
        "number",
        "filename",
        "page",
    }
    for name in PROMPT_FILES:
        found = set(re.findall(r"\$([a-z_]+)", load_prompt(name).template))
        assert found <= allowed, f"{name} has prompt-piece placeholders: {found - allowed}"
