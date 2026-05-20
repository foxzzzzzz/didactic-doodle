"""坐标标定辅助工具。

交互式标定屏幕坐标区域，生成 coordinates.local.yaml 配置文件。

使用方法:
    python tools/calibrate.py

流程:
    1. 全屏截图并显示
    2. 按照提示点击各区域
    3. 自动计算并保存坐标
"""

import tkinter as tk
from pathlib import Path
from tkinter.messagebox import showinfo

import mss
import yaml
from PIL import Image, ImageTk


class Calibrator:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("坐标标定工具 — 拼多多智能客服系统")

        self.points: list[tuple[int, int]] = []
        self.labels: list[str] = []
        self.steps = [
            ("chat_tl", "请点击【对话内容区域】的左上角"),
            ("chat_br", "请点击【对话内容区域】的右下角"),
            ("input_center", "请点击【输入框】的中心位置"),
            ("send_center", "请点击【发送按钮】的中心位置"),
        ]

        # 加载截图
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            self.image = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            self.tk_image = ImageTk.PhotoImage(self.image)

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.image.width,
            height=self.image.height,
            cursor="crosshair",
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.bind("<Button-1>", self._on_click)

        # 状态标签
        self.status = tk.Label(
            self.root,
            text=self.steps[0][1],
            font=("Microsoft YaHei", 14),
            bg="yellow",
        )
        self.status.pack(fill=tk.X)

        self._current_step = 0

    def _on_click(self, event: tk.Event) -> None:
        x, y = event.x, event.y
        name, _ = self.steps[self._current_step]
        self.points.append((x, y))
        self.labels.append(name)

        # 画标记
        self.canvas.create_oval(
            x - 5, y - 5, x + 5, y + 5, fill="red", outline="red",
        )
        self.canvas.create_text(
            x + 15, y - 10, text=name, fill="red", anchor=tk.W,
        )

        self._current_step += 1

        if self._current_step < len(self.steps):
            self.status.config(text=self.steps[self._current_step][1])
        else:
            self.status.config(text="标定完成！正在保存...")
            self.root.after(500, self._save_and_exit)

    def _save_and_exit(self) -> None:
        config_path = Path("config/coordinates.local.yaml")

        # 计算区域
        tl = self.points[0]  # chat area top-left
        br = self.points[1]  # chat area bottom-right
        inp = self.points[2]  # input center
        send = self.points[3]  # send button center

        data = {
            "window": {"offset_x": 0, "offset_y": 0},
            "chat_area": {
                "x": tl[0], "y": tl[1],
                "width": br[0] - tl[0], "height": br[1] - tl[1],
            },
            "input_box": {
                "x": inp[0] - 150, "y": inp[1] - 30,
                "width": 300, "height": 60,
            },
            "send_button": {
                "x": send[0] - 25, "y": send[1] - 20,
                "width": 50, "height": 40,
            },
            "send_button_center": {"x": send[0], "y": send[1]},
            "input_box_center": {"x": inp[0], "y": inp[1]},
        }

        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# 自动生成的坐标配置（覆盖 coordinates.yaml）\n")
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        showinfo("完成", f"坐标已保存到 {config_path}")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    print("坐标标定工具")
    print("请确保拼多多商家工作台窗口可见")
    print()
    Calibrator().run()
