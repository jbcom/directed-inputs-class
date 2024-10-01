"""Module containing decorators for automatic input processing in DirectedInputsClass.

This module defines the auto_directed_inputs decorator, which dynamically creates
Pydantic models from method attributes to validate and parse inputs. It leverages
Pydantic's InitSettingsSource along with DirectedInputsSettings to ensure robust
and flexible input handling from multiple sources, with customization options per function.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Callable, Any, Type, get_type_hints, Union

from pydantic import BaseModel, create_model, ValidationError
from pydantic_settings import InitSettingsSource, PydanticBaseSettingsSource
from inputs import DirectedInputsSettings, StdinSettingsSource
from decoding_types import (
    JSONDecoded, YAMLDecoded, Base64Decoded,
    JSONAndBase64Decoded, YAMLAndBase64Decoded,
    JSONWithoutBase64Decoded, YAMLWithoutBase64Decoded
)


def create_dynamic_model(func: Callable) -> Type[BaseModel]:
    """Creates a dynamic Pydantic model from a function's parameters.

    This function dynamically generates a Pydantic model based on the function's
    parameter annotations, allowing for validation and parsing of inputs
    directly from the method's attributes.

    Args:
        func (Callable): The function to generate the model from.

    Returns:
        Type[BaseModel]: A Pydantic model class matching the function's parameters.
    """
    parameters = inspect.signature(func).parameters
    fields = {}
    type_hints = get_type_hints(func)

    for name, param in parameters.items():
        if name == 'self':  # Skip 'self' for instance methods
            continue

        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            # Skip variadic arguments (*args, **kwargs)
            continue

        annotation = type_hints.get(name, Any)  # Use Any if no type hint is provided
        default = param.default if param.default is not param.empty else ...
        fields[name] = (annotation, default)

    # Create a Pydantic model dynamically with the extracted fields
    return create_model(f"{func.__name__.capitalize()}Model", **fields)


def auto_directed_inputs(
        from_environment: bool | None = None,
        from_stdin: bool | None = None,
) -> Callable:
    """Decorator to automatically process directed inputs for method arguments using Pydantic models.

    This decorator inspects the function's parameters and dynamically creates
    a Pydantic model to validate and parse inputs. It leverages DirectedInputsSettings
    to fetch inputs from prioritized sources: environment variables, stdin, and init settings.
    If `from_environment` or `from_stdin` are not provided, it uses the default values from
    DirectedInputsClass.

    Args:
        from_environment (bool | None): Whether to load inputs from environment variables.
                                        Falls back to DirectedInputsClass default if None.
        from_stdin (bool | None): Whether to load inputs from stdin.
                                  Falls back to DirectedInputsClass default if None.

    Returns:
        Callable: The decorator that wraps a function with automatic directed input processing.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Use defaults from DirectedInputsClass if not explicitly overridden
            default_from_environment = getattr(self, 'from_environment', True)
            default_from_stdin = getattr(self, 'from_stdin', False)

            effective_from_environment = from_environment if from_environment is not None else default_from_environment
            effective_from_stdin = from_stdin if from_stdin is not None else default_from_stdin

            # Create the dynamic Pydantic model from the function's parameters
            DynamicModel = create_dynamic_model(func)

            # Initialize InitSettingsSource with the function's provided arguments (kwargs)
            init_settings = InitSettingsSource(DynamicModel, kwargs)

            # Create an instance of DirectedInputsSettings with custom sources prioritized
            settings = DirectedInputsSettings(
                from_environment=effective_from_environment,
                from_stdin=effective_from_stdin
            )

            # Get the customized sources based on DirectedInputsSettings
            sources = settings.settings_customise_sources(
                DynamicModel, init_settings, env_settings=settings.env_settings,
                dotenv_settings=settings.dotenv_settings, file_secret_settings=settings.file_secret_settings
            )

            # Combine all settings sources into one dictionary
            combined_settings = {}
            for source in sources:
                combined_settings.update(source())

            # Parse the combined settings into the dynamic model
            try:
                validated_inputs = DynamicModel(**combined_settings)
            except ValidationError as e:
                raise RuntimeError(f"Input validation error: {e}")

            # Pass validated inputs as arguments to the function
            bound_args = inspect.signature(func).bind(self, *args, **validated_inputs.dict())

            # Use decode_input for all inputs, passing through to get_input when no decoding is needed
            for name, param in bound_args.arguments.items():
                if name == 'self':
                    continue

                # Skip handling variadic args and kwargs
                if name in ('args', 'kwargs'):
                    continue

                annotation = get_type_hints(func).get(name, Any)
                # Only pass decode_type if it matches one of the custom decoding types
                decode_type = annotation if issubclass(annotation, (
                    JSONDecoded, YAMLDecoded, Base64Decoded,
                    JSONAndBase64Decoded, YAMLAndBase64Decoded,
                    JSONWithoutBase64Decoded, YAMLWithoutBase64Decoded
                )) else None

                # Update the argument with the decoded or fetched input
                bound_args.arguments[name] = self.decode_input(
                    key=name,
                    default=param,
                    required=param is not None,
                    decode_type=decode_type
                )

            return func(*bound_args.args, **bound_args.kwargs)

        return wrapper

    return decorator
