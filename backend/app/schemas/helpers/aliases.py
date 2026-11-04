"""Field aliases: accept the English name or the Spanish key(s)."""

from pydantic import AliasChoices


def spanish_alias(english: str, *spanish: str) -> AliasChoices:
    """Accept a field by its English name or any of its Spanish keys.

    Args:
        english: Name used by the code and the API.
        *spanish: Keys used by the LLM prompt (for example ``"minimo"`` and
            ``"mínimo"``).

    Returns:
        The alias choices, English first.
    """
    return AliasChoices(english, *spanish)
