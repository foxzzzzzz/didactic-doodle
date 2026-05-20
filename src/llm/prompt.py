"""Prompt 模板管理。

提供 system prompt 构建、用户消息组装、LLM 回复解析等功能。
"""

from typing import Dict, List, Optional


def build_system_prompt(
    shop_name: str = "",
    kb_text: str = "",
    customer_nickname: str = "亲",
) -> str:
    """构建系统角色 prompt。

    Args:
        shop_name: 店铺名称。
        kb_text: 知识库文本（商品信息、政策、话术等）。
        customer_nickname: 当前客户的昵称。

    Returns:
        完整的 system prompt 字符串。
    """
    parts = []

    # 角色设定
    parts.append(
        f"你是拼多多店铺「{shop_name or '拼多多商家'}」的专业客服。"
        f"你的回复风格亲切、专业、有耐心。"
        f"对客户的称呼使用「{customer_nickname}」或「亲」。"
    )

    # 回复原则
    parts.append(
        "回复原则：\n"
        "- 简洁明了，不要啰嗦\n"
        "- 遇到商品质量问题，先道歉并表示理解\n"
        "- 不要承诺无法兑现的事情（如具体到货时间）\n"
        "- 涉及退款、赔偿的事项，统一回复「为您转接人工客服处理」\n"
        "- 不要发送任何商品链接、电话、微信号\n"
        "- 只回复中文，不要使用其他语言"
    )

    # 知识库注入
    if kb_text:
        # 截断过长的知识库
        if len(kb_text) > 3000:
            kb_text = kb_text[:3000] + "\n...(知识库内容过长，已截断)"
        parts.append(f"\n以下是本店铺的相关信息，请严格依据以下内容回复：\n\n{kb_text}")

    # 输出格式
    parts.append(
        "\n你只需要输出要回复给客户的文字内容，不要加任何前缀、引号或标记。"
        "如果是退款/赔偿相关，请回复「REFUND:」后跟兜底话术。"
    )

    return "\n\n".join(parts)


def build_user_message(
    customer_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """构建用户消息 prompt，带上对话历史。

    Args:
        customer_message: 客户最新消息文本。
        history: 历史对话列表 [{"role": "customer"/"assistant", "content": "..."}]

    Returns:
        组装好的用户消息字符串。
    """
    if not history:
        return f"客户说：{customer_message}\n\n请回复。"

    lines = ["以下是最近的对话历史：\n"]
    for item in history[-20:]:  # 最多 20 轮
        role_label = "客户" if item["role"] == "customer" else "客服"
        lines.append(f"{role_label}: {item['content']}")

    lines.append(f"\n客户的最新消息：{customer_message}")
    lines.append("\n请根据历史对话和店铺知识库，给出专业的回复。")
    return "\n".join(lines)


def parse_llm_response(response: str) -> Dict[str, str]:
    """解析 LLM 返回内容，提取回复文本和标记。

    Returns:
        {"reply": "实际回复内容", "tag": "REFUND" | "TRANSFER_HUMAN" | ""}
    """
    response = response.strip()

    # 检测是否触发退款转人工标记
    if response.upper().startswith("REFUND"):
        # 去掉 REFUND: 或 REFUND 前缀
        reply = response.split(":", 1)[-1].strip() if ":" in response else response[6:].strip()
        if not reply:
            reply = "亲，已为您转接人工客服处理，请稍等~"
        return {"reply": reply, "tag": "REFUND"}

    # 检测转人工标记
    if "TRANSFER_HUMAN" in response.upper():
        return {"reply": "亲，已为您转接人工客服处理，请稍等~", "tag": "TRANSFER_HUMAN"}

    return {"reply": response, "tag": ""}
