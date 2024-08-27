"""
Module to handle directed inputs for the DirectedInputsClass library.

This module provides functionality for managing inputs from various sources
(environment, stdin) and allows for dynamic merging, freezing, and thawing
of inputs. It includes methods to decode inputs from JSON, YAML, and Base64
formats, as well as handling boolean and integer conversions.
"""

from __future__ import annotations

import binascii
import json
import os
import sys
from copy import deepcopy
from typing import Any

from case_insensitive_dict import CaseInsensitiveDict
from deepmerge import Merger  # type: ignore
from extended_data_types import is_nothing, strtobool, base64_decode, decode_json, decode_yaml
from yaml import YAMLError


class DirectedInputsClass:
    """
    A class to manage and process directed inputs from environment variables,
    stdin, or provided dictionaries.

    Attributes:
        inputs (CaseInsensitiveDict): Dictionary to store inputs.
        frozen_inputs (CaseInsensitiveDict): Dictionary to store frozen inputs.
        from_stdin (bool): Flag indicating if inputs were read from stdin.
        merger (Merger): Object to manage deep merging of dictionaries.
    """

    def __init__(
            self,
            inputs: Any | None = None,
            from_environment: bool = True,
            from_stdin: bool = False,
    ):
        """
        Initializes the DirectedInputsClass with the provided inputs,
        optionally loading additional inputs from environment variables and stdin.

        Args:
            inputs (Any | None): Initial inputs to be processed.
            from_environment (bool): Whether to load inputs from environment variables.
            from_stdin (bool): Whether to load inputs from stdin.
        """
        if inputs is None:
            inputs = {}

        if from_environment:
            inputs.update(os.environ)

        if from_stdin and not strtobool(os.getenv("OVERRIDE_STDIN", "False")):
            inputs_from_stdin = sys.stdin.read()

            if not is_nothing(inputs_from_stdin):
                try:
                    inputs.update(decode_json(inputs_from_stdin))
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Failed to decode stdin:\n{inputs_from_stdin}"
                    ) from exc

        self.from_stdin = from_stdin
        self.inputs: CaseInsensitiveDict[str, Any] = CaseInsensitiveDict(inputs)
        self.frozen_inputs: CaseInsensitiveDict[str, Any] = CaseInsensitiveDict()
        self.merger = Merger(
            [(list, ["append"]), (dict, ["merge"]), (set, ["union"])],
            ["override"],
            ["override"],
        )

    def get_input(
            self,
            k: str,
            default: Any | None = None,
            required: bool = False,
            is_bool: bool = False,
            is_integer: bool = False
    ) -> Any:
        """
        Retrieves an input by key, with options for type conversion and default values.

        Args:
            k (str): The key for the input.
            default (Any | None): The default value if the key is not found.
            required (bool): Whether the input is required. Raises an error if required and not found.
            is_bool (bool): Whether to convert the input to a boolean.
            is_integer (bool): Whether to convert the input to an integer.

        Returns:
            Any: The retrieved input, potentially converted or defaulted.
        """
        inp = self.inputs.get(k, default)

        if is_nothing(inp):
            inp = default

        if is_bool:
            inp = strtobool(inp)

        if is_integer and inp is not None:
            try:
                inp = int(inp)
            except TypeError as exc:
                raise RuntimeError(f"Input {k} not an integer: {inp}") from exc

        if is_nothing(inp) and required:
            raise RuntimeError(
                f"Required input {k} not passed from inputs:\n{self.inputs}"
            )

        return inp

    def decode_input(
            self,
            k: str,
            default: Any | None = None,
            required: bool = False,
            decode_from_json: bool = True,
            decode_from_yaml: bool = False,
            decode_from_base64: bool = True,
            allow_none: bool = True,
    ) -> Any:
        """
        Decodes an input value, optionally from Base64, JSON, or YAML.

        Args:
            k (str): The key for the input.
            default (Any | None): The default value if the key is not found.
            required (bool): Whether the input is required. Raises an error if required and not found.
            decode_from_json (bool): Whether to decode the input from JSON format.
            decode_from_yaml (bool): Whether to decode the input from YAML format.
            decode_from_base64 (bool): Whether to decode the input from Base64.
            allow_none (bool): Whether to allow None as a valid return value.

        Returns:
            Any: The decoded input, potentially converted or defaulted.
        """
        conf = self.get_input(k, default=default, required=required)

        if conf is None or conf == default:
            return conf

        if decode_from_base64:
            try:
                conf = base64_decode(
                    conf,
                    unwrap_raw_data=decode_from_json or decode_from_yaml,
                    encoding="json" if decode_from_json else "yaml"
                )
            except binascii.Error as exc:
                raise RuntimeError(f"Failed to decode {conf} from base64") from exc

        # Convert conf to str if it is memoryview, bytes, or bytearray
        if isinstance(conf, memoryview):
            conf = conf.tobytes().decode('utf-8')
        elif isinstance(conf, (bytes, bytearray)):
            try:
                conf = conf.decode('utf-8')
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"Failed to decode bytes to string: {conf}") from exc

        if decode_from_yaml:
            try:
                conf = decode_yaml(conf)
            except YAMLError as exc:
                raise RuntimeError(f"Failed to decode {conf} from YAML") from exc
        elif decode_from_json:
            try:
                conf = decode_json(conf)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Failed to decode {conf} from JSON") from exc

        if conf is None and not allow_none:
            return default

        return conf

    def freeze_inputs(self) -> CaseInsensitiveDict[str, Any]:
        """
        Freezes the current inputs, preventing further modifications until thawed.

        Returns:
            CaseInsensitiveDict: The frozen inputs.
        """
        if is_nothing(self.frozen_inputs):
            self.frozen_inputs = deepcopy(self.inputs)
            self.inputs = CaseInsensitiveDict()

        return self.frozen_inputs

    def thaw_inputs(self) -> CaseInsensitiveDict[str, Any]:
        """
        Thaws the inputs, merging the frozen inputs back into the current inputs.

        Returns:
            CaseInsensitiveDict: The thawed inputs.
        """
        if is_nothing(self.inputs):
            self.inputs = deepcopy(self.frozen_inputs)
            self.frozen_inputs = CaseInsensitiveDict()
            return self.inputs

        self.inputs = self.merger.merge(
            deepcopy(self.inputs), deepcopy(self.frozen_inputs)
        )
        self.frozen_inputs = CaseInsensitiveDict()
        return self.inputs

    def shift_inputs(self) -> CaseInsensitiveDict[str, Any]:
        """
        Shifts between frozen and thawed inputs.

        Returns:
            CaseInsensitiveDict: The resulting inputs after the shift.
        """
        if is_nothing(self.frozen_inputs):
            return self.freeze_inputs()

        return self.thaw_inputs()
