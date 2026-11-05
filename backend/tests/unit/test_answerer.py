import uuid

from app.ai.providers.fake_provider import FakeLLMProvider
from app.ai.rag.answerer import NOT_ENOUGH_INFORMATION, Answerer
from app.domain.dtos import RetrievedChunk, ScoredChunk

DOC = uuid.uuid4()


class _StaticRetriever:
    def __init__(self, fragments: list[RetrievedChunk]) -> None:
        self.fragments = fragments
        self.calls: list = []

    def retrieve(self, question, document_ids=None, pages=None):
        self.calls.append((question, document_ids))
        return self.fragments


def _fragment(page: int, content: str) -> RetrievedChunk:
    chunk = ScoredChunk(
        chunk_id=page, document_id=DOC, filename="poliza.pdf", page=page, content=content, score=1
    )
    return RetrievedChunk(chunk=chunk, similarity=0.9, keyword_match=True, fused_score=0.1)


FRAGMENTS = [_fragment(2, "Cubre robo total."), _fragment(4, "Vigencia 2025.")]


def test_without_fragments_the_llm_is_not_called():
    llm = FakeLLMProvider()
    response = Answerer(_StaticRetriever([]), llm).answer("¿Qué cubre?")
    assert response.answered is False
    assert response.answer == NOT_ENOUGH_INFORMATION
    assert llm.calls == []


def test_citations_map_markers_to_document_and_page():
    llm = FakeLLMProvider(scripted={"answer": ["Cubre robo [1] y vence en 2025 [2]."]})
    response = Answerer(_StaticRetriever(FRAGMENTS), llm).answer("¿Qué cubre?")
    assert response.answered is True
    assert [(c.marker, c.page, c.filename) for c in response.citations] == [
        (1, 2, "poliza.pdf"),
        (2, 4, "poliza.pdf"),
    ]
    assert response.citations[0].excerpt == "Cubre robo total."


def test_only_cited_fragments_are_listed_and_renumbered():
    llm = FakeLLMProvider(scripted={"answer": ["Vence en 2025 [2]."]})
    response = Answerer(_StaticRetriever(FRAGMENTS), llm).answer("¿Cuándo vence?")
    # The model cited the 2nd fragment; it is the only citation, so it becomes [1].
    assert response.answer == "Vence en 2025 [1]."
    assert [(c.marker, c.page) for c in response.citations] == [(1, 4)]


def test_markers_never_exceed_the_number_of_citations():
    fragments = [_fragment(page, f"Texto {page}.") for page in range(1, 7)]
    llm = FakeLLMProvider(
        scripted={"answer": ["Cuatro líneas de negocio [5]. Venden 1.200 al año [1]."]}
    )
    response = Answerer(_StaticRetriever(fragments), llm).answer("¿Cómo es el negocio?")
    assert response.answer == "Cuatro líneas de negocio [1]. Venden 1.200 al año [2]."
    # Each new marker still points to the fragment the model cited.
    assert [(c.marker, c.page) for c in response.citations] == [(1, 5), (2, 1)]


def test_model_reporting_no_evidence_gives_not_enough_information():
    llm = FakeLLMProvider(scripted={"answer": ["NO_EVIDENCE"]})
    response = Answerer(_StaticRetriever(FRAGMENTS), llm).answer("¿Quién ganó el mundial?")
    assert response.answered is False
    assert response.citations == []


def test_uncited_answer_is_treated_as_invented():
    llm = FakeLLMProvider(scripted={"answer": ["La póliza lo cubre todo."]})
    response = Answerer(_StaticRetriever(FRAGMENTS), llm).answer("¿Qué cubre?")
    assert response.answered is False
    assert response.answer == NOT_ENOUGH_INFORMATION


def test_citation_to_a_non_existing_fragment_is_dropped():
    llm = FakeLLMProvider(scripted={"answer": ["Cubre robo [1] e incendio [5]."]})
    response = Answerer(_StaticRetriever(FRAGMENTS), llm).answer("¿Qué cubre?")
    assert "[5]" not in response.answer
    assert [c.marker for c in response.citations] == [1]


def test_search_text_and_document_filter_reach_the_retriever():
    retriever = _StaticRetriever(FRAGMENTS)
    Answerer(retriever, FakeLLMProvider()).answer(
        "¿Qué cubre la póliza FS-1?", [DOC], search_text="¿Qué cubre?"
    )
    assert retriever.calls == [("¿Qué cubre?", [DOC])]


def test_question_is_searched_when_there_is_no_search_text():
    retriever = _StaticRetriever(FRAGMENTS)
    Answerer(retriever, FakeLLMProvider()).answer("¿Qué cubre?")
    assert retriever.calls == [("¿Qué cubre?", None)]
