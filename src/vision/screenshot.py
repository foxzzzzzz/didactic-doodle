"""屏幕截图模块。

使用 mss 进行高性能局部区域截屏，比 PIL ImageGrab 快 5-10 倍。
"""

from typing import Optional

import mss
from PIL import Image

from ..config.schema import Coordinates


class ScreenCapture:
    """屏幕区域截图器。"""

    def __init__(self, coordinates: Coordinates) -> None:
        self._coords = coordinates
        self._sct = mss.mss()

    def capture_chat_area(self) -> Optional[Image.Image]:
        """截取对话内容区域。

        Returns:
            PIL Image 对象，或 None（截取失败时）。
        """
        x, y, w, h = self._coords.chat_area
        return self.capture_region((x, y, w, h))

    def capture_input_area(self) -> Optional[Image.Image]:
        """截取输入框区域。"""
        x, y, w, h = self._coords.input_box
        return self.capture_region((x, y, w, h))

    def capture_region(self, region: tuple) -> Optional[Image.Image]:
        """截取指定区域。

        Args:
            region: (x, y, width, height) 屏幕坐标。

        Returns:
            PIL Image 对象。
        """
        x, y, w, h = region
        x += self._coords.offset_x
        y += self._coords.offset_y

        monitor = {"top": y, "left": x, "width": w, "height": h}
        try:
            img = self._sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        except Exception:
            return None

    def capture_full(self) -> Optional[Image.Image]:
        """截取全屏（调试用）。"""
        try:
            monitor = self._sct.monitors[1]
            img = self._sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        except Exception:
            return None

    def save_debug(self, image: Image.Image, name: str, debug_dir: str = "./data/screenshots") -> None:
        """保存调试截图到指定目录。"""
        import os
        from pathlib import Path

        path = Path(debug_dir)
        path.mkdir(parents=True, exist_ok=True)
        image.save(str(path / f"{name}.png"))
