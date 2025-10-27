"""Integration with VideoSubFinder executable."""

from __future__ import annotations

import os
import re
import subprocess
import threading

from tkinter import messagebox

from . import monitor
from .logger import LOGGER


def build_command(
    vsf_path: str,
    video_file: str,
    output_folder: str,
    crop_top: float,
    crop_bottom: float,
    crop_left: float,
    crop_right: float,
    create_txtimages: bool,
):
    """Construct the VideoSubFinder command."""
    base_command = [
        vsf_path,
        "-c",
        "-r",
    ]
    if create_txtimages:
        base_command.append("-ccti")
    base_command.extend(
        [
            "-i",
            video_file,
            "-o",
            output_folder,
            "-te",
            str(crop_top),
            "-be",
            str(crop_bottom),
            "-le",
            str(crop_left),
            "-re",
            str(crop_right),
        ]
    )
    return base_command


def run_vsf(gui, command, output_base_path: str, output_folder_name: str):
    """Execute VideoSubFinder and update the UI/log accordingly."""

    def run_videosubfinder():
        try:
            LOGGER.log(f"🚀 Đang chạy lệnh VideoSubFinder: {' '.join(command)}")

            video_output_folder = output_base_path
            images_folder = os.path.join(video_output_folder, output_folder_name)
            rgb_images_folder = os.path.join(video_output_folder, "RGBImages")

            LOGGER.log(f"👀 Bắt đầu giám sát thư mục RGBImages tại: {rgb_images_folder}")
            threading.Thread(
                target=monitor.wait_for_rgbimages_and_monitor,
                args=(gui, rgb_images_folder, gui.duration or "00:00:00"),
                daemon=True,
            ).start()

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if not line:
                    continue
                line = line.strip()
                LOGGER.log(line)
                match = re.search(r"%(\d+)", line)
                if match:
                    try:
                        percentage = int(match.group(1))
                        gui.root.after(0, gui.progress_bar.config, {"value": percentage})
                    except ValueError:
                        LOGGER.log("Lỗi chuyển đổi phần trăm")

            stderr_output = process.stderr.read()
            if stderr_output:
                LOGGER.log(f"❌ Lỗi VideoSubFinder: {stderr_output}")
                gui.root.after(
                    0,
                    lambda: messagebox.showerror("Lỗi", f"Quá trình xử lý video thất bại: {stderr_output}"),
                )
                gui.root.after(0, gui.status_label.config, {"text": "❌ Lỗi!"})

            returncode = process.wait()

            if returncode != 0:
                LOGGER.log("✅ VideoSubFinder đã hoàn tất xử lý ảnh từ Video")
                gui.root.after(
                    0,
                    lambda: messagebox.showinfo("Thông báo", "VideoSubFinder đã hoàn tất xử lý ảnh từ Video"),
                )
                if monitor.STATE.event_handler:
                    total_images = monitor.STATE.event_handler.file_count
                    gui.root.after(
                        0,
                        gui.status_label.config,
                        {"text": f"Đã xử lý xong Video! | 📂 Tổng ảnh: {total_images}"},
                    )
            else:
                LOGGER.log("✅ Quá trình xử lý video đã hoàn tất.")
                gui.root.after(0, gui.status_label.config, {"text": "✅ Hoàn thành!"})

            if os.path.exists(images_folder):
                gui.root.after(0, lambda: gui.images_entry.delete(0, "end"))
                gui.root.after(0, lambda: gui.images_entry.insert(0, images_folder))
                gui.images_dirr = images_folder
                threading.Timer(
                    3.0, monitor.start_monitoring_rgbimages, args=[gui, rgb_images_folder, gui.duration or "00:00:00"]
                ).start()
            else:
                LOGGER.log("❌ Lỗi: Thư mục RGBImages không tồn tại.")
                gui.root.after(
                    0,
                    lambda: messagebox.showerror("Lỗi", "Thư mục RGBImages không tồn tại."),
                )
        except FileNotFoundError:
            LOGGER.log(f"❌ Lỗi: Không tìm thấy file: {command[0]}")
            gui.root.after(
                0,
                lambda: messagebox.showerror("Lỗi", f"Không tìm thấy VideoSubFinder tại: {command[0]}"),
            )
            gui.root.after(0, gui.status_label.config, {"text": "Lỗi!"})
        except Exception as exc:
            LOGGER.log(f"❌ Lỗi hệ thống:{exc}")
            gui.root.after(
                0,
                lambda: messagebox.showerror("Lỗi hệ thống", f"Không thể thực thi lệnh: {exc}"),
            )
            gui.root.after(0, gui.status_label.config, {"text": "Lỗi!"})
        finally:
            gui.root.after(0, gui.VSF_button.config, {"state": "normal"})
            gui.root.after(0, gui.start_button.config, {"state": "normal"})
            gui.root.after(0, gui.subtitle_button.config, {"state": "normal"})
            gui.root.after(0, gui.images_button.config, {"state": "normal"})

    threading.Thread(target=run_videosubfinder, daemon=True).start()
