"""知识库加载模块测试。"""

from src.knowledge.loader import KnowledgeBase


def test_load_all_returns_content():
    kb = KnowledgeBase("./knowledge_base")
    text = kb.load_all("shop_001")
    assert len(text) > 0
    assert "商品信息" in text or "退换货" in text or "话术" in text


def test_get_topics():
    kb = KnowledgeBase("./knowledge_base")
    topics = kb.get_topics("shop_001")
    assert len(topics) >= 3


def test_load_nonexistent_shop():
    kb = KnowledgeBase("./knowledge_base")
    text = kb.load_all("nonexistent")
    assert text == ""
