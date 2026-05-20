"""配置加载模块测试。"""

import os
import tempfile

import pytest
import yaml

from src.config.loader import ConfigLoader, _resolve_env_vars, _deep_merge
from src.config.schema import AppConfig


def test_resolve_env_vars():
    os.environ["TEST_VAR"] = "hello"
    result = _resolve_env_vars({"key": "${TEST_VAR}"})
    assert result["key"] == "hello"


def test_deep_merge_override():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}}
    result = _deep_merge(base, override)
    assert result["a"] == 1
    assert result["b"]["c"] == 99
    assert result["b"]["d"] == 3


def test_config_loads_with_defaults():
    config = ConfigLoader.load("./config")
    assert isinstance(config, AppConfig)
    assert config.shop_id == "shop_001"
    assert config.llm.model == "M2.7"
    assert config.screenshot.interval == 1.5
