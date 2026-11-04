import pytest

from app.core.retry import retry


def test_returns_without_waiting_on_success():
    waits: list[float] = []

    @retry(delays=(2, 6), sleep=waits.append)
    def ok() -> str:
        return "ok"

    assert ok() == "ok"
    assert waits == []


def test_waits_the_given_intervals_until_success():
    waits: list[float] = []
    calls = {"n": 0}

    @retry(delays=(2, 6), exceptions=(ValueError,), sleep=waits.append)
    def flaky() -> int:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("todavía no")
        return calls["n"]

    assert flaky() == 3
    assert waits == [2, 6]


def test_reraises_after_the_last_interval():
    waits: list[float] = []

    @retry(delays=(2, 6), exceptions=(ValueError,), sleep=waits.append)
    def always_fails() -> None:
        raise ValueError("siempre")

    with pytest.raises(ValueError, match="siempre"):
        always_fails()
    assert waits == [2, 6]


def test_other_exceptions_are_not_retried():
    waits: list[float] = []

    @retry(delays=(1,), exceptions=(ValueError,), sleep=waits.append)
    def wrong_type() -> None:
        raise KeyError("x")

    with pytest.raises(KeyError):
        wrong_type()
    assert waits == []
