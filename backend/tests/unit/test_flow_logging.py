"""Common shape of the flow logs."""

import logging

import pytest

from app.core.flow_logging import fields, log_step

logger = logging.getLogger("tests.flow")


def test_reserved_names_are_prefixed():
    extra = fields(filename="a.pdf", name="x", module="m", document_id="1")
    assert extra == {
        "field_filename": "a.pdf",
        "field_name": "x",
        "field_module": "m",
        "document_id": "1",
    }
    logger.info("works", extra=extra)  # Would raise KeyError without the prefix.


def test_step_logs_info_with_inputs_outputs_and_duration(caplog):
    with (
        caplog.at_level(logging.DEBUG, logger="tests.flow"),
        log_step(logger, "text chunked", document_id="d1") as out,
    ):
        out["chunks"] = 3
    started, finished = caplog.records
    assert (started.levelno, started.getMessage()) == (logging.DEBUG, "text chunked: started")
    assert (finished.levelno, finished.getMessage()) == (logging.INFO, "text chunked")
    assert finished.document_id == "d1"
    assert finished.chunks == 3
    assert finished.duration_ms >= 0


def test_failed_step_logs_a_warning_and_reraises(caplog):
    with (
        caplog.at_level(logging.INFO, logger="tests.flow"),
        pytest.raises(ValueError),
        log_step(logger, "document classified", document_id="d1"),
    ):
        raise ValueError("bad pdf")
    (record,) = caplog.records
    assert record.levelno == logging.WARNING
    assert record.getMessage() == "document classified: failed"
    assert (record.error_type, record.error, record.document_id) == ("ValueError", "bad pdf", "d1")


def test_info_level_hides_the_debug_start_line(caplog):
    with caplog.at_level(logging.INFO, logger="tests.flow"), log_step(logger, "step"):
        pass
    assert [r.levelno for r in caplog.records] == [logging.INFO]
