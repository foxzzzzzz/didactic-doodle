"""YAML 配置加载器。

支持：
- 合并多个 YAML 文件（主配置 + 坐标配置）
- ${ENV_VAR} 环境变量替换
- 本地覆盖文件（*.local.yaml）自动叠加
"""

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml

from .schema import (
    ActionConfig,
    AppConfig,
    ContextConfig,
    Coordinates,
    KnowledgeBaseConfig,
    LLMConfig,
    LoggingConfig,
    MonitoringConfig,
    OcrConfig,
    OperatorConfig,
    ScreenshotConfig,
    TemplateMatchingConfig,
)
from ..utils.exceptions import ConfigError


_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: Any) -> Any:
    """递归替换字符串中的 ${VAR} 为环境变量值。"""
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")
        return _ENV_VAR_RE.sub(repl, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _load_yaml(path: Path) -> Dict:
    """加载单个 YAML 文件，返回字典。文件不存在则返回空字典。"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典，override 覆盖 base。"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _build_coordinates(raw: Dict) -> Coordinates:
    """从原始配置字典构建 Coordinates 对象。"""
    w = raw.get("window", {})
    chat = raw.get("chat_area", {})
    inp = raw.get("input_box", {})
    send = raw.get("send_button", {})
    send_center = raw.get("send_button_center", {})
    inp_center = raw.get("input_box_center", {})
    tmpl = raw.get("templates", {})

    return Coordinates(
        offset_x=w.get("offset_x", 0),
        offset_y=w.get("offset_y", 0),
        chat_area=(
            chat.get("x", 380), chat.get("y", 120),
            chat.get("width", 820), chat.get("height", 580),
        ),
        input_box=(
            inp.get("x", 380), inp.get("y", 720),
            inp.get("width", 760), inp.get("height", 80),
        ),
        send_button=(
            send.get("x", 1140), send.get("y", 720),
            send.get("width", 60), send.get("height", 80),
        ),
        send_button_center=(send_center.get("x", 1170), send_center.get("y", 760)),
        input_box_center=(inp_center.get("x", 760), inp_center.get("y", 760)),
        templates_dir=tmpl.get("directory", "./docs/templates"),
        template_send_button=tmpl.get("send_button", "send_button.png"),
        template_input_box=tmpl.get("input_box", "input_box.png"),
        template_unread_badge=tmpl.get("unread_badge", "unread_badge.png"),
    )


class ConfigLoader:
    """配置加载器。

    加载顺序（后者覆盖前者）：
    1. default.yaml （基础配置）
    2. coordinates.yaml （坐标配置）
    3. *.local.yaml （本地覆盖，gitignored）
    """

    @staticmethod
    def load(config_dir: str = "./config") -> AppConfig:
        """加载所有配置并返回 AppConfig 实例。

        Args:
            config_dir: 配置文件目录路径。

        Returns:
            AppConfig 实例。

        Raises:
            ConfigError: 配置文件不存在或格式错误。
        """
        base = Path(config_dir)

        if not base.exists():
            raise ConfigError(f"配置目录不存在: {config_dir}")

        # 加载 main config
        config = _load_yaml(base / "default.yaml")
        if not config:
            raise ConfigError(f"主配置文件为空或不存在: {base / 'default.yaml'}")

        # 合并坐标配置
        coords = _load_yaml(base / "coordinates.yaml")
        config = _deep_merge(config, coords)

        # 合并本地覆盖
        local = _load_yaml(base / "coordinates.local.yaml")
        config = _deep_merge(config, local)

        # 环境变量替换
        config = _resolve_env_vars(config)

        # 构建数据对象
        app = config.get("app", {})
        llm = config.get("llm", {})
        screenshot = config.get("screenshot", {})
        ocr = config.get("ocr", {})
        tm = config.get("template_matching", {})
        kb = config.get("knowledge_base", {})
        ctx = config.get("context", {})
        action = config.get("action", {})
        operator = config.get("operator", {})
        logging_cfg = config.get("logging", {})
        monitoring = config.get("monitoring", {})

        return AppConfig(
            shop_id=app.get("shop_id", "shop_001"),
            screenshot=ScreenshotConfig(
                interval=screenshot.get("interval", 1.5),
                save_debug=screenshot.get("save_debug", False),
                debug_dir=screenshot.get("debug_dir", "./data/screenshots"),
            ),
            ocr=OcrConfig(
                confidence_threshold=ocr.get("confidence_threshold", 0.7),
                use_gpu=ocr.get("use_gpu", False),
            ),
            template_matching=TemplateMatchingConfig(
                threshold=tm.get("threshold", 0.8),
            ),
            llm=LLMConfig(
                provider=llm.get("provider", "minimax"),
                api_key=llm.get("api_key", ""),
                model=llm.get("model", "M2.7"),
                base_url=llm.get("base_url", "https://api.minimax.chat/v1"),
                timeout=llm.get("timeout", 15),
                max_retries=llm.get("max_retries", 3),
                temperature=llm.get("temperature", 0.7),
                max_output_tokens=llm.get("max_output_tokens", 500),
            ),
            knowledge_base=KnowledgeBaseConfig(
                base_path=kb.get("base_path", "./knowledge_base"),
                max_chars=kb.get("max_chars", 3000),
            ),
            context=ContextConfig(
                max_history_rounds=ctx.get("max_history_rounds", 20),
                retention_days=ctx.get("retention_days", 3),
                session_idle_minutes=ctx.get("session_idle_minutes", 30),
            ),
            action=ActionConfig(
                type_delay=action.get("type_delay", 0.05),
                click_delay=action.get("click_delay", 0.3),
                random_delay_range=action.get("random_delay_range", [0.5, 1.5]),
            ),
            operator=OperatorConfig(
                debug_mode=operator.get("debug_mode", False),
                demo_mode=operator.get("demo_mode", False),
            ),
            logging=LoggingConfig(
                level=logging_cfg.get("level", "INFO"),
                file=logging_cfg.get("file", "./data/logs/pdd_cs.log"),
                max_size_mb=logging_cfg.get("max_size_mb", 10),
                backup_count=logging_cfg.get("backup_count", 5),
            ),
            monitoring=MonitoringConfig(
                health_check_interval=monitoring.get("health_check_interval", 60),
                target_process=monitoring.get("target_process", "拼多多商家工作台.exe"),
            ),
            coordinates=_build_coordinates(config),
        )
