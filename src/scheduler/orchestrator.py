"""Phase 1 主循环调度器。

单店铺单会话的自动回复循环：
截屏 → OCR → 检测新消息 → 组装 prompt → 调用 LLM → 输入并发送 → 记录数据库
"""

import hashlib
import time
from datetime import datetime
from typing import Optional

from ..config.schema import AppConfig
from ..vision.screenshot import ScreenCapture
from ..vision.ocr import OcrEngine
from ..vision.template import TemplateMatcher
from ..llm.client import BaseLLMClient, LLMMessage
from ..llm.prompt import build_system_prompt, build_user_message, parse_llm_response
from ..knowledge.loader import KnowledgeBase
from ..action.operator import UIOperator
from ..memory.database import Database, ConversationRecord
from ..memory.context import SessionContext
from ..utils.exceptions import LLMError, OcrError, VisionError
from ..utils.logger import setup_logger


class Phase1Orchestrator:
    """Phase 1 主调度器。

    单店铺单会话全自动回复流程。
    通过文字变化 hash 对比检测新消息（Phase 2 升级为未读标记检测）。

    Usage:
        orchestrator = Phase1Orchestrator(config, capture, ocr, ...)
        orchestrator.run()
    """

    def __init__(
        self,
        config: AppConfig,
        capture: ScreenCapture,
        ocr: OcrEngine,
        llm: BaseLLMClient,
        operator: UIOperator,
        kb: KnowledgeBase,
        db: Database,
        ctx: SessionContext,
    ) -> None:
        self._config = config
        self._capture = capture
        self._ocr = ocr
        self._llm = llm
        self._operator = operator
        self._kb = kb
        self._db = db
        self._ctx = ctx

        self._logger = setup_logger(
            level=config.logging.level,
            log_file=config.logging.file,
            max_bytes=config.logging.max_size_mb * 1024 * 1024,
            backup_count=config.logging.backup_count,
        )

        self._running = False
        self._last_message_hash: str = ""
        self._customer_nickname: str = "unknown"
        self._rounds_processed: int = 0
        self._refund_sessions: set = set()  # 已标记转人工的会话集合
        self._kb_cache: Optional[str] = None  # 知识库全文缓存，首轮加载后复用

    # ---- 主循环 ----

    def run(self) -> None:
        """启动主循环。按 Ctrl+C 停止。"""
        self._logger.info("=" * 50)
        self._logger.info("拼多多智能客服系统 Phase %d 启动", self._config.shop_id)
        self._logger.info("店铺: %s", self._config.shop_id)
        self._logger.info("=" * 50)

        self._running = True

        try:
            while self._running:
                try:
                    self.process_once()
                except (VisionError, OcrError) as e:
                    self._logger.warning("视觉识别异常，跳过本轮: %s", e)
                except LLMError as e:
                    self._logger.error("LLM 调用异常，跳过本轮: %s", e)
                except Exception as e:
                    self._logger.error("未预期异常，跳过本轮: %s", e, exc_info=True)

                time.sleep(self._config.screenshot.interval)
        except KeyboardInterrupt:
            self._logger.info("收到停止信号，正在退出...")
        finally:
            self.stop()

    def stop(self) -> None:
        """优雅停止。"""
        self._running = False
        self._logger.info(
            "系统已停止。本次运行处理 %d 轮对话。",
            self._rounds_processed,
        )

    def process_once(self) -> None:
        """单次处理循环。"""
        # 1. 截屏对话区域
        screenshot = self._capture.capture_chat_area()
        if screenshot is None:
            self._logger.warning("截屏失败，跳过本轮")
            return

        if self._config.screenshot.save_debug:
            self._capture.save_debug(
                screenshot,
                f"chat_{datetime.now().strftime('%H%M%S')}",
                self._config.screenshot.debug_dir,
            )

        # 2. OCR 提取文字
        results = self._ocr.recognize(screenshot)
        if not results:
            return  # 无文字，无新消息

        full_text = "\n".join(r.text for r in results)
        current_hash = hashlib.md5(full_text.encode()).hexdigest()

        # 3. 检测新消息（hash 对比 + 排除 AI 最后的消息）
        if current_hash == self._last_message_hash:
            return
        self._last_message_hash = current_hash

        # 提取最新客户消息（OCR 结果的最后几行）
        customer_msg = self._extract_latest_message(results)
        if not customer_msg:
            return

        # 提取客户昵称
        self._customer_nickname = self._extract_customer_name(results)
        session_id = f"{self._config.shop_id}_{self._customer_nickname}"

        self._logger.info("检测到新消息 from %s: %s", session_id, customer_msg[:80])

        # 检查是否转人工会话
        if session_id in self._refund_sessions:
            self._logger.info("会话 %s 已标记转人工，跳过", session_id)
            return

        # 4. 获取上下文
        history = self._ctx.get_history_for_prompt(
            session_id=session_id,
            retention_days=self._config.context.retention_days,
        )
        if self._kb_cache is None:
            self._kb_cache = self._kb.load_all(
                self._config.shop_id,
                max_chars=self._config.knowledge_base.max_chars,
            )
        kb_text = self._kb_cache

        # 5. 组装 prompt 并调用 LLM
        system_prompt = build_system_prompt(
            shop_name=self._config.shop_id,
            kb_text=kb_text,
            customer_nickname=self._customer_nickname,
        )
        user_message = build_user_message(
            customer_message=customer_msg,
            history=history,
        )

        if self._config.operator.debug_mode:
            self._logger.info("DEBUG - System prompt:\n%s", system_prompt[:500])
            self._logger.info("DEBUG - User message:\n%s", user_message[:500])

        if self._config.operator.demo_mode:
            reply = "亲，您好！这是演示模式的自动回复~"
            tag = ""
        else:
            raw_reply = self._llm.chat([
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_message),
            ])
            parsed = parse_llm_response(raw_reply)
            reply = parsed["reply"]
            tag = parsed["tag"]

        self._logger.info("LLM 回复: %s", reply[:80])

        # 6. 检查转人工
        if tag == "REFUND" or tag == "TRANSFER_HUMAN":
            self._logger.info("会话 %s 触发转人工 (tag=%s)", session_id, tag)
            self._refund_sessions.add(session_id)

        # 7. 输入并发送
        if not self._config.operator.debug_mode:
            self._operator.send_message(reply)
        else:
            self._logger.info("DEBUG 模式，跳过实际操作: %s", reply)

        # 8. 记录数据库
        self._ctx.add_interaction(
            session_id=session_id,
            shop_id=self._config.shop_id,
            customer_id=self._customer_nickname,
            customer_msg=customer_msg,
            reply=reply,
            tag=tag,
        )

        self._rounds_processed += 1
        self._logger.info("第 %d 轮处理完成", self._rounds_processed)

    # ---- 消息提取 ----

    def _extract_latest_message(self, results: list) -> Optional[str]:
        """从 OCR 结果列表中提取最新的客户消息。

        Phase 1 策略：取最后 3 行中非空、内容看起来像客户消息的文本。
        后续可通过对话区域的"客户:"模式匹配来改进。

        Args:
            results: OCRResult 列表。

        Returns:
            提取到的客户消息文本，或 None 表示没有新消息。
        """
        if not results:
            return None

        # 取最后几条非空文本
        recent = [r.text.strip() for r in results[-3:] if r.text.strip()]
        if not recent:
            return None

        # 过滤过短的文本（可能是 UI 元素被 OCR 出来）
        meaningful = [t for t in recent if len(t) >= 2]
        if not meaningful:
            return None

        return meaningful[-1]  # 最后一条有意义的消息

    def _extract_customer_name(self, results: list) -> str:
        """从对话区域 OCR 结果中提取客户昵称。

        Phase 1 策略：取前几行中包含"客户"关键词或看起来像昵称的文本。
        后续可以通过屏幕区域的特定位置提取。

        Args:
            results: OCRResult 列表。

        Returns:
            客户昵称字符串。
        """
        if not results:
            return "unknown"

        for r in results[:5]:
            text = r.text.strip()
            # 尝试匹配 "客户: xxx" 格式
            if ":" in text or "：" in text:
                parts = text.replace("：", ":").split(":", 1)
                if len(parts) == 2 and len(parts[1].strip()) >= 1:
                    return parts[1].strip().split()[0]  # 取第一部分作为昵称

        # 回退：取顶部第一行非空且不太长的文本作为可能的昵称
        for r in results[:5]:
            text = r.text.strip()
            if 2 <= len(text) <= 20:
                return text

        return "unknown"
