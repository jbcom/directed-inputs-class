"""Module defining custom types for decoding inputs in DirectedInputsClass.

This module provides custom type annotations to specify decoding and parsing
requirements for inputs, such as decoding with YAML, JSON, Base64, or combinations
thereof.
"""

from typing import Type, TypeVar

# Type variable for flexibility in generics
T = TypeVar('T')


# Standalone types for decoding with specific formats
class JSONDecoded(str):
    """Type annotation for inputs that should be decoded from JSON."""
    pass


class YAMLDecoded(str):
    """Type annotation for inputs that should be decoded from YAML."""
    pass


class Base64Decoded(str):
    """Type annotation for inputs that should be decoded from Base64."""
    pass


# Combined types for decoding with multiple formats
class JSONAndBase64Decoded(str):
    """Type annotation for inputs that should be decoded from JSON and Base64."""
    pass


class YAMLAndBase64Decoded(str):
    """Type annotation for inputs that should be decoded from YAML and Base64."""
    pass


class JSONWithoutBase64Decoded(str):
    """Type annotation for inputs that should be decoded from JSON without Base64."""
    pass


class YAMLWithoutBase64Decoded(str):
    """Type annotation for inputs that should be decoded from YAML without Base64."""
    pass
