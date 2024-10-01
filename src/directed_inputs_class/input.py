"""Module for Pydantic settings and input models for directed input handling.

This module defines the Pydantic settings models used by the DirectedInputsClass
to manage and validate inputs from various sources. Developers can customize the
sources of inputs using the `settings_customise_sources` method to fit their needs.
"""

from __future__ import annotations

import binascii
import json
import os
import sys
from copy import deepcopy
from typing import Any, Dict, Tuple, Type, Union

from pydantic import BaseSettings, Field, PrivateAttr, ValidationError
from pydantic_settings import PydanticBaseSettingsSource
from deepmerge import Merger
from extended_data_types import is_nothing, strtobool, decode_json, decode_yaml, base64_decode
from yaml import YAMLError


class StdinSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that loads variables from stdin if enabled."""

    def __call__(self) -> Dict[str, Any]:
        """Reads input from stdin and decodes it as JSON.

        Returns:
            Dict[str, Any]: The decoded settings from stdin.

        Raises:
            RuntimeError: If decoding from stdin fails.
        """
        d: Dict[str, Any] = {}

        if not strtobool(os.getenv("OVERRIDE_STDIN", "False")):
            inputs_from_stdin = sys.stdin.read()
            if not is_nothing(inputs_from_stdin):
                try:
                    d.update(decode_json(inputs_from_stdin))
                except json.JSONDecodeError as exc:
                    message = f"Failed to decode stdin:\n{inputs_from_stdin}"
                    raise RuntimeError(message) from exc

        return d


class DirectedInputsSettings(BaseSettings):
    """Pydantic settings model to handle directed inputs.

    This model manages inputs from various sources, providing type validation
    and parsing. It supports customization of input sources via the
    `settings_customise_sources` method.

    Attributes:
        from_environment (bool): Flag to load inputs from environment variables.
        from_stdin (bool): Flag to load inputs from standard input.
    """

    from_environment: bool = Field(True, description="Flag to load inputs from environment variables.")
    from_stdin: bool = Field(False, description="Flag to load inputs from standard input.")

    # Private attributes to handle input states and merging
    _inputs: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _frozen_inputs: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _inputs_merger: Merger = PrivateAttr(default_factory=lambda: Merger(
        [(list, ["append"]), (dict, ["merge"]), (set, ["union"])],
        ["override"],
        ["override"],
    ))

    class Config:
        env_prefix = "DIRECTED_INPUTS_"

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customizes the order and sources of settings.

        This method allows developers to change the priority of input sources
        or add custom sources to the settings loading process.

        Args:
            settings_cls (Type[BaseSettings]): The settings class.
            init_settings (PydanticBaseSettingsSource): Initial settings source.
            env_settings (PydanticBaseSettingsSource): Environment variables settings source.
            dotenv_settings (PydanticBaseSettingsSource): Dotenv file settings source.
            file_secret_settings (PydanticBaseSettingsSource): File secret settings source.

        Returns:
            Tuple[PydanticBaseSettingsSource, ...]: The customized order of settings sources.
        """
        # Default sources: environment -> stdin -> initialization -> dotenv -> file secrets
        sources = [
            env_settings if cls.from_environment else None,
            StdinSettingsSource(settings_cls) if cls.from_stdin else None,
            init_settings,
            dotenv_settings,
            file_secret_settings,
        ]

        # Filter out any None values in the sources list
        return tuple(source for source in sources if source is not None)

    def get_input(
            self,
            key: str,
            default: Any | None = None,
            required: bool = False,
            is_bool: bool = False,
            is_integer: bool = False,
            is_float: bool = False,
    ) -> Any:
        """Retrieves an input by key, with options for type conversion and default values.

        Args:
            key (str): The key for the input.
            default (Any | None): The default value if the key is not found.
            required (bool): Whether the input is required. Raises an error if required and not found.
            is_bool (bool): Whether to convert the input to a boolean.
            is_integer (bool): Whether to convert the input to an integer.
            is_float (bool): Whether to convert the input to a float.

        Returns:
            Any: The retrieved input, potentially converted or defaulted.

        Raises:
            RuntimeError: If the input cannot be converted to the specified type or is required but not found.
        """
        inp = self._inputs.get(key.casefold(), default)

        if is_nothing(inp):
            inp = default

        if is_bool:
            inp = strtobool(inp)

        if is_integer and inp is not None:
            try:
                inp = int(inp)
            except (TypeError, ValueError) as exc:
                message = f"Input {key} not an integer: {inp}"
                raise RuntimeError(message) from exc

        if is_float and inp is not None:
            try:
                inp = float(inp)
            except (TypeError, ValueError) as exc:
                message = f"Input {key} not a float: {inp}"
                raise RuntimeError(message) from exc

        if is_nothing(inp) and required:
            message = f"Required input {key} not passed from inputs:\n{self._inputs}"
            raise RuntimeError(message)

        return inp

    def decode_input(
            self,
            key: str,
            default: Any | None = None,
            required: bool = False,
            decode_from_json: bool = False,
            decode_from_yaml: bool = False,
            decode_from_base64: bool = False,
            allow_none: bool = True,
            decode_type: Type | None = None
    ) -> Any:
        """Decodes an input value, optionally from Base64, JSON, or YAML.

        Args:
            key (str): The key for the input.
            default (Any | None): The default value if the key is not found.
            required (bool): Whether the input is required. Raises an error if required and not found.
            decode_from_json (bool): Whether to decode the input from JSON format.
            decode_from_yaml (bool): Whether to decode the input from YAML format.
            decode_from_base64 (bool): Whether to decode the input from Base64.
            allow_none (bool): Whether to allow None as a valid return value.
            decode_type (Type | None): Custom decoding type that specifies the exact decoding strategy.
                                       Overrides the boolean decode flags if provided.

        Returns:
            Any: The decoded input, potentially converted or defaulted.

        Raises:
            RuntimeError: If decoding fails or input is required but missing.
        """
        # If decode_type is provided, override the boolean decoding flags
        if decode_type:
            decode_from_json = issubclass(decode_type, (JSONDecoded, JSONAndBase64Decoded, JSONWithoutBase64Decoded))
            decode_from_yaml = issubclass(decode_type, (YAMLDecoded, YAMLAndBase64Decoded, YAMLWithoutBase64Decoded))
            decode_from_base64 = issubclass(decode_type, (Base64Decoded, JSONAndBase64Decoded, YAMLAndBase64Decoded))

        conf = self.get_input(key, default=default, required=required)

        if conf is None or conf == default:
            return conf

        # Decode based on specified decoding flags or type
        if decode_from_base64:
            try:
                conf = base64_decode(
                    conf,
                    unwrap_raw_data=decode_from_json or decode_from_yaml,
                    encoding="json" if decode_from_json else "yaml",
                )
            except binascii.Error as exc:
                message = f"Failed to decode {conf} from base64"
                raise RuntimeError(message) from exc

        if isinstance(conf, memoryview):
            conf = conf.tobytes().decode("utf-8")
        elif isinstance(conf, (bytes, bytearray)):
            try:
                conf = conf.decode("utf-8")
            except UnicodeDecodeError as exc:
                message = f"Failed to decode bytes to string: {conf}"
                raise RuntimeError(message) from exc

        if decode_from_yaml:
            try:
                conf = decode_yaml(conf)
            except YAMLError as exc:
                message = f"Failed to decode {conf} from YAML"
                raise RuntimeError(message) from exc
        elif decode_from_json:
            try:
                conf = decode_json(conf)
            except json.JSONDecodeError as exc:
                message = f"Failed to decode {conf} from JSON"
                raise RuntimeError(message) from exc

        if conf is None and not allow_none:
            return default

        return conf

