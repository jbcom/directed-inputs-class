"""Module implementing DirectedInputsClass using Pydantic for input handling.

This module defines the DirectedInputsClass, which manages directed inputs from
various sources, leveraging Pydantic settings for robust validation and parsing.
It supports dynamic merging, freezing, and thawing of inputs, and includes methods
for decoding inputs from JSON, YAML, and Base64 formats.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from deepmerge import Merger  # type: ignore[import-untyped]
from inputs import DirectedInputsSettings
from extended_data_types import is_nothing, base64_decode, decode_json, decode_yaml
from yaml import YAMLError


class DirectedInputsClass:
    """A class to manage and process directed inputs using Pydantic settings.

    This class handles inputs from environment variables, stdin, and provided dictionaries,
    utilizing Pydantic for input validation and parsing.

    Attributes:
        settings (DirectedInputsSettings): The Pydantic settings object managing inputs.
        _inputs (Dict[str, Any]): Dictionary to store current inputs.
        _frozen_inputs (Dict[str, Any]): Dictionary to store frozen inputs.
        _inputs_merger (Merger): Object to manage deep merging of dictionaries.
    """

    def __init__(self, inputs: Dict[str, Any] | None = None):
        """Initializes the DirectedInputsClass with the provided inputs.

        Args:
            inputs (Dict[str, Any] | None): Initial inputs to be processed.
        """
        self.settings = DirectedInputsSettings(**(inputs or {}))
        self._inputs = self.settings.dict()
        self._frozen_inputs = {}
        self._inputs_merger = Merger(
            [(list, ["append"]), (dict, ["merge"]), (set, ["union"])],
            ["override"],
            ["override"],
        )



    def freeze_inputs(self) -> Dict[str, Any]:
        """Freezes the current inputs, preventing further modifications until thawed.

        Returns:
            Dict[str, Any]: The frozen inputs.
        """
        if is_nothing(self._frozen_inputs):
            self._frozen_inputs = deepcopy(self._inputs)
            self._inputs = {}

        return self._frozen_inputs

    def thaw_inputs(self) -> Dict[str, Any]:
        """Thaws the inputs, merging the frozen inputs back into the current inputs.

        Returns:
            Dict[str, Any]: The thawed inputs.
        """
        if is_nothing(self._inputs):
            self._inputs = deepcopy(self._frozen_inputs)
            self._frozen_inputs = {}
            return self._inputs

        self._inputs = self._inputs_merger.merge(
            deepcopy(self._inputs), deepcopy(self._frozen_inputs)
        )
        self._frozen_inputs = {}
        return self._inputs

    def shift_inputs(self) -> Dict[str, Any]:
        """Shifts between frozen and thawed inputs.

        Returns:
            Dict[str, Any]: The resulting inputs after the shift.
        """
        if is_nothing(self._frozen_inputs):
            return self.freeze_inputs()

        return self.thaw_inputs()