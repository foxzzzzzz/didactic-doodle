"""MiniMax API Key 连通性验证工具。

验证 default.yaml 中的 api_key 配置是否正确、能否正常调用 LLM。

使用方法:
    python tools/check_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.loader import ConfigLoader
from src.llm.client import LLMMessage, MiniMaxClient
from src.utils.exceptions import LLMApiError, LLMRateLimitError, LLMTimeoutError


def main() -> None:
    print("=" * 50)
    print("  MiniMax API Key 连通性验证")
    print("=" * 50)
    print()

    # 1. 加载配置
    print("[1/3] 加载配置文件...")
    config = ConfigLoader.load("./config")

    # 2. 检查 api_key
    print("[2/3] 检查 api_key 配置...")
    if not config.llm.api_key:
        print()
        print("[FAIL] api_key 未配置！")
        print("  请在 config/default.yaml 的 llm.api_key 字段中填入密钥")
        sys.exit(1)

    print(f"  Provider : {config.llm.provider}")
    print(f"  Model    : {config.llm.model}")
    print(f"  Base URL : {config.llm.base_url}")
    print(f"  API Key  : {config.llm.api_key[:8]}...{config.llm.api_key[-4:]}")
    print()

    # 3. 发送测试请求
    print("[3/3] 发送测试请求...")
    client = MiniMaxClient(config.llm)

    try:
        reply = client.chat([
            LLMMessage(role="system", content="你是一个测试助手。"),
            LLMMessage(role="user", content="请回复'OK'，不要多字。"),
        ])
        print(f"  LLM 回复 : {reply}")
        print()
        print("=" * 50)
        print("  [PASS] API Key 配置正确，连通性正常！")
        print("=" * 50)
    except LLMTimeoutError as e:
        print(f"  [FAIL] 请求超时: {e}")
        print("  请检查网络连接或增大 llm.timeout")
        sys.exit(1)
    except LLMRateLimitError as e:
        print(f"  [FAIL] 触发限流: {e}")
        print("  请稍后重试或检查账户配额")
        sys.exit(1)
    except LLMApiError as e:
        error_msg = str(e)
        print(f"  [FAIL] API 错误: {error_msg}")
        if "401" in error_msg or "403" in error_msg:
            print("  → 可能是 api_key 无效，请检查配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
