import math

from app.ai.providers.fake_provider import FakeEmbeddingProvider, FakeLLMProvider
from app.ai.providers.traced import TracedLLMProvider


def _cosine(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_fake_embeddings_are_deterministic_and_normalized():
    provider = FakeEmbeddingProvider(dimension=64)
    first, second = provider.embed(["póliza de hogar", "póliza de hogar"])
    assert first == second
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)
    assert len(first) == 64


def test_fake_embeddings_reflect_word_overlap():
    provider = FakeEmbeddingProvider(dimension=384)
    query, related, unrelated = provider.embed(
        ["cobertura de robo", "la póliza incluye cobertura de robo total", "receta de paella"]
    )
    assert _cosine(query, related) > _cosine(query, unrelated)


def test_empty_text_has_a_defined_vector():
    vector = FakeEmbeddingProvider(dimension=8).embed([""])[0]
    assert math.isclose(sum(v * v for v in vector), 1.0)


def test_scripted_replies_are_used_in_order_then_default():
    llm = FakeLLMProvider(scripted={"answer": ["primera"]})
    assert llm.complete([], purpose="answer").text == "primera"
    assert llm.complete([], purpose="answer").text == "NO_EVIDENCE"


def test_traced_wrapper_returns_inner_response():
    traced = TracedLLMProvider(FakeLLMProvider(scripted={"answer": ["hola"]}))
    response = traced.complete([], purpose="answer")
    assert response.text == "hola"
    assert traced.model == "fake-llm"
