"""Markdown 知识库加载器。

读取店铺对应的 markdown 文件，拼接为文本供 LLM prompt 使用。
Phase 1 采用全文加载策略，不做智能切片。
Phase 2 TODO: 语义检索替代全量加载，按客户问题匹配相关内容，节省 token。
"""

from pathlib import Path
from typing import List, Optional


class KnowledgeBase:
    """店铺知识库管理器。

    Args:
        base_path: 知识库根目录路径，如 "./knowledge_base"。
    """

    def __init__(self, base_path: str = "./knowledge_base") -> None:
        self._base = Path(base_path)

    def load_all(self, shop_id: str, max_chars: int = 3000) -> str:
        """加载指定店铺的全部知识库文件，拼接为连续文本。

        Args:
            shop_id: 店铺编号（目录名），如 "shop_001"。
            max_chars: 最大总字符数，超出部分截断。

        Returns:
            拼接后的知识库文本。
        """
        shop_dir = self._base / shop_id
        if not shop_dir.exists():
            return ""

        parts = []
        total = 0

        for md_file in sorted(shop_dir.glob("*.md")):
            if total >= max_chars:
                break

            content = self.load_file(shop_id, md_file.name)
            if not content:
                continue

            # 按文件名生成标题
            title = md_file.stem
            section = f"## {title}\n\n{content}\n"

            if total + len(section) > max_chars:
                remaining = max_chars - total
                section = section[:remaining] + "\n..."

            parts.append(section)
            total += len(section)

        return "\n".join(parts)

    def load_file(self, shop_id: str, filename: str) -> Optional[str]:
        """读取指定文件内容。

        Args:
            shop_id: 店铺编号。
            filename: 文件名（如 "商品信息.md"）。

        Returns:
            文件文本内容，或 None 表示文件不存在。
        """
        file_path = self._base / shop_id / filename
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def get_topics(self, shop_id: str) -> List[str]:
        """列出指定店铺可用的知识主题（即文件名不含扩展名）。

        Args:
            shop_id: 店铺编号。

        Returns:
            知识主题名称列表。
        """
        shop_dir = self._base / shop_id
        if not shop_dir.exists():
            return []

        return sorted(md.stem for md in shop_dir.glob("*.md"))
