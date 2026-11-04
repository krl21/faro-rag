"""Result of a chat completion."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Result of a chat completion.

    Attributes:
        text: Generated text.
        model: Model that produced the answer.
        input_tokens: Prompt tokens, when the provider reports them.
        output_tokens: Completion tokens, when the provider reports them.
    """

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
