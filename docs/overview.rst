Overview
--------

The Directed Inputs Class library provides a robust and flexible interface for managing inputs from various sources in Python applications, leveraging Pydantic's powerful settings management capabilities. It simplifies the process of working with inputs from environment variables, stdin, and customizable sources, while offering advanced features such as input freezing, thawing, and decoding from multiple formats.

Key Features
------------

- **Environment Variable Integration**: Automatically integrates environment variables into your inputs, allowing for seamless configuration management.
- **Stdin Input Handling**: Supports reading and merging inputs from stdin, with options to override default behaviors using environment flags.
- **Customizable Settings Sources**: Customize the priority and types of input sources via Pydantic's `settings_customise_sources` method, allowing for flexible configuration tailored to your application's needs.
- **Input Freezing and Thawing**: Freeze inputs to prevent further modifications and thaw them when needed, ensuring consistent input management.
- **Advanced Decoding Utilities**: Decode inputs from Base64, JSON, and YAML formats with built-in error handling and customization options.
- **Type Conversion**: Convert inputs to boolean, integer, or float types, with robust error handling for invalid inputs.

Usage Examples
--------------

Below are some examples demonstrating how to use the Directed Inputs Class library:

### Initializing the Class with Environment Variables

.. code-block:: python

    from directed_inputs_class import DirectedInputsClass

    dic = DirectedInputsClass()
    print(dic.get_input("MY_ENV_VAR"))  # Accessing an environment variable

### Reading Inputs from Stdin

.. code-block:: python

    import sys
    from directed_inputs_class import DirectedInputsClass

    sys.stdin.write('{"stdin_key": "stdin_value"}')
    dic = DirectedInputsClass(inputs={}, from_stdin=True)
    print(dic.get_input("stdin_key"))  # Output: stdin_value

### Customizing Settings Sources

.. code-block:: python

    from inputs import DirectedInputsSettings
    from pydantic_settings import PydanticBaseSettingsSource

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
            # Custom source priority: environment first, then stdin
            return env_settings, StdinSettingsSource(settings_cls), init_settings

    settings = CustomSettings()
    print(settings.dict())  # Prints settings with custom source order

### Freezing and Thawing Inputs

.. code-block:: python

    from directed_inputs_class import DirectedInputsClass

    dic = DirectedInputsClass(inputs={"key1": "value1"})
    frozen = dic.freeze_inputs()
    print(frozen)  # Outputs: {'key1': 'value1'}

    thawed = dic.thaw_inputs()
    print(thawed)  # Outputs: {'key1': 'value1'}

### Decoding Base64 Inputs

.. code-block:: python

    from directed_inputs_class import DirectedInputsClass

    encoded_value = "eyJuYW1lIjogIkpvaG4ifQ=="  # Base64 encoded JSON {"name": "John"}
    dic = DirectedInputsClass(inputs={"base64_key": encoded_value})
    decoded = dic.decode_input("base64_key", decode_from_base64=True)
    print(decoded)  # Output: {'name': 'John'}

### Boolean, Integer, and Float Conversion

.. code-block:: python

    from directed_inputs_class import DirectedInputsClass

    dic = DirectedInputsClass(inputs={"bool_key": "true", "int_key": "42", "float_key": "3.14"})
    bool_value = dic.get_input("bool_key", is_bool=True)
    int_value = dic.get_input("int_key", is_integer=True)
    float_value = dic.get_input("float_key", is_float=True)
    print(bool_value)  # Output: True
    print(int_value)   # Output: 42
    print(float_value) # Output: 3.14
