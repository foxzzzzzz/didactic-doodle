"""自定义异常体系。

所有自定义异常继承自 PddCSException，方便上层统一捕获和处理。
"""


class PddCSException(Exception):
    """所有自定义异常的基类。"""
    pass


# ---- 配置相关 ----
class ConfigError(PddCSException):
    """配置加载失败。"""
    pass


# ---- 视觉识别相关 ----
class VisionError(PddCSException):
    """视觉识别模块错误。"""
    pass


class OcrError(VisionError):
    """OCR 识别错误。"""
    pass


class TemplateMatchError(VisionError):
    """模板匹配错误（未找到匹配）。"""
    pass


# ---- LLM 调用相关 ----
class LLMError(PddCSException):
    """LLM 调用相关错误。"""
    pass


class LLMApiError(LLMError):
    """API 返回错误。"""
    pass


class LLMTimeoutError(LLMError):
    """API 请求超时。"""
    pass


class LLMRateLimitError(LLMError):
    """API 限流。"""
    pass


# ---- 操作执行相关 ----
class ActionError(PddCSException):
    """操作执行相关错误。"""
    pass


class ClickError(ActionError):
    """鼠标点击失败。"""
    pass


class TypeActionError(ActionError):
    """键盘输入失败。"""
    pass
