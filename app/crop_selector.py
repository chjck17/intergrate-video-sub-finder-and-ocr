"""Interactive crop selector window for defining subtitle regions."""

from __future__ import annotations

import datetime

import cv2
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk


class CropSelectorApp:
    """Allow the user to fine-tune crop boundaries on top of a playing video."""

    def __init__(
        self,
        window: tk.Toplevel,
        video_path: str,
        update_crop_callback,
        profile_getter,
        apply_video_callback,
    ):
        self.root = window
        self.video_path = video_path
        self.update_crop_callback = update_crop_callback
        self.profile_getter = profile_getter
        self.apply_video_callback = apply_video_callback

        self.cap = None
        self.frame = None
        self.photo = None
        self.canvas = None
        self.canvas_width = 0
        self.canvas_height = 0

        self.top_line_y = 0
        self.bottom_line_y = 0
        self.left_line_x = 0
        self.right_line_x = 0
        self.selected_line = None
        self.total_frames = 0
        self.current_frame_index = 0

        self.top_var = tk.StringVar(value="0")
        self.bottom_var = tk.StringVar(value="0")
        self.left_var = tk.StringVar(value="0")
        self.right_var = tk.StringVar(value="0")

        self._build_ui()
        self.root.after(100, self.load_video)

    def _build_ui(self):
        self.root.title("Chọn vùng chứa phụ đề")
        self.root.geometry("700x600")
        self.root.transient(self.root.master)
        self.root.grab_set()

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(main_frame, bg="black", cursor="arrow")
        self.canvas.pack(expand=True, fill=tk.BOTH, padx=1, pady=1)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        param_frame = tk.Frame(main_frame)
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text="Top:").pack(side=tk.LEFT, padx=5)
        tk.Entry(param_frame, textvariable=self.top_var, width=10, state="readonly",
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=2)

        tk.Label(param_frame, text="Bottom:").pack(side=tk.LEFT, padx=5)
        tk.Entry(param_frame, textvariable=self.bottom_var, width=10, state="readonly",
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=2)

        tk.Label(param_frame, text="Left:").pack(side=tk.LEFT, padx=5)
        tk.Entry(param_frame, textvariable=self.left_var, width=10, state="readonly",
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=2)

        tk.Label(param_frame, text="Right:").pack(side=tk.LEFT, padx=5)
        tk.Entry(param_frame, textvariable=self.right_var, width=10, state="readonly",
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=2)

        tk.Button(param_frame, text="Xác nhận vùng chọn", command=self.confirm_selection).pack(side=tk.LEFT, padx=5)

        timeline_frame = tk.Frame(main_frame)
        timeline_frame.pack(fill=tk.X, pady=5)

        self.slider = tk.Scale(timeline_frame, orient="horizontal", command=self.seek_video)
        self.slider.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.time_label = tk.Label(timeline_frame, text="00:00:00.000", font=("Helvetica", 10))
        self.time_label.pack(side=tk.LEFT, padx=2)
        tk.Button(timeline_frame, text=">>1giây", command=self.fast_forward_1s, width=8).pack(side=tk.LEFT, padx=5)

    def load_video(self):
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", f"Could not open video file at {self.video_path}")
            return

        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        scale_ratio = min(window_width / self.video_width, window_height / self.video_height)

        self.canvas_width = int(self.video_width * scale_ratio)
        self.canvas_height = int(self.video_height * scale_ratio)
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)

        if self.video_width > 0 and self.video_height > 0:
            self.top_line_y = int(0.8574 * self.video_height)
            self.bottom_line_y = int(0.9898 * self.video_height)
            self.left_line_x = int(0.1 * self.video_width)
            self.right_line_x = int(0.9 * self.video_width)

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.config(to=self.total_frames - 1)
        self.current_frame_index = 0

        self.show_frame()

    def seek_video(self, value):
        frame_index = int(float(value))
        if frame_index != self.current_frame_index:
            self.current_frame_index = frame_index
            self.show_frame()

    def fast_forward_1s(self):
        if not self.cap:
            return
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        current_time = self.current_frame_index / fps if fps else 0
        new_time = current_time + 1
        new_frame_index = int(new_time * fps) if fps else self.current_frame_index
        new_frame_index = min(new_frame_index, self.total_frames - 1)
        self.current_frame_index = new_frame_index
        self.slider.set(new_frame_index)
        self.show_frame()

    def show_frame(self):
        if not self.cap or not self.cap.isOpened():
            return

        self.canvas_width = self.canvas.winfo_width() or self.canvas_width
        self.canvas_height = self.canvas.winfo_height() or self.canvas_height

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index)
        success, frame = self.cap.read()
        if not success:
            return

        if self.video_width > 0 and self.video_height > 0:
            frame = cv2.resize(frame, (self.canvas_width, self.canvas_height))
        self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(self.frame)
        self.photo = ImageTk.PhotoImage(image=img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        self.draw_bounding_lines()

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        current_time = self.current_frame_index / fps if fps else 0
        self.update_time_display(current_time)

    def on_mouse_press(self, event):
        x = int(event.x * (self.video_width / self.canvas_width)) if self.canvas_width > 0 else event.x
        y = int(event.y * (self.video_height / self.canvas_height)) if self.canvas_height > 0 else event.y
        self.selected_line = self.get_clicked_line(x, y)

    def on_mouse_drag(self, event):
        x = int(event.x * (self.video_width / self.canvas_width)) if self.canvas_width > 0 else event.x
        y = int(event.y * (self.video_height / self.canvas_height)) if self.canvas_height > 0 else event.y

        if self.selected_line == "top":
            self.top_line_y = max(0, min(y, self.bottom_line_y))
        elif self.selected_line == "bottom":
            self.bottom_line_y = max(self.top_line_y, min(y, self.video_height))
        elif self.selected_line == "left":
            self.left_line_x = max(0, min(x, self.right_line_x))
        elif self.selected_line == "right":
            self.right_line_x = max(self.left_line_x, min(x, self.video_width))

        self.draw_bounding_lines()
        self.update_parameters()

    def on_mouse_release(self, _event):
        self.selected_line = None
        self.canvas.config(cursor="arrow")

    def on_mouse_move(self, event):
        x = int(event.x * (self.video_width / self.canvas_width)) if self.canvas_width > 0 else event.x
        y = int(event.y * (self.video_height / self.canvas_height)) if self.canvas_height > 0 else event.y

        line = self.get_clicked_line(x, y)
        if line in ("top", "bottom"):
            self.canvas.config(cursor="sb_v_double_arrow")
        elif line in ("left", "right"):
            self.canvas.config(cursor="sb_h_double_arrow")
        else:
            self.canvas.config(cursor="arrow")

    def get_clicked_line(self, x, y):
        tolerance = 5
        if abs(y - self.top_line_y) < tolerance:
            return "top"
        if abs(y - self.bottom_line_y) < tolerance:
            return "bottom"
        if abs(x - self.left_line_x) < tolerance:
            return "left"
        if abs(x - self.right_line_x) < tolerance:
            return "right"
        return None

    def update_parameters(self):
        if not self.video_width or not self.video_height:
            return

        top_crop = 1 - (self.top_line_y / self.video_height)
        bottom_crop = (self.video_height - self.bottom_line_y) / self.video_height
        left_crop = self.left_line_x / self.video_width
        right_crop = self.right_line_x / self.video_width

        self.top_var.set(f"{top_crop:.4f}")
        self.bottom_var.set(f"{bottom_crop:.4f}")
        self.left_var.set(f"{left_crop:.4f}")
        self.right_var.set(f"{right_crop:.4f}")

    def update_time_display(self, current_time):
        time_obj = datetime.datetime.min + datetime.timedelta(seconds=current_time)
        self.time_label.config(text=time_obj.strftime("%H:%M:%S.%f")[:-3])

    def draw_bounding_lines(self):
        if not self.video_width or not self.video_height:
            return

        canvas_top_y = int(self.top_line_y * (self.canvas_height / self.video_height)) if self.canvas_height else self.top_line_y
        canvas_bottom_y = int(self.bottom_line_y * (self.canvas_height / self.video_height)) if self.canvas_height else self.bottom_line_y
        canvas_left_x = int(self.left_line_x * (self.canvas_width / self.video_width)) if self.canvas_width else self.left_line_x
        canvas_right_x = int(self.right_line_x * (self.canvas_width / self.video_width)) if self.canvas_width else self.right_line_x

        self.canvas.delete("bounding_lines")
        self.canvas.create_line(0, canvas_top_y, self.canvas_width, canvas_top_y, fill="yellow", width=2, tags="bounding_lines")
        self.canvas.create_line(0, canvas_bottom_y, self.canvas_width, canvas_bottom_y, fill="yellow", width=2, tags="bounding_lines")
        self.canvas.create_line(canvas_left_x, 0, canvas_left_x, self.canvas_height, fill="yellow", width=2, tags="bounding_lines")
        self.canvas.create_line(canvas_right_x, 0, canvas_right_x, self.canvas_height, fill="yellow", width=2, tags="bounding_lines")

    def confirm_selection(self):
        top_crop = float(self.top_var.get())
        bottom_crop = float(self.bottom_var.get())
        left_crop = float(self.left_var.get())
        right_crop = float(self.right_var.get())

        self.update_crop_callback(top=top_crop, bottom=bottom_crop, left=left_crop, right=right_crop)

        if self.profile_getter() == "Tuỳ chỉnh":
            self.apply_video_callback(self.video_path)

        self.root.destroy()
