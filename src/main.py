"""拼多多智能客服系统 — Phase 1 程序入口。

单店铺单会话全自动回复。
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.loader import ConfigLoader
from src.vision.screenshot import ScreenCapture
from src.vision.ocr import OcrEngine
from src.llm.client import MiniMaxClient
from src.knowledge.loader import KnowledgeBase
from src.action.operator import UIOperator
from src.memory.database import Database
from src.memory.context import SessionContext
from src.scheduler.orchestrator import Phase1Orchestrator
from src.utils.logger import setup_logger


def main() -> None:
    """程序入口：初始化所有模块 → 启动 Phase 1 主循环。"""

    # 1. 加载配置
    config = ConfigLoader.load("./config")

    print("=" * 50)
    print(f"  {config.name} v{config.version} (Phase {config.phase})")
    print("=" * 50)
    print()

    # 检查 API Key
    if not config.llm.api_key and not config.operator.demo_mode:
        print("[ERROR] 未配置 LLM API Key")
        print("  请在 config/default.yaml 的 llm.api_key 字段中填入密钥")
        print("  或启用 operator.demo_mode=true 进入演示模式")
        sys.exit(1)

    # 2. 初始化日志
    logger = setup_logger(
        level=config.logging.level,
        log_file=config.logging.file,
        max_bytes=config.logging.max_size_mb * 1024 * 1024,
        backup_count=config.logging.backup_count,
    )

    # 3. 初始化各模块
    print("初始化各模块...")
    capture = ScreenCapture(config.coordinates)
    ocr_engine = OcrEngine(config.ocr)
    llm_client = MiniMaxClient(config.llm)
    operator = UIOperator(config.action, config.coordinates)
    kb = KnowledgeBase(config.knowledge_base.base_path)
    db = Database()
    db.init_db()
    ctx = SessionContext(db, config.context.max_history_rounds)

    print(f"  店铺: {config.name} ({config.shop_id})")
    print(f"  LLM: {config.llm.provider}/{config.llm.model}")
    print(f"  模式: {'演示模式' if config.operator.demo_mode else '正常模式'}")
    if config.operator.debug_mode:
        print("  DEBUG 模式已启用（不会执行实际操作）")
    print()

    # 4. 启动调度器
    orchestrator = Phase1Orchestrator(
        config=config,
        capture=capture,
        ocr=ocr_engine,
        llm=llm_client,
        operator=operator,
        kb=kb,
        db=db,
        ctx=ctx,
    )

    print("系统已启动，按 Ctrl+C 停止...")
    orchestrator.run()

    # 5. 清理
    db.close()


if __name__ == "__main__":
    main()
