import pytest

from app.ai.extraction.json_output import parse_json_object
from app.core.errors import InvalidLLMOutputError


def test_plain_object_is_parsed():
    assert parse_json_object('{"tipo": "poliza"}') == {"tipo": "poliza"}


@pytest.mark.parametrize("fence", ['```json\n{"a": 1}\n```', '```\n{"a": 1}\n```'])
def test_markdown_fence_is_tolerated(fence):
    assert parse_json_object(fence) == {"a": 1}


@pytest.mark.parametrize("text", ["", "no es json", "{'a': 1}", '{"a": 1', "Respuesta: {}"])
def test_invalid_json_is_rejected(text):
    with pytest.raises(InvalidLLMOutputError):
        parse_json_object(text)


@pytest.mark.parametrize("text", ["[1, 2]", '"texto"', "42", "null"])
def test_non_object_json_is_rejected(text):
    with pytest.raises(InvalidLLMOutputError, match="JSON object"):
        parse_json_object(text)
