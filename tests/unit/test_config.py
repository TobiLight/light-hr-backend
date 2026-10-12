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


@pytest.mark.parametrize("env", ["staging", "production", "test"])
def test_debug_rejected_outside_dev(env):
    with pytest.raises(ValidationError) as exc_info:
        Configs(debug=True, app_env=env)

    message = str(exc_info.value)
    assert "debug" in message
    assert "app_env" in message


def test_debug_rejected_in_production():
    with pytest.raises(ValidationError):
        Configs(debug=True, app_env="production")


def test_debug_rejected_in_staging():
    with pytest.raises(ValidationError):
        Configs(debug=True, app_env="staging")


def test_debug_allowed_in_dev():
    assert Configs(debug=True, app_env="dev").debug is True


@pytest.mark.parametrize("env", ["dev", "test", "staging", "production"])
def test_debug_false_always_allowed(env):
    assert Configs(debug=False, app_env=env).debug is False
