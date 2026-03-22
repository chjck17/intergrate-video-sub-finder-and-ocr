"""Tkinter UI wiring for the OCR application."""

from __future__ import annotations

import os
import signal
import sys
import threading
from pathlib import Path

import psutil
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk

from .config_manager import load_config, save_config
from .crop_selector import CropSelectorApp
from .logger import LOGGER
from . import monitor
from . import ocr
from . import video_utils
from . import vsf


class OCRGui:
    """Primary application window and event handlers."""

    def __init__(self, flags):
        self.flags = flags
        self.root = tk.Tk()
        self.root.title("SEGG OCR Tool v1.36_Optimizer")
        self.root.geometry("622x578")

        (
            self.folder_id,
            delete_raw_texts,
            delete_texts,
            nen_raw_texts,
            self.videosubfinder_path,
            self.threads,
            self.crop_profiles,
            self.subtitle_color,
        ) = load_config()

        self.duration = None
        self.images_dirr = ""

        self.delete_raw_texts_var = tk.BooleanVar(value=delete_raw_texts)
        self.delete_texts_var = tk.BooleanVar(value=delete_texts)
        self.nen_raw_texts_var = tk.BooleanVar(value=nen_raw_texts)
        self.create_txtimages_var = tk.BooleanVar(value=False)

        self.crop_top_var = tk.StringVar(value="0")
        self.crop_bottom_var = tk.StringVar(value="0")
        self.crop_left_var = tk.StringVar(value="0")
        self.crop_right_var = tk.StringVar(value="0")

        self._build_layout()
        LOGGER.configure(self.root, self.log_text)

        self.profile_combobox.set("Chọn profile")
        self.update_crop_values()
        self.toado_button.config(state=tk.DISABLED)

        LOGGER.log(
            "|====================CHÚ Ý QUAN TRỌNG====================|\n\n"
            "Vui lòng cấu hình trước API bằng tài khoản google của bạn.\n"
            "Sau đó tải credentials.json đặt cùng thư mục chương trình.\n\n"
            "|=====================================Discord: ePubc#9826|\n"
        )

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _build_layout(self):
        button_width = 20

        subtitle_frame = tk.Frame(self.root)
        subtitle_frame.pack(pady=5, fill="x")
        tk.Label(subtitle_frame, text="Tên file phụ đề:").pack(side="left", padx=5)
        self.subtitle_entry = tk.Entry(subtitle_frame, width=58)
        self.subtitle_entry.pack(side="left", padx=5)
        self.subtitle_button = tk.Button(
            subtitle_frame,
            text="📂 Chọn nơi lưu sub",
            width=button_width,
            command=self.choose_subtitle_file,
        )
        self.subtitle_button.pack(side="right", padx=5)

        images_frame = tk.Frame(self.root)
        images_frame.pack(pady=5, fill="x")
        tk.Label(images_frame, text="Thư mục ảnh:").pack(side="left", padx=5)
        self.images_entry = tk.Entry(images_frame, width=59)
        self.images_entry.pack(side="left", padx=5)
        self.images_button = tk.Button(
            images_frame,
            text="📂 Chọn thư mục ảnh",
            width=button_width,
            command=self.choose_images_directory,
        )
        self.images_button.pack(side="right", padx=5)

        video_frame = tk.Frame(self.root)
        video_frame.pack(pady=(0, 1), fill="x")
        tk.Label(video_frame, text="Tệp tin video:").pack(side="left", padx=5)
        self.entry_video = tk.Entry(video_frame, width=59)
        self.entry_video.pack(side="left", padx=5)

        self.toado_button = tk.Button(
            video_frame,
            text="✨ Toạ độ",
            width=8,
            command=self.choose_video_for_crop,
        )
        self.toado_button.pack(side="right", padx=5)

        self.VSF_button = tk.Button(
            video_frame,
            text="🚀 Chạy VSF",
            width=9,
            command=self.choose_video_file,
        )
        self.VSF_button.pack(side="right", padx=5)

        crop_frame = tk.Frame(self.root)
        crop_frame.pack(padx=10, pady=5, fill="x")
        tk.Label(crop_frame, text="Crop (Top, Bottom, Left, Right):").pack(side="left", padx=5)

        validate_command = (self.root.register(self.validate_float_input), "%d", "%P")

        self.entry_crop_top = tk.Entry(
            crop_frame,
            textvariable=self.crop_top_var,
            width=10,
            state="readonly",
            validate="key",
            validatecommand=validate_command,
        )
        self.entry_crop_top.pack(side="left", padx=2)

        self.entry_crop_bottom = tk.Entry(
            crop_frame,
            textvariable=self.crop_bottom_var,
            width=10,
            state="readonly",
            validate="key",
            validatecommand=validate_command,
        )
        self.entry_crop_bottom.pack(side="left", padx=2)

        self.entry_crop_left = tk.Entry(
            crop_frame,
            textvariable=self.crop_left_var,
            width=10,
            state="readonly",
            validate="key",
            validatecommand=validate_command,
        )
        self.entry_crop_left.pack(side="left", padx=2)

        self.entry_crop_right = tk.Entry(
            crop_frame,
            textvariable=self.crop_right_var,
            width=10,
            state="readonly",
            validate="key",
            validatecommand=validate_command,
        )
        self.entry_crop_right.pack(side="left", padx=2)

        self.profile_combobox = ttk.Combobox(
            crop_frame,
            values=["Chọn profile", "vlxx, javhd", "sextop", "phimKK", "titdam", "tiktok", "Tuỳ chỉnh"],
            state="readonly",
        )
        self.profile_combobox.pack(side="left", padx=5)
        self.profile_combobox.bind("<<ComboboxSelected>>", self.update_crop_values)

        delete_options_frame = tk.Frame(self.root)
        delete_options_frame.pack(pady=(0, 1), fill="x")

        tk.Checkbutton(
            delete_options_frame,
            text="Xóa folder raw_texts khi xong",
            variable=self.delete_raw_texts_var,
            anchor="w",
        ).pack(side="left", padx=5)

        tk.Checkbutton(
            delete_options_frame,
            text="Xóa folder texts khi xong",
            variable=self.delete_texts_var,
            anchor="w",
        ).pack(side="left", padx=5)

        tk.Checkbutton(
            delete_options_frame,
            text="Nén folder raw_texts",
            variable=self.nen_raw_texts_var,
            anchor="w",
        ).pack(side="left", padx=5)

        tk.Checkbutton(
            delete_options_frame,
            text="Tạo TXTImages",
            variable=self.create_txtimages_var,
            anchor="w",
        ).pack(side="left", padx=5)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=(0, 2), fill="x")

        self.start_button = tk.Button(
            button_frame,
            text="🎬 Bắt đầu OCR",
            width=12,
            command=self.on_start_button_click,
            bg="#F50398",
        )
        self.start_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(
            button_frame,
            text="❌ Dừng OCR",
            width=11,
            command=lambda: ocr.stop_processing(self),
            state=tk.DISABLED,
        )
        self.stop_button.pack(side="left", padx=2)

        self.status_label = tk.Label(button_frame, text="Trạng thái chương trình: Sẵn sàng", fg="red")
        self.status_label.pack(side="right", padx=2)

        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=612, mode="determinate")
        self.progress_bar.pack(pady=(1, 0))

        color_frame = tk.Frame(self.root)
        color_frame.pack(padx=10, pady=(0, 5), fill="x")
        tk.Label(color_frame, text="Subtitle color (RGB)").pack(side="left", padx=5)
        self.color_preview = tk.Label(color_frame, width=10, relief="sunken")
        self.color_preview.pack(side="left", padx=5)
        self.color_value_label = tk.Label(color_frame, text="Not set")
        self.color_value_label.pack(side="left", padx=5)
        tk.Button(color_frame, text="Pick subtitle color", command=self.choose_subtitle_color).pack(side="right", padx=5)

        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=(0, 5), fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=5, wrap="word", state="disabled", bg="#0C0C0C", fg="#CCCCCC")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self._update_color_preview()

    def validate_float_input(self, action, value):
        if action != "1":
            return True
        return value.replace(".", "", 1).isdigit()

    def set_entries_state(self, state):
        self.entry_crop_top.config(state=state)
        self.entry_crop_bottom.config(state=state)
        self.entry_crop_left.config(state=state)
        self.entry_crop_right.config(state=state)

    def update_crop_values(self, event=None, top=None, bottom=None, left=None, right=None):
        if top is not None:
            self.crop_top_var.set(f"{top:.4f}")
        if bottom is not None:
            self.crop_bottom_var.set(f"{bottom:.4f}")
        if left is not None:
            self.crop_left_var.set(f"{left:.4f}")
        if right is not None:
            self.crop_right_var.set(f"{right:.4f}")

        selected_profile = self.profile_combobox.get()
        if selected_profile in self.crop_profiles:
            profile = self.crop_profiles[selected_profile]
            self.crop_top_var.set(f"{profile['top']:.4f}")
            self.crop_bottom_var.set(f"{profile['bottom']:.4f}")
            self.crop_left_var.set(f"{profile['left']:.4f}")
            self.crop_right_var.set(f"{profile['right']:.4f}")
            self.set_entries_state("readonly")
            self.toado_button.config(state=tk.DISABLED)
            self.VSF_button.config(state=tk.NORMAL)
        elif selected_profile == "Tuỳ chỉnh":
            self.set_entries_state("normal")
            self.toado_button.config(state=tk.NORMAL)
            self.VSF_button.config(state=tk.DISABLED if not self.entry_video.get() else tk.NORMAL)
        else:
            self.set_entries_state("readonly")

    def choose_images_directory(self):
        images_dirr = filedialog.askdirectory(title="Chọn thư mục chứa hình ảnh")
        if images_dirr:
            self.images_entry.delete(0, tk.END)
            self.images_entry.insert(0, images_dirr)
            LOGGER.log(f"✅ Đường dẫn thư mục đã chọn: {images_dirr}")
        else:
            LOGGER.log("⚠️ Không có thư mục nào được chọn.")

    def choose_subtitle_file(self):
        subtitle_file = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt")],
            title="Lưu file phụ đề",
        )
        if subtitle_file:
            self.subtitle_entry.delete(0, tk.END)
            self.subtitle_entry.insert(0, subtitle_file)
            LOGGER.log(f"✅ Nơi lưu phụ đề: {subtitle_file}")
        else:
            LOGGER.log("⚠️ BẮT BUỘC PHẢI CHỌN LƯU PHỤ ĐỀ.")

    def _get_custom_crop(self):
        try:
            return {
                "top": float(self.crop_top_var.get()),
                "bottom": float(self.crop_bottom_var.get()),
                "left": float(self.crop_left_var.get()),
                "right": float(self.crop_right_var.get()),
            }
        except ValueError:
            return None

    def _rgb_to_hex(self, color):
        if not color:
            return "#000000"
        return "#{:02X}{:02X}{:02X}".format(*color)

    def _update_color_preview(self):
        if self.subtitle_color:
            hex_value = self._rgb_to_hex(self.subtitle_color)
            self.color_preview.config(bg=hex_value)
            self.color_value_label.config(text=f"{self.subtitle_color}")
        else:
            self.color_preview.config(bg=self.root.cget("bg"))
            self.color_value_label.config(text="Not set")

    def _persist_config(self, custom_crop=None):
        save_config(
            self.folder_id,
            self.delete_raw_texts_var.get(),
            self.delete_texts_var.get(),
            self.nen_raw_texts_var.get(),
            self.videosubfinder_path,
            self.threads,
            self.crop_profiles,
            custom_crop=custom_crop,
            subtitle_color=self.subtitle_color,
        )

    def choose_subtitle_color(self):
        initial = self.subtitle_color if self.subtitle_color else (255, 255, 255)
        color_tuple = colorchooser.askcolor(color=initial, title="Select subtitle color")
        if not color_tuple or not color_tuple[0]:
            return
        r, g, b = map(int, color_tuple[0])
        self.subtitle_color = (r, g, b)
        self._update_color_preview()
        self._persist_config(self._get_custom_crop())
        LOGGER.log(f"Picked subtitle color: {self.subtitle_color}")

    def on_start_button_click(self):
        file_sub = self.subtitle_entry.get()
        images_dirr = self.images_entry.get()

        if not file_sub or not images_dirr:
            LOGGER.log("⚠️ Vui lòng nhập đầy đủ thông tin...")
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin.")
            return

        custom_crop = self._get_custom_crop()
        self._persist_config(custom_crop)

        log_file_path = file_sub if file_sub.endswith(".srt") else f"{file_sub}.srt"
        log_file_path = log_file_path.replace(".srt", ".log")
        LOGGER.set_log_file(log_file_path)

        LOGGER.log("🎬 Bắt đầu quá trình xử lý...")

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.VSF_button.config(state=tk.DISABLED)
        self.subtitle_button.config(state=tk.DISABLED)
        self.images_button.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0

        threading.Thread(
            target=ocr.start_processing,
            args=(
                self,
                file_sub,
                images_dirr,
                self.delete_raw_texts_var.get(),
                self.delete_texts_var.get(),
                self.nen_raw_texts_var.get(),
                self.flags,
            ),
            daemon=True,
        ).start()

    def choose_video_file(self):
        selected_profile = self.profile_combobox.get()
        video_file = None

        if selected_profile != "Tuỳ chỉnh" or not self.entry_video.get():
            video_file = filedialog.askopenfilename(
                filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")],
                title="Chọn video để xử lý",
            )
            if not video_file:
                LOGGER.log("⚠️ Không có video nào được chọn.")
                return
            self.entry_video.delete(0, tk.END)
            self.entry_video.insert(0, video_file)
        else:
            video_file = self.entry_video.get()

        LOGGER.log(f"✅ Đã chọn video: {video_file}")

        self.duration = video_utils.get_video_duration_opencv(video_file)
        if self.duration:
            self.status_label.config(text=f"⏳ Thời lượng Video: | {self.duration}")
        else:
            self.status_label.config(text="⏳ Đang xử lý")

        subtitle_file = Path(video_file).with_suffix(".srt")
        self.subtitle_entry.delete(0, tk.END)
        self.subtitle_entry.insert(0, str(subtitle_file))

        try:
            crop_left = float(self.entry_crop_left.get())
            crop_right = float(self.entry_crop_right.get())
            crop_top = float(self.entry_crop_top.get())
            crop_bottom = float(self.entry_crop_bottom.get())
        except ValueError:
            LOGGER.log("❌ Lỗi nhập liệu: Vui lòng nhập đúng giá trị số cho các tham số crop.")
            messagebox.showerror("Lỗi nhập liệu", "Vui lòng nhập đúng giá trị số cho các tham số crop.")
            return

        if not os.path.exists(self.videosubfinder_path):
            LOGGER.log(f"❌ Lỗi: Không tìm thấy VideoSubFinder tại: {self.videosubfinder_path}")
            messagebox.showerror("Lỗi", f"Không tìm thấy VideoSubFinder tại: {self.videosubfinder_path}")
            return

        output_base = str(Path(video_file).with_suffix("")) + "_out"
        output_folder = "TXTImages" if self.create_txtimages_var.get() else "RGBImages"

        command = vsf.build_command(
            self.videosubfinder_path,
            video_file,
            output_base,
            crop_top,
            crop_bottom,
            crop_left,
            crop_right,
            self.create_txtimages_var.get(),
        )

        self.VSF_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.subtitle_button.config(state=tk.DISABLED)
        self.images_button.config(state=tk.DISABLED)

        vsf.run_vsf(self, command, output_base, output_folder)

    def _apply_video_after_crop(self, video_path: str):
        self.entry_video.delete(0, tk.END)
        self.entry_video.insert(0, video_path)
        self.profile_combobox.set("Tuỳ chỉnh")
        self.update_crop_values()
        self.choose_video_file()

    def choose_video_for_crop(self):
        video_file = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")],
            title="Chọn video để chọn tọa độ",
        )
        if not video_file:
            return

        self.profile_combobox.set("Tuỳ chỉnh")
        self.update_crop_values()

        crop_window = tk.Toplevel(self.root)
        CropSelectorApp(
            crop_window,
            video_file,
            self.update_crop_values,
            self.profile_combobox.get,
            self._apply_video_after_crop,
        )

        crop_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - crop_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - crop_window.winfo_height()) // 2
        crop_window.geometry(f"+{x}+{y}")
        crop_window.attributes("-topmost", True)
        self.root.wait_window(crop_window)

    def on_exit(self):
        if not messagebox.askokcancel("Xác nhận thoát", "Bạn có chắc chắn muốn thoát chương trình?"):
            return

        LOGGER.log("✅ Chương trình đã được đóng.")

        monitor.STATE.stop_all()

        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "VideoSubFinderWXW_intel.exe" in process.info["name"]:
                try:
                    LOGGER.log("⚠️ Đang đóng VideoSubFinderWXW_intel.exe...")
                    os.kill(process.info["pid"], signal.SIGTERM)
                    LOGGER.log("✅ Đã đóng VideoSubFinderWXW_intel.exe thành công!")
                except Exception as exc:
                    LOGGER.log(f"❌ Lỗi khi đóng VideoSubFinderWXW_intel.exe: {exc}")

        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()
