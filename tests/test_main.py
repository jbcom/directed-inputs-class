from __future__ import annotations

import json
import os
from extended_data_types import base64_encode
import pytest
from directed_inputs_class.__main__ import DirectedInputsClass


@pytest.fixture
def env_setup(monkeypatch):
    """Fixture to set up environment variables."""
    monkeypatch.setenv("TEST_ENV_VAR", "test_value")
    monkeypatch.setenv("OVERRIDE_STDIN", "False")


@pytest.fixture
def stdin_setup(monkeypatch):
    """Fixture to set up stdin."""
    monkeypatch.setattr("sys.stdin", open(os.devnull, 'w'))


def test_init_with_env_vars(env_setup):
    dic = DirectedInputsClass()
    assert dic.inputs["TEST_ENV_VAR"] == "test_value"


def test_init_with_stdin(monkeypatch, env_setup):
    input_data = json.dumps({"stdin_key": "stdin_value"})
    monkeypatch.setattr("sys.stdin.read", lambda: input_data)

    dic = DirectedInputsClass(from_stdin=True)
    assert dic.inputs["stdin_key"] == "stdin_value"


def test_get_input_with_default():
    dic = DirectedInputsClass(inputs={"key1": "value1"})
    assert dic.get_input("key1", default="default_value") == "value1"
    assert dic.get_input("key2", default="default_value") == "default_value"


def test_get_input_required():
    dic = DirectedInputsClass(inputs={"key1": "value1"})
    with pytest.raises(RuntimeError, match="Required input key2 not passed"):
        dic.get_input("key2", required=True)


def test_get_input_boolean():
    dic = DirectedInputsClass(inputs={"bool_key": "true"})
    assert dic.get_input("bool_key", is_bool=True) is True


def test_get_input_integer():
    dic = DirectedInputsClass(inputs={"int_key": "10"})
    assert dic.get_input("int_key", is_integer=True) == 10


def test_decode_input_json():
    dic = DirectedInputsClass(inputs={"json_key": '{"name": "test"}'})
    decoded = dic.decode_input("json_key", decode_from_json=True, decode_from_base64=False)
    assert decoded == {"name": "test"}


def test_decode_input_yaml():
    dic = DirectedInputsClass(inputs={"yaml_key": "name: test"})
    decoded = dic.decode_input("yaml_key", decode_from_yaml=True, decode_from_base64=False)
    assert decoded == {"name": "test"}


def test_decode_input_base64():
    encoded_value = base64_encode(json.dumps({"name": "test"}).encode())
    dic = DirectedInputsClass(inputs={"base64_key": encoded_value})
    decoded = dic.decode_input("base64_key", decode_from_base64=True, decode_from_json=True)
    assert decoded == {"name": "test"}


def test_freeze_inputs():
    dic = DirectedInputsClass(inputs={"key1": "value1"})
    frozen_inputs = dic.freeze_inputs()
    assert frozen_inputs["key1"] == "value1"
    assert dic.inputs == {}


def test_thaw_inputs():
    dic = DirectedInputsClass(inputs={"key1": "value1"})
    dic.freeze_inputs()
    dic.thaw_inputs()
    assert dic.inputs["key1"] == "value1"
    assert dic.frozen_inputs == {}


def test_shift_inputs():
    dic = DirectedInputsClass(inputs={"key1": "value1"})
    dic.shift_inputs()
    assert dic.inputs == {}
    assert dic.frozen_inputs["key1"] == "value1"

    dic.shift_inputs()
    assert dic.inputs["key1"] == "value1"
    assert dic.frozen_inputs == {}
