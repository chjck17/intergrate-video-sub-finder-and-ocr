"""Watchdog-based monitor for the RGBImages directory."""

from __future__ import annotations

import datetime
import os
import re
import threading
import time
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .logger import LOGGER


class RGBImagesEventHandler(FileSystemEventHandler):
    """Track new RGB image exports and update the UI."""

    def __init__(self, gui, video_duration: str = "00:00:00"):
        super().__init__()
        self.gui = gui
        self.video_duration = video_duration
        self.file_count = 0
        try:
            hrs, mins, secs = map(int, video_duration.split(":"))
            self.video_duration_timedelta = datetime.timedelta(hours=hrs, minutes=mins, seconds=secs)
        except ValueError:
            LOGGER.log("Lỗi định dạng thời lượng video, sử dụng giá trị mặc định '00:00:00'")
            self.video_duration_timedelta = datetime.timedelta()

    def on_created(self, event):
        if event.is_directory:
            return

        file_name = os.path.basename(event.src_path)
        self.file_count += 1
        LOGGER.log(f"📂 RGBImages: {file_name}")

        match = re.search(r"(\d+)_(\d+)_(\d+)_(\d+)", file_name)
        if not match:
            return

        extracted_time = f"{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}"
        self.gui.extracted_time = extracted_time

        if self.video_duration_timedelta.total_seconds() <= 0:
            return

        try:
            extracted_time_obj = datetime.datetime.strptime(extracted_time, "%H:%M:%S:%f").time()
        except ValueError:
            LOGGER.log("Lỗi xử lý thời gian: Không thể chuyển đổi thời gian vừa trích xuất.")
            return

        extracted_timedelta = datetime.timedelta(
            hours=extracted_time_obj.hour,
            minutes=extracted_time_obj.minute,
            seconds=extracted_time_obj.second,
            microseconds=extracted_time_obj.microsecond,
        )

        time_remaining = self.video_duration_timedelta - extracted_timedelta
        time_remaining_str = str(time_remaining).split(".")[0]

        percentage_complete = 0
        if self.video_duration_timedelta.total_seconds():
            percentage_complete = (extracted_timedelta / self.video_duration_timedelta) * 100
            percentage_complete = max(0, min(percentage_complete, 100))

        status_text = (
            "VSF đang chạy...👀 "
            f"Còn lại: {time_remaining_str} |⏱ Tổng thời gian: {self.video_duration} |📂 Ảnh: {self.file_count}"
        )
        self.gui.status_label.config(text=status_text)
        self.gui.root.after(0, self.gui.progress_bar.config, {"value": percentage_complete})


class MonitorState:
    """Holds active observer references."""

    def __init__(self):
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[RGBImagesEventHandler] = None
        self.worker_threads: list[threading.Thread] = []

    def stop_all(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        self.observer = None
        self.event_handler = None
        self.worker_threads.clear()


STATE = MonitorState()


def start_monitoring_rgbimages(gui, rgb_images_folder: str, video_duration: str = "00:00:00"):
    """Start a watchdog observer for the RGBImages folder."""
    if not os.path.exists(rgb_images_folder):
        LOGGER.log("❌ Thư mục RGBImages chưa được tạo, không thể giám sát.")
        return

    if STATE.observer and STATE.observer.is_alive():
        return

    observer = Observer()
    handler = RGBImagesEventHandler(gui, video_duration)
    observer.schedule(handler, rgb_images_folder, recursive=True)

    observer_thread = threading.Thread(target=observer.start, daemon=True)
    STATE.worker_threads.append(observer_thread)
    STATE.observer = observer
    STATE.event_handler = handler
    observer_thread.start()


def wait_for_rgbimages_and_monitor(gui, path: str, video_duration: str, retries: int = 10, delay: int = 1):
    """Block until the RGBImages folder becomes available, then begin monitoring."""
    remaining = retries
    while remaining > 0:
        if os.path.exists(path):
            LOGGER.log(f"👀 Đã thấy thư mục: {path}.\n🚀 Bắt đầu giám sát!")
            start_monitoring_rgbimages(gui, path, video_duration)
            return
        LOGGER.log(f"⚠️ Không thấy RGBImages. Đang đợi... {remaining}s còn lại")
        time.sleep(delay)
        remaining -= 1

    LOGGER.log("❌ LỖI: Không thể tìm thấy thư mục RGBImages sau thời gian chờ.")
