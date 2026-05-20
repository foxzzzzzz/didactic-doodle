"""SQLite 数据库管理。

管理对话记录的表创建、插入、查询操作。
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


@dataclass
class ConversationRecord:
    """单条对话记录。"""
    shop_id: str
    customer_id: str
    session_id: str      # "shop_001_customer_张三"
    customer_msg: str
    reply: str
    tag: str = ""
    created_at: str = ""


class Database:
    """SQLite 数据库管理器。"""

    def __init__(self, db_path: str = "./data/pdd_cs.db") -> None:
        self._db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def init_db(self) -> None:
        """初始化数据库，创建表结构。"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id     TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                customer_msg TEXT NOT NULL,
                reply       TEXT NOT NULL,
                tag         TEXT DEFAULT '',
                created_at  TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON conversations(session_id, created_at)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created
            ON conversations(created_at)
        """)
        self._conn.commit()

    def save_conversation(self, record: ConversationRecord) -> int:
        """保存一条对话记录。

        Returns:
            新记录的 ID。
        """
        if record.created_at == "":
            record.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = self._conn.execute(
            """INSERT INTO conversations
               (shop_id, customer_id, session_id, customer_msg, reply, tag, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (record.shop_id, record.customer_id, record.session_id,
             record.customer_msg, record.reply, record.tag, record.created_at),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_history(
        self,
        session_id: str,
        limit: int = 20,
        retention_days: int = 3,
    ) -> List[ConversationRecord]:
        """查询指定会话的历史对话。

        Args:
            session_id: 会话标识（店铺 + 客户昵称）。
            limit: 最多返回条数。
            retention_days: 只查询最近 N 天的记录。

        Returns:
            对话记录列表，按时间升序。
        """
        since = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")

        cursor = self._conn.execute(
            """SELECT shop_id, customer_id, session_id, customer_msg, reply, tag, created_at
               FROM conversations
               WHERE session_id = ? AND created_at >= ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (session_id, since, limit),
        )

        return [
            ConversationRecord(
                shop_id=row[0],
                customer_id=row[1],
                session_id=row[2],
                customer_msg=row[3],
                reply=row[4],
                tag=row[5],
                created_at=row[6],
            )
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn:
            self._conn.close()
            self._conn = None
