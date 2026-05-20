"""操作执行模块。

封装 pyautogui 鼠标键盘操作，加入随机延迟模拟人工操作节奏。
支持模板匹配定位 + 固定坐标回退两种定位方式。
"""

import random
import time
from pathlib import Path
from typing import Optional

import pyautogui

from ..config.schema import ActionConfig, Coordinates
from ..utils.exceptions import ClickError

# pyautogui 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class UIOperator:
    """UI 操作器。

    封装点击、键盘输入、发送等操作，自动加入随机延迟。
    """

    def __init__(self, config: ActionConfig, coordinates: Coordinates) -> None:
        self._config = config
        self._coords = coordinates
        self._template_dir = Path(coordinates.templates_dir)

    # ---- 基础操作 ----

    def click(self, x: int, y: int) -> None:
        """点击指定屏幕坐标。

        Raises:
            ClickError: 坐标越界或点击失败。
        """
        try:
            pyautogui.click(x, y)
            self._random_delay_after_click()
        except Exception as e:
            raise ClickError(f"点击 ({x}, {y}) 失败: {e}") from e

    def type_text(self, text: str) -> None:
        """逐字输入文本，字符间加随机延迟模拟打字节奏。"""
        for char in text:
            pyautogui.typewrite(char, interval=self._config.type_delay / 2)
            time.sleep(random.uniform(0.02, 0.06))

    def press_enter(self) -> None:
        """按下回车键。"""
        pyautogui.press("enter")
        self._random_delay_after_click()

    def select_all(self) -> None:
        """Ctrl+A 全选。"""
        pyautogui.hotkey("ctrl", "a")
        time.sleep(self._config.click_delay)

    def press_delete(self) -> None:
        """按下 Delete 键。"""
        pyautogui.press("delete")
        time.sleep(self._config.click_delay)

    # ---- 组合操作 ----

    def click_input_box(self) -> None:
        """点击输入框使其获得焦点。

        先尝试模板匹配，失败则用固定坐标。
        """
        match = self._find_template(self._coords.template_input_box, self._coords.input_box)
        if match:
            x = self._coords.offset_x + match[0]
            y = self._coords.offset_y + match[1]
        else:
            ix, iy = self._coords.input_box_center
            x = self._coords.offset_x + ix
            y = self._coords.offset_y + iy

        self.click(x, y)

    def click_send(self) -> None:
        """点击发送按钮。

        先尝试模板匹配，失败则用固定坐标。
        """
        match = self._find_template(self._coords.template_send_button, self._coords.send_button)
        if match:
            x = self._coords.offset_x + match[0]
            y = self._coords.offset_y + match[1]
        else:
            sx, sy = self._coords.send_button_center
            x = self._coords.offset_x + sx
            y = self._coords.offset_y + sy

        self.click(x, y)

    def select_all_and_delete(self) -> None:
        """清空输入框内容。"""
        self.select_all()
        self.press_delete()

    def send_message(self, text: str) -> None:
        """完整的发送消息流程：聚焦输入框 → 清空 → 输入 → 发送。

        Args:
            text: 要发送的消息内容。
        """
        self.click_input_box()
        self.select_all_and_delete()
        self.type_text(text)
        time.sleep(self._config.click_delay)
        self.click_send()
        self._random_delay()

    # ---- 内部方法 ----

    def _find_template(self, template_name: str, fallback_region: tuple) -> Optional[tuple]:
        """尝试模板匹配定位 UI 元素。

        Returns:
            (center_x, center_y) 或 None。
        """
        template_path = self._template_dir / template_name
        if not template_path.exists():
            return None

        try:
            from ..vision.template import TemplateMatcher
            from ..vision.screenshot import ScreenCapture

            capture = ScreenCapture(self._coords)
            screenshot = capture.capture_region(fallback_region)
            if screenshot is None:
                return None

            matcher = TemplateMatcher()
            result = matcher.find(screenshot, str(template_path))
            if result.found:
                # 坐标相对于 fallback_region 左上角，转为屏幕坐标
                rx, ry, _, _ = fallback_region
                return (rx + result.x, ry + result.y)
        except Exception:
            pass

        return None

    def _random_delay(self) -> None:
        """操作间的随机延迟。"""
        lo, hi = self._config.random_delay_range
        time.sleep(random.uniform(lo, hi))

    def _random_delay_after_click(self) -> None:
        """点击后的固定 + 随机延迟。"""
        time.sleep(self._config.click_delay)
        self._random_delay()
