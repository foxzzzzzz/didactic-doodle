"""配置数据模型定义。"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ScreenshotConfig:
    interval: float = 1.5
    save_debug: bool = False
    debug_dir: str = "./data/screenshots"


@dataclass
class OcrConfig:
    confidence_threshold: float = 0.7
    use_gpu: bool = False


@dataclass
class TemplateMatchingConfig:
    threshold: float = 0.8


@dataclass
class LLMConfig:
    provider: str = "minimax"
    api_key: str = ""
    model: str = "M2.7"
    base_url: str = "https://api.minimax.chat/v1"
    timeout: int = 15
    max_retries: int = 3
    temperature: float = 0.7
    max_output_tokens: int = 500


@dataclass
class KnowledgeBaseConfig:
    base_path: str = "./knowledge_base"
    max_chars: int = 3000


@dataclass
class ContextConfig:
    max_history_rounds: int = 20
    retention_days: int = 3
    session_idle_minutes: int = 30


@dataclass
class ActionConfig:
    type_delay: float = 0.05
    click_delay: float = 0.3
    random_delay_range: List[float] = field(default_factory=lambda: [0.5, 1.5])


@dataclass
class OperatorConfig:
    debug_mode: bool = False
    demo_mode: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "./data/logs/pdd_cs.log"
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass
class MonitoringConfig:
    health_check_interval: int = 60
    target_process: str = "拼多多商家工作台.exe"


@dataclass
class Coordinates:
    """屏幕坐标区域配置。"""
    # 窗口偏移
    offset_x: int = 0
    offset_y: int = 0

    # 对话内容区域
    chat_area: Tuple[int, int, int, int] = (380, 120, 820, 580)
    # 输入框区域
    input_box: Tuple[int, int, int, int] = (380, 720, 760, 80)
    # 发送按钮区域
    send_button: Tuple[int, int, int, int] = (1140, 720, 60, 80)
    # 发送按钮中心
    send_button_center: Tuple[int, int] = (1170, 760)
    # 输入框中心
    input_box_center: Tuple[int, int] = (760, 760)

    # 模板图片路径
    templates_dir: str = "./docs/templates"
    template_send_button: str = "send_button.png"
    template_input_box: str = "input_box.png"
    template_unread_badge: str = "unread_badge.png"


@dataclass
class AppConfig:
    """应用总配置。"""
    shop_id: str = "shop_001"
    screenshot: ScreenshotConfig = field(default_factory=ScreenshotConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    template_matching: TemplateMatchingConfig = field(default_factory=TemplateMatchingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    knowledge_base: KnowledgeBaseConfig = field(default_factory=KnowledgeBaseConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    action: ActionConfig = field(default_factory=ActionConfig)
    operator: OperatorConfig = field(default_factory=OperatorConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    coordinates: Coordinates = field(default_factory=Coordinates)
