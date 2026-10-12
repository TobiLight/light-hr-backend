import logging

import pytest
from app.core.config import Configs
from pydantic import ValidationError


def test_log_level_defaults_to_info():
    assert Configs().log_level == "INFO"


def test_log_level_normalizes_case():
    assert Configs(log_level="debug").log_level == "DEBUG"


def test_log_level_strips_surrounding_whitespace():
    assert Configs(log_level="  info \n").log_level == "INFO"


def test_log_level_rejects_unknown_value():
    with pytest.raises(ValidationError) as exc_info:
        Configs(log_level="BOGUS")

    message = str(exc_info.value)
    assert "log_level" in message
    assert "LOG_LEVEL 'BOGUS' is not a valid logging level" in message
    assert "INFO" in message


@pytest.mark.parametrize("level", sorted(logging.getLevelNamesMapping()))
def test_log_level_accepts_every_stdlib_level(level):
    assert Configs(log_level=level).log_level == level
