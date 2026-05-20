"""Prompt 模板测试。"""

from src.llm.prompt import build_system_prompt, build_user_message, parse_llm_response


def test_build_system_prompt_includes_kb():
    result = build_system_prompt(
        shop_name="测试店铺",
        kb_text="这是商品信息",
        customer_nickname="亲",
    )
    assert "测试店铺" in result
    assert "这是商品信息" in result


def test_build_system_prompt_truncates_long_kb():
    long_kb = "X" * 4000
    result = build_system_prompt(kb_text=long_kb)
    assert len(result) < 3500


def test_parse_normal_response():
    result = parse_llm_response("亲，您好，有什么可以帮您的？")
    assert result["tag"] == ""
    assert "您好" in result["reply"]


def test_parse_refund_response():
    result = parse_llm_response("REFUND:亲，已为您转接人工客服处理")
    assert result["tag"] == "REFUND"
    assert "转接" in result["reply"]


def test_build_user_message_with_history():
    history = [
        {"role": "customer", "content": "你好"},
        {"role": "assistant", "content": "您好"},
    ]
    result = build_user_message("新消息", history)
    assert "你好" in result
    assert "您好" in result
    assert "新消息" in result
