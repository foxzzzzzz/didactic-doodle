"""OCR 文字识别模块。

封装 PaddleOCR，提供文字识别和坐标提取能力。
PaddleOCR 初始化耗时较长（1-3 秒），使用单例模式，程序启动时初始化一次。
"""

from dataclasses import dataclass
from typing import List, Optional, Union

import numpy as np
from PIL import Image

from ..config.schema import OcrConfig
from ..utils.exceptions import OcrError


@dataclass
class OCRResult:
    """单条 OCR 识别结果。"""
    text: str
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2) 相对输入图片左上角


class OcrEngine:
    """PaddleOCR 引擎封装（单例）。

    使用方法:
        engine = OcrEngine(config)
        results = engine.recognize(image)
        text = engine.get_text(image)
    """

    _instance: Optional["OcrEngine"] = None

    def __new__(cls, config: Optional[OcrConfig] = None) -> "OcrEngine":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self, config: Optional[OcrConfig] = None) -> None:
        if self._initialized:
            return
        if config is None:
            config = OcrConfig()

        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            use_gpu=config.use_gpu,
            show_log=False,
        )
        self._conf_threshold = config.confidence_threshold
        self._initialized = True

    def recognize(self, image: Union[Image.Image, np.ndarray]) -> List[OCRResult]:
        """识别图片中的全部文字。

        Args:
            image: PIL Image 或 numpy 数组 (H, W, C) RGB/BGR 格式。

        Returns:
            OCRResult 列表，按阅读顺序（先上后下，先左后右）排列。
        """
        if isinstance(image, Image.Image):
            image = np.array(image)

        if not isinstance(image, np.ndarray):
            raise OcrError(f"OCR 输入类型错误，期望 PIL Image 或 numpy 数组，实际: {type(image)}")

        results = self._ocr.ocr(image, cls=True)

        if not results or not results[0]:
            return []

        items = []
        for line in results[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]
            confidence = line[1][1]

            if confidence < self._conf_threshold:
                continue

            x1 = min(p[0] for p in bbox)
            y1 = min(p[1] for p in bbox)
            x2 = max(p[0] for p in bbox)
            y2 = max(p[1] for p in bbox)

            items.append(OCRResult(
                text=text,
                confidence=confidence,
                bbox=(int(x1), int(y1), int(x2), int(y2)),
            ))

        # 按阅读顺序排序：从上到下，从左到右
        items.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
        return items

    def get_text(self, image: Image.Image) -> str:
        """识别图片中的全部文字并拼接为连续文本。

        Returns:
            所有识别结果用换行拼接的字符串。
        """
        results = self.recognize(image)
        return "\n".join(r.text for r in results)

    def find_text(self, image: Image.Image, keyword: str) -> List[OCRResult]:
        """查找图片中包含指定关键字的文字区域。

        Args:
            image: PIL Image 对象。
            keyword: 要搜索的关键字。

        Returns:
            匹配的 OCRResult 列表。
        """
        results = self.recognize(image)
        return [r for r in results if keyword in r.text]

    @property
    def confidence_threshold(self) -> float:
        return self._conf_threshold
