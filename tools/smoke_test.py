"""冒烟测试 — 验证项目在基本层面可正常运行。

不依赖外部服务（LLM API、拼多多商家工作台），仅验证：
- 配置文件可加载，字段完整
- 所有模块可正常导入
- 日志系统无格式错误
- 数据库可建表、读写

用法: python tools/smoke_test.py
"""

import os
import sys
import tempfile
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _h1(text: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {text}")
    print("=" * 50)


def _ok(text: str) -> None:
    print(f"  [OK] {text}")


def _fail(text: str) -> None:
    print(f"  [FAIL] {text}")


def test_config_loading() -> int:
    """验证配置加载。"""
    _h1("1. 配置加载")

    from src.config.loader import ConfigLoader
    from src.config.schema import AppConfig

    config = ConfigLoader.load("./config")

    assert isinstance(config, AppConfig), f"类型错误: {type(config)}"
    assert config.name, "name 为空"
    assert config.version, "version 为空"
    assert config.phase >= 1, f"phase 异常: {config.phase}"
    assert config.shop_id, "shop_id 为空"
    assert config.llm.provider, "llm.provider 为空"
    assert config.llm.model, "llm.model 为空"
    assert config.ocr.confidence_threshold > 0, "ocr.confidence_threshold <= 0"
    assert config.coordinates.chat_area[2] > 0, "chat_area width <= 0"
    assert config.logging.file, "logging.file 为空"

    _ok(f"配置加载成功: {config.name} v{config.version} Phase {config.phase}")
    _ok(f"  shop_id={config.shop_id}, llm={config.llm.provider}/{config.llm.model}")
    return 0


def test_imports() -> int:
    """验证所有核心模块可导入。"""
    _h1("2. 模块导入")

    modules = [
        ("src.config.loader", "ConfigLoader"),
        ("src.config.schema", "AppConfig"),
        ("src.vision.screenshot", "ScreenCapture"),
        ("src.vision.ocr", "OcrEngine"),
        ("src.llm.client", "MiniMaxClient"),
        ("src.knowledge.loader", "KnowledgeBase"),
        ("src.action.operator", "UIOperator"),
        ("src.memory.database", "Database"),
        ("src.memory.context", "SessionContext"),
        ("src.scheduler.orchestrator", "Phase1Orchestrator"),
        ("src.utils.logger", "setup_logger"),
        ("src.utils.exceptions", "PddCSException"),
    ]

    for mod_name, cls_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            getattr(mod, cls_name)
            _ok(f"{mod_name}.{cls_name}")
        except Exception as e:
            _fail(f"{mod_name}.{cls_name}: {e}")
            return 1

    # 验证 TypeActionError 已重命名，TypeError 不再存在
    from src.utils import exceptions
    assert not hasattr(exceptions, "TypeError"), \
        "exceptions.TypeError 应已重命名为 TypeActionError"
    assert hasattr(exceptions, "TypeActionError"), \
        "exceptions.TypeActionError 缺失"
    _ok("TypeActionError 重命名确认无误")

    return 0


def test_logging() -> int:
    """验证日志系统无格式错误。"""
    _h1("3. 日志系统")

    from src.utils.logger import setup_logger

    with tempfile.TemporaryDirectory() as tmp:
        log_file = str(Path(tmp) / "test.log")
        logger = setup_logger(
            level="DEBUG",
            log_file=log_file,
            max_bytes=10 * 1024 * 1024,
            backup_count=2,
        )

        # 测试各种格式组合 — 之前 %d 配合 str 的 bug 会在这里暴露
        logger.info("测试整型: %d", 42)
        logger.info("测试字符串: %s", "hello")
        logger.info("测试浮点: %.2f", 3.14)
        logger.info("测试多参数: %s %d %s", "id", 1, "ok")
        logger.warning("测试警告: %s", "warning message")
        logger.debug("测试调试: %s", "debug message")

        # 验证日志文件已写入
        assert Path(log_file).exists(), "日志文件未创建"
        content = Path(log_file).read_text(encoding="utf-8")
        assert "测试整型: 42" in content
        assert "测试字符串: hello" in content
        _ok(f"日志写入正常 ({len(content)} bytes)")

        # 关闭 handler 释放文件句柄，避免 Windows 清理报错
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    return 0


def test_database() -> int:
    """验证数据库建表和基本读写。"""
    _h1("4. 数据库")

    from src.memory.database import Database, ConversationRecord

    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "test.db")
        db = Database(db_path)
        db.init_db()

        # 写入
        record = ConversationRecord(
            shop_id="test_shop",
            customer_id="test_customer",
            session_id="test_shop_test_customer",
            customer_msg="你好",
            reply="亲，您好！",
            tag="",
        )
        rid = db.save_conversation(record)
        assert rid > 0, f"插入失败: {rid}"
        _ok(f"写入记录 id={rid}")

        # 查询
        history = db.get_history("test_shop_test_customer", limit=10, retention_days=7)
        assert len(history) == 1, f"查询结果数异常: {len(history)}"
        assert history[0].customer_msg == "你好"
        assert history[0].reply == "亲，您好！"
        _ok("查询记录正常")

        db.close()
        _ok("数据库关闭正常")

    return 0


def test_config_schema_consistency() -> int:
    """验证 YAML 中定义的字段都在 AppConfig 中存在对应。"""
    _h1("5. Config 一致性")

    import yaml
    from src.config.schema import AppConfig

    config_path = Path("./config/default.yaml")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    # 检查顶层 keys 与 AppConfig dataclass fields 对应
    from dataclasses import fields
    schema_fields = {f.name for f in fields(AppConfig)}

    # AppConfig 下的一级子配置名
    raw_keys = set(raw.keys())
    raw_keys.discard("app")  # app 的字段平铺到 AppConfig

    # 检查 app 下的字段
    app_raw = raw.get("app", {})
    app_field_names = {"name", "version", "phase", "shop_id"}
    missing_in_schema = app_field_names - schema_fields
    if missing_in_schema:
        _fail(f"YAML app 字段在 AppConfig 中缺失: {missing_in_schema}")
        return 1
    else:
        _ok(f"app 段 {len(app_raw)} 个字段均映射到 AppConfig")

    # 检查子配置与 schema 的对应
    sub_config_map = {
        "screenshot": "screenshot",
        "ocr": "ocr",
        "template_matching": "template_matching",
        "llm": "llm",
        "knowledge_base": "knowledge_base",
        "context": "context",
        "action": "action",
        "operator": "operator",
        "logging": "logging",
        "monitoring": "monitoring",
    }
    for yaml_key, schema_key in sub_config_map.items():
        if yaml_key in raw_keys:
            if schema_key in schema_fields:
                _ok(f"  {yaml_key} -> AppConfig.{schema_key}")
            else:
                _fail(f"  {yaml_key} 在 AppConfig 中找不到字段 {schema_key}")
                return 1

    return 0


def main() -> int:
    print("=" * 50)
    print("  冒烟测试 — 验证项目基本运行能力")
    print("=" * 50)

    failures = 0
    for test_fn in [
        test_config_loading,
        test_imports,
        test_logging,
        test_database,
        test_config_schema_consistency,
    ]:
        try:
            failures += test_fn()
        except Exception as e:
            _fail(f"测试抛出异常: {e}")
            import traceback
            traceback.print_exc()
            failures += 1

    print()
    print("=" * 50)
    if failures == 0:
        print("  全部通过！")
        print("=" * 50)
        return 0
    else:
        print(f"  {failures} 项失败！")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
