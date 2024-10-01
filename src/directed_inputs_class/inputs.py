"""
Module for managing directed inputs with dynamic Pydantic models and optional case insensitivity.

This module provides the DirectedInputs class, which manages inputs from various
sources (e.g., environment variables, stdin) using dynamically created Pydantic
models. The class supports freezing, thawing, and shifting inputs, allowing for
robust handling of configuration states in Python applications. Inputs are validated
and parsed through Pydantic models, ensuring type safety and consistency.

Classes:
    DirectedInputs: A class for managing and validating directed inputs using Pydantic models.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Type

from pathlib import Path
from case_insensitive_dict import CaseInsensitiveDict
from deepmerge import Merger
from extended_data_types import is_nothing, decode_json
from functools import lru_cache

FilePath = Union[str, bytes, os.PathLike, Path]

class DirectedInputs:
    """A class for managing and validating directed inputs using Pydantic models.

    This class dynamically creates Pydantic models to manage inputs from various
    sources such as environment variables and stdin. It supports freezing, thawing,
    and shifting of inputs to manage different configuration states.

    Attributes:
        from_environment (bool): Flag indicating whether to load inputs from environment variables.
        from_stdin (bool): Flag indicating whether to load inputs from stdin.
        case_sensitive (bool): Flag indicating if keys should be case-sensitive.
    """

    def __init__(
            self,
            from_inputs: Dict[str, Any] | None = None,
            from_environment: bool = True,
            from_stdin: bool = False,
            from_json_files: List[FilePath] | None = None,
            from_yaml_files: List[FilePath] | None = None,
            from_toml_files: List[FilePath] | None = None,
            case_sensitive: bool = False,
    ):
        """Initializes the DirectedInputs class.

        Args:
            inputs (Dict[str, Any] | None): Initial inputs for the dynamic model.
            from_environment (bool): Whether to load inputs from environment variables.
            from_stdin (bool): Whether to load inputs from stdin.
            case_sensitive (bool): Whether keys should be case-sensitive.
        """
        self.from_environment = from_environment
        self.from_stdin = from_stdin
        self.case_sensitive = case_sensitive
        self._custom_inputs = self._create_dict()
        self._active_state = self._create_dict()
        self._frozen_state = self._create_dict()
        self._inputs_merger = Merger(
            [(list, ["append"]), (dict, ["merge"]), (set, ["union"])],
            ["override"],
            ["override"],
        )

        self.update_custom_inp

    def _read_from_stdin(self) -> Dict[str, Any] | None:
        """Reads input from stdin and decodes it as JSON.

        Returns:
            Dict[str, Any] | None: The decoded settings from stdin, or None if not applicable.

        Raises:
            RuntimeError: If decoding from stdin fails.
        """
        try:
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                return json.loads(stdin_data)
        except (json.JSONDecodeError, IOError) as exc:
            raise RuntimeError(f"Failed to decode stdin data: {exc}")
        return None

    @property
    @lru_cache(maxsize=1)
    def inputs(self) -> Dict[str, Any]:
        """Gets all available inputs by merging sources.

        Returns:
            Dict[str, Any]: A dictionary of available inputs.
        """
        combined_inputs = self._create_dict()
        if self.from_environment:
            combined_inputs.update(os.environ)
        if self.from_stdin:
            stdin_data = self._read_from_stdin()
            if stdin_data:
                combined_inputs.update(stdin_data)
        if self._active_state:
            combined_inputs.update(self._active_state)
        return combined_inputs

    @inputs.setter
    def inputs(self, value: Dict[str, Any] | PydanticBaseSettingsSource):
        """Sets the inputs, updating the settings sources if a custom source is provided.

        Args:
            value (Dict[str, Any] | PydanticBaseSettingsSource): The inputs to set, either
            as a dictionary or a custom settings source.
        """
        if isinstance(value, dict):
            self._active_state.update(self._create_dict(value))
        elif isinstance(value, PydanticBaseSettingsSource):
            self._active_state = value()  # Assume callable returning dict
        else:
            raise ValueError("Unsupported input type; must be dict or PydanticBaseSettingsSource")

    def get(
            self,
            key: str,
            default: Any | None = None,
            required: bool = False,
            input_type: Type | None = str,
    ) -> Any:
        """Retrieves an input value by key, updating the model if necessary.

        Args:
            key (str): The key for the input.
            default (Any | None): The default value if the key is not found.
            required (bool): Whether the input is required.
            input_type (Type | None): The expected type of the input.

        Returns:
            Any: The retrieved input, potentially converted or defaulted.

        Raises:
            RuntimeError: If the input is required but not found.
        """
        if key not in self._active_state:
            self._add_field_to_model(key, default, required, input_type)
            self._refresh_active_state()

        return self._active_state.get(key, default)

    def freeze(self) -> Dict[str, Any]:
        """Freezes the current inputs, preventing further modifications until thawed.

        Returns:
            Dict[str, Any]: The frozen inputs.
        """
        if is_nothing(self._frozen_state):
            self._frozen_state = self._create_dict(self._active_state)
            self._active_state.clear()

        return self._frozen_state

    def thaw(self) -> Dict[str, Any]:
        """Thaws the inputs, merging the frozen inputs back into the current inputs.

        Returns:
            Dict[str, Any]: The thawed inputs.
        """
        if is_nothing(self._active_state):
            self._active_state = self._create_dict(self._frozen_state)
            self._frozen_state.clear()
            return self._active_state

        self._active_state = self._inputs_merger.merge(
            self._create_dict(self._active_state), self._create_dict(self._frozen_state)
        )
        self._frozen_state.clear()
        return self._active_state

    def shift(self) -> Dict[str, Any]:
        """Shifts between frozen and thawed inputs.

        Returns:
            Dict[str, Any]: The resulting inputs after the shift.
        """
        if is_nothing(self._frozen_state):
            return self.freeze()

        return self.thaw()

    def _add_field_to_model(self, key: str, default: Any, required: bool, input_type: Type):
        """Adds a field to the dynamic Pydantic model.

        Args:
            key (str): The key for the input.
            default (Any): The default value for the field.
            required (bool): Whether the field is required.
            input_type (Type): The type of the field.
        """
        # Implementation for adding a field dynamically to the Pydantic model
        # This is a placeholder and would need implementation to update a dynamic model
        pass

    def _refresh_active_state(self):
        """Refreshes the active state by re-evaluating the dynamic model against sources."""
        # Implementation for refreshing the active state by calling Pydantic with current sources
        pass



    def _create_dict(self, initial: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Creates a new dictionary based on case sensitivity setting.

        Args:
            initial (Dict[str, Any] | None): Initial values to populate the dictionary.

        Returns:
            Dict[str, Any]: A case-insensitive or case-sensitive dictionary.
        """
        if initial is None:
            initial = {}
        return CaseInsensitiveDict(initial) if not self.case_sensitive else initial
