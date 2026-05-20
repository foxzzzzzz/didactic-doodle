"""会话上下文管理器。

按 session_id（店铺 + 客户昵称）管理对话上下文，
提供历史对话的读取、新消息的持久化和 prompt 格式化。
"""

from typing import Dict, List, Optional

from .database import ConversationRecord, Database


class SessionContext:
    """会话上下文管理器。

    Args:
        database: Database 实例。
        max_history: 注入 prompt 的最大历史轮数。
    """

    def __init__(self, database: Database, max_history: int = 20) -> None:
        self._db = database
        self._max_history = max_history

    def get_history_for_prompt(
        self,
        session_id: str,
        retention_days: int = 3,
    ) -> List[Dict[str, str]]:
        """获取指定会话的对话历史，格式化为 prompt 可用格式。

        Args:
            session_id: 会话标识。
            retention_days: 上下文保留天数。

        Returns:
            [{"role": "customer", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        records = self._db.get_history(
            session_id=session_id,
            limit=self._max_history * 2,  # 每轮对话有客户 + 客服两条
            retention_days=retention_days,
        )

        history = []
        for r in records:
            history.append({"role": "customer", "content": r.customer_msg})
            if r.reply:
                history.append({"role": "assistant", "content": r.reply})

        return history

    def add_interaction(
        self,
        session_id: str,
        shop_id: str,
        customer_id: str,
        customer_msg: str,
        reply: str,
        tag: str = "",
    ) -> None:
        """添加一轮交互到上下文。

        Args:
            session_id: 会话标识。
            shop_id: 店铺编号。
            customer_id: 客户标识（昵称）。
            customer_msg: 客户消息内容。
            reply: AI 回复内容。
            tag: 问题分类标签。
        """
        record = ConversationRecord(
            shop_id=shop_id,
            customer_id=customer_id,
            session_id=session_id,
            customer_msg=customer_msg,
            reply=reply,
            tag=tag,
        )
        self._db.save_conversation(record)
