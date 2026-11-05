"""Conversations: creation, continuation, stored messages and the history sent to the LLM."""

import uuid
from datetime import date

import pytest

from app.ai.providers.fake_provider import FakeLLMProvider
from app.ai.query.interpreter import QueryInterpreter
from app.ai.query.llm_parser import QUERY_PURPOSE, LLMQueryParser
from app.ai.rag.answerer import Answerer
from app.config import get_settings
from app.db.repositories import ConversationRepository
from app.db.session import SessionLocal, session_scope
from app.services.chat_service import ChatService
from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def test_first_question_creates_a_conversation_and_next_ones_continue_it(client):
    first = client.post("/ask", json={"question": "necesito las facturas"}).json()
    conversation_id = first["conversation_id"]
    second = client.post(
        "/ask", json={"question": "¿y las pólizas?", "conversation_id": conversation_id}
    ).json()
    assert second["conversation_id"] == conversation_id

    detail = client.get(f"/conversations/{conversation_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][0]["content"] == "necesito las facturas"
    assert detail["messages"][1]["details"]["mode"] == "list"
    assert detail["messages"][1]["details"]["filters"]["document_type"] == "invoice"
    assert detail["messages"][0]["details"] is None


def test_each_question_without_id_starts_a_new_conversation(client):
    a = client.post("/ask", json={"question": "necesito las facturas"}).json()
    b = client.post("/ask", json={"question": "necesito las facturas"}).json()
    assert a["conversation_id"] != b["conversation_id"]


def test_unknown_conversation_returns_404(client):
    response = client.post(
        "/ask", json={"question": "hola mundo", "conversation_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"
    assert client.get(f"/conversations/{uuid.uuid4()}").status_code == 404


def test_invalid_conversation_id_returns_422(client):
    assert client.get("/conversations/no-es-uuid").status_code == 422


def test_answer_with_citations_is_stored(client):
    client.post("/documents", files={"file": ("p.pdf", make_pdf([POLICY_TEXT]), "application/pdf")})
    body = client.post("/ask", json={"question": "¿qué coberturas incluye?"}).json()
    detail = client.get(f"/conversations/{body['conversation_id']}").json()
    stored = detail["messages"][1]["details"]
    assert stored["mode"] == "answer"
    assert stored["citations"] == body["citations"]


def test_appends_from_two_sessions_are_not_lost(clean_database):
    with session_scope() as session:
        conversation_id = ConversationRepository(session).create().id
    first, second = SessionLocal(), SessionLocal()
    try:
        ConversationRepository(first).get(conversation_id)  # Both read the same state...
        ConversationRepository(second).get(conversation_id)
        ConversationRepository(first).append(conversation_id, [{"n": 1}])
        first.commit()
        ConversationRepository(second).append(conversation_id, [{"n": 2}])
        second.commit()
    finally:
        first.close()
        second.close()
    with session_scope() as session:
        messages = ConversationRepository(session).get(conversation_id).messages
    assert messages == [{"n": 1}, {"n": 2}]  # ...and neither append overwrites the other.


class _Retriever:
    def retrieve(self, question, document_ids=None, pages=None):
        return []

    def retrieve_sources(self, question, document_ids=None, pages=None):
        return [], []


def _chat_service(session, llm: FakeLLMProvider, context_turns: int = 3) -> ChatService:
    settings = get_settings()
    parser = LLMQueryParser(llm, timezone=settings.timezone, retry_delays=[], sleep=lambda _: None)
    return ChatService(
        session,
        QueryInterpreter(parser),
        Answerer(_Retriever(), llm),
        tz=settings.tzinfo,
        context_turns=context_turns,
        list_limit=10,
    )


def _llm_history(llm: FakeLLMProvider) -> str:
    prompts = [messages[-1].content for purpose, messages in llm.calls if purpose == QUERY_PURPOSE]
    return prompts[-1]


def test_only_the_last_three_exchanges_are_sent_to_the_llm(clean_database):
    llm = FakeLLMProvider()
    session = SessionLocal()
    try:
        service = _chat_service(session, llm)
        conversation_id = service.ask("pregunta uno sobre coberturas").conversation_id
        for n in ("dos", "tres", "cuatro"):
            service.ask(f"pregunta {n} sobre coberturas", conversation_id=conversation_id)
        service.ask("¿y la de B?", conversation_id=conversation_id)  # Reference: LLM needed.
    finally:
        session.close()
    prompt = _llm_history(llm)
    assert "pregunta uno" not in prompt
    for n in ("dos", "tres", "cuatro"):
        assert f"pregunta {n}" in prompt
    assert prompt.count('rol="usuario"') == 3
    assert prompt.count('rol="asistente"') == 3
    assert "¿y la de B?" in prompt.split("<peticion>")[1]


def test_history_can_be_disabled(clean_database):
    llm = FakeLLMProvider()
    session = SessionLocal()
    try:
        service = _chat_service(session, llm, context_turns=0)
        conversation_id = service.ask("pregunta uno").conversation_id
        service.ask("pólizas de Juan Pérez", conversation_id=conversation_id)
    finally:
        session.close()
    assert "(sin mensajes anteriores)" in _llm_history(llm)


def test_relative_dates_use_the_configured_time_zone(clean_database):
    from datetime import UTC, datetime

    llm = FakeLLMProvider()
    session = SessionLocal()
    try:
        service = _chat_service(session, llm)
        # 03:00 UTC on 4 November is still 3 November in Toronto (UTC-5).
        service._clock = lambda: datetime(2026, 11, 4, 3, 0, tzinfo=UTC)
        result = service.ask("facturas subidas ayer")
    finally:
        session.close()
    assert result.filters.uploaded.start == date(2026, 11, 2)
