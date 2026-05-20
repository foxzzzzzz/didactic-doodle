"""模板匹配模块。

使用 OpenCV 在截图中定位固定 UI 元素（发送按钮、输入框、未读标记）。
匹配失败时返回未找到状态，由调用方回退到坐标配置。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image


@dataclass
class MatchResult:
    """模板匹配结果。"""
    found: bool
    x: int = 0       # 匹配中心点 x（相对截图左上角）
    y: int = 0       # 匹配中心点 y
    confidence: float = 0.0


class TemplateMatcher:
    """OpenCV 模板匹配器。"""

    def __init__(self, threshold: float = 0.8) -> None:
        self._threshold = threshold

    def find(
        self,
        screenshot: Image.Image,
        template_path: str,
        region: Optional[tuple] = None,
    ) -> MatchResult:
        """在截图中查找模板位置。

        Args:
            screenshot: 截图的 PIL Image。
            template_path: 模板图片的文件路径。
            region: 可选的搜索子区域 (x, y, w, h)，相对于截图。

        Returns:
            MatchResult，found=False 表示未找到。
        """
        template_file = Path(template_path)
        if not template_file.exists():
            return MatchResult(found=False)

        # 转 OpenCV 格式
        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        template_cv = cv2.imread(str(template_file))

        if template_cv is None:
            return MatchResult(found=False)

        # 裁切搜索区域
        if region is not None:
            rx, ry, rw, rh = region
            screen_cv = screen_cv[ry:ry + rh, rx:rx + rw]

        # 防止模板大于截图
        th, tw = template_cv.shape[:2]
        sh, sw = screen_cv.shape[:2]
        if th > sh or tw > sw:
            return MatchResult(found=False)

        result = cv2.matchTemplate(screen_cv, template_cv, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < self._threshold:
            return MatchResult(found=False, confidence=max_val)

        center_x = max_loc[0] + tw // 2
        center_y = max_loc[1] + th // 2

        if region is not None:
            center_x += region[0]
            center_y += region[1]

        return MatchResult(
            found=True,
            x=center_x,
            y=center_y,
            confidence=max_val,
        )

    def find_all(
        self,
        screenshot: Image.Image,
        template_path: str,
    ) -> List[MatchResult]:
        """查找截图中所有匹配的模板位置（用于多个红点等场景）。

        Args:
            screenshot: 截图的 PIL Image。
            template_path: 模板图片的文件路径。

        Returns:
            MatchResult 列表（仅包含 found=True 的结果）。
        """
        template_file = Path(template_path)
        if not template_file.exists():
            return []

        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        template_cv = cv2.imread(str(template_file))

        if template_cv is None:
            return []

        th, tw = template_cv.shape[:2]
        sh, sw = screen_cv.shape[:2]
        if th > sh or tw > sw:
            return []

        result = cv2.matchTemplate(screen_cv, template_cv, cv2.TM_CCOEFF_NORMED)

        locations = []
        result_flat = result.ravel()
        for idx in np.argsort(result_flat)[::-1]:
            val = result_flat[idx]
            if val < self._threshold:
                break

            cy = idx // result.shape[1] + th // 2
            cx = idx % result.shape[1] + tw // 2

            # 去重：与已有结果距离过近的跳过
            too_close = False
            for existing in locations:
                if abs(cx - existing.x) < tw and abs(cy - existing.y) < th:
                    too_close = True
                    break

            if not too_close:
                locations.append(MatchResult(
                    found=True, x=int(cx), y=int(cy), confidence=float(val),
                ))

        return locations
