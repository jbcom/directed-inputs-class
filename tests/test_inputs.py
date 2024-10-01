"""Test suite for the inputs.py module handling directed inputs with Pydantic.

This suite tests the functionality of the DirectedInputsSettings class,
ensuring it correctly loads inputs from various sources like environment variables,
stdin, and custom settings sources. It also verifies that the customization
of settings sources behaves as expected.
"""

from __future__ import annotations

import os
import pytest
from pytest_mock import MockerFixture
from typing import Dict, Any, Tuple, Type

from pydantic import ValidationError
from pydantic_settings import PydanticBaseSettingsSource
from inputs import DirectedInputsSettings, StdinSettingsSource


@pytest.fixture
def clear_env() -> None:
    """Fixture to clear specific environment variables before each test.

    This fixture removes any environment variables starting with
    'DIRECTED_INPUTS_' to ensure a clean environment for each test.
    """
    keys_to_clear = [key for key in os.environ.keys() if key.startswith("DIRECTED_INPUTS_")]
    for key in keys_to_clear:
        del os.environ[key]


def test_load_from_environment(monkeypatch: pytest.MonkeyPatch, clear_env: None) -> None:
    """Test loading settings from environment variables.

    This test verifies that the DirectedInputsSettings class correctly loads
    settings from environment variables when 'from_environment' is set to True.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture to modify environment variables.
        clear_env (None): Fixture to clear specific environment variables.
    """
    monkeypatch.setenv("DIRECTED_INPUTS_FROM_ENVIRONMENT", "True")
    monkeypatch.setenv("DIRECTED_INPUTS_FROM_STDIN", "False")

    settings = DirectedInputsSettings()
    assert settings.from_environment is True
    assert settings.from_stdin is False


def test_load_from_stdin(mocker: MockerFixture) -> None:
    """Test loading settings from stdin.

    This test verifies that the StdinSettingsSource class correctly loads
    inputs from stdin when 'from_stdin' is enabled and the environment variable
    'OVERRIDE_STDIN' is not set to True.

    Args:
        mocker (MockerFixture): Fixture for mocking input and environment variables.
    """
    mocker.patch("sys.stdin.read", return_value='{"test_key": "test_value"}')
    mocker.patch.dict(os.environ, {"OVERRIDE_STDIN": "False"})

    stdin_source = StdinSettingsSource(DirectedInputsSettings)
    result = stdin_source()
    assert result["test_key"] == "test_value"


def test_stdin_override(mocker: MockerFixture) -> None:
    """Test that stdin is not read when OVERRIDE_STDIN is set to True.

    This test ensures that the StdinSettingsSource does not read from stdin
    when the 'OVERRIDE_STDIN' environment variable is set to True.

    Args:
        mocker (MockerFixture): Fixture for mocking input and environment variables.
    """
    mocker.patch("sys.stdin.read", return_value='{"test_key": "test_value"}')
    mocker.patch.dict(os.environ, {"OVERRIDE_STDIN": "True"})

    stdin_source = StdinSettingsSource(DirectedInputsSettings)
    result = stdin_source()
    assert "test_key" not in result


def test_custom_settings_sources_order() -> None:
    """Test customization of settings sources order.

    This test verifies that the DirectedInputsSettings class correctly allows
    customization of the settings sources order by overriding the
    settings_customise_sources method.
    """

    class CustomSettings(DirectedInputsSettings):
        @classmethod
        def settings_customise_sources(
                cls,
                settings_cls: Type[DirectedInputsSettings],
                init_settings: PydanticBaseSettingsSource,
                env_settings: PydanticBaseSettingsSource,
                dotenv_settings: PydanticBaseSettingsSource,
                file_secret_settings: PydanticBaseSettingsSource,
        ) -> Tuple[PydanticBaseSettingsSource, ...]:
            # Custom order: stdin first, then env, then init
            return StdinSettingsSource(settings_cls), env_settings, init_settings

    mocker = MockerFixture()
    mocker.patch("sys.stdin.read", return_value='{"test_key": "test_value"}')
    mocker.patch.dict(os.environ, {"DIRECTED_INPUTS_FROM_ENVIRONMENT": "False"})

    settings = CustomSettings()
    assert settings.dict().get("test_key") == "test_value"


def test_validation_error_on_missing_required_fields(clear_env: None) -> None:
    """Test that a ValidationError is raised when required fields are missing.

    This test ensures that the DirectedInputsSettings class raises a
    ValidationError when required fields are not provided.

    Args:
        clear_env (None): Fixture to clear specific environment variables.
    """
    with pytest.raises(ValidationError) as excinfo:
        DirectedInputsSettings(from_stdin=True)
    assert "validation error" in str(excinfo.value).lower()


def test_settings_reload(mocker: MockerFixture) -> None:
    """Test reloading settings in place after changing environment variables.

    This test verifies that the DirectedInputsSettings instance correctly reloads
    its values in place after the environment variables have changed.

    Args:
        mocker (MockerFixture): Fixture for mocking input and environment variables.
    """
    mocker.patch.dict(os.environ, {"DIRECTED_INPUTS_FROM_ENVIRONMENT": "True"})
    settings = DirectedInputsSettings()
    assert settings.from_environment is True

    mocker.patch.dict(os.environ, {"DIRECTED_INPUTS_FROM_ENVIRONMENT": "False"})
    settings.__init__()  # Reload settings in place
    assert settings.from_environment is False
