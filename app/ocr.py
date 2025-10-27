"""OCR pipeline powered by Google Drive conversions."""

from __future__ import annotations

import concurrent.futures
import datetime
import io
import os
import shutil
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext

import httplib2
from apiclient import discovery
from apiclient.http import MediaFileUpload, MediaIoBaseDownload

from . import auth
from .config_manager import load_config
from .logger import LOGGER

SRT_FILE_LIST: dict[int, list[str]] = {}
PROGRESS_LOCK = threading.Lock()
STOP_FLAG = False
TOTAL_IMAGES = 0
COMPLETED_SCANS = 0
START_TIME = 0.0


def reset_state():
    """Restore globals to default values before a new OCR run."""
    global SRT_FILE_LIST, STOP_FLAG, TOTAL_IMAGES, COMPLETED_SCANS, START_TIME
    SRT_FILE_LIST = {}
    STOP_FLAG = False
    TOTAL_IMAGES = 0
    COMPLETED_SCANS = 0
    START_TIME = 0.0


def request_stop():
    """Signal all workers to stop gracefully."""
    global STOP_FLAG
    STOP_FLAG = True


def stop_processing(gui):
    """Stop the OCR process and reset UI controls."""
    request_stop()
    gui.start_button.config(state=tk.NORMAL)
    gui.stop_button.config(state=tk.DISABLED)
    gui.VSF_button.config(state=tk.NORMAL)
    LOGGER.log("Quá trình đã được dừng.")


def _progress_callback(gui):
    """Update the progress bar and label safely from worker threads."""
    if TOTAL_IMAGES == 0:
        return
    gui.progress_bar["value"] = (COMPLETED_SCANS / TOTAL_IMAGES) * 100
    gui.status_label.config(text=f"✅ Đã OCR: {COMPLETED_SCANS}/{TOTAL_IMAGES}")
    gui.root.update_idletasks()


def ocr_image(gui, image_path, line, credentials, folder_id, current_directory):
    """Perform OCR on a single image via Google Drive conversion."""
    global STOP_FLAG
    tries = 0

    while True:
        if STOP_FLAG:
            LOGGER.log("❌ Quá trình đã được dừng.")
            return

        try:
            http = credentials.authorize(httplib2.Http())
            service = discovery.build("drive", "v3", http=http)
            imgfile = str(image_path.absolute())
            imgname = str(image_path.name)
            raw_txtfile = current_directory / "raw_texts" / f"{imgname[:-5]}.txt"
            txtfile = current_directory / "texts" / f"{imgname[:-5]}.txt"

            mime = "application/vnd.google-apps.document"
            res = (
                service.files()
                .create(
                    body={"name": imgname, "mimeType": mime, "parents": [folder_id]},
                    media_body=MediaFileUpload(imgfile, mimetype=mime, resumable=True),
                )
                .execute()
            )

            downloader = MediaIoBaseDownload(
                io.FileIO(raw_txtfile, "wb"),
                service.files().export_media(fileId=res["id"], mimeType="text/plain"),
            )
            done = False
            while not done:
                _, done = downloader.next_chunk()

            service.files().delete(fileId=res["id"]).execute()

            with open(raw_txtfile, "r", encoding="utf-8") as raw_text_file:
                text_content = raw_text_file.read()
            text_content = "".join(text_content.split("\n")[2:])

            preview_text = text_content[:55] + "..." if len(text_content) > 55 else text_content
            LOGGER.log(f"✅ Đã OCR: {preview_text}")

            with open(txtfile, "w", encoding="utf-8") as text_file:
                text_file.write(text_content)

            try:
                start_parts = imgname.split("_")
                end_parts = imgname.split("__")[1].split("_")

                start_time = f"{start_parts[0][:2]}:{start_parts[1][:2]}:{start_parts[2][:2]},{start_parts[3][:3]}"
                end_time = f"{end_parts[0][:2]}:{end_parts[1][:2]}:{end_parts[2][:2]},{end_parts[3][:3]}"
            except (IndexError, ValueError):
                LOGGER.log(
                    f"Error processing {imgname}: Filename format is incorrect. Please ensure the correct format is used."
                )
                return

            SRT_FILE_LIST[line] = [
                f"{line}\n",
                f"{start_time} --> {end_time}\n",
                f"{text_content}\n\n",
                "",
            ]

            break
        except Exception as exc:
            tries += 1
            if tries > 5:
                LOGGER.log(f"Lỗi sau 5 lần thử: {exc}")
                raise
            time.sleep(1)
            continue


def preview_srt(gui, srt_content, save_callback):
    """Show a modal window to preview and optionally edit SRT content."""
    if gui.root.state() == "iconic":
        gui.root.deiconify()

    preview_window = tk.Toplevel(gui.root)
    preview_window.title("Xem trước phụ đề SRT")
    preview_window.geometry("600x400")
    preview_window.transient(gui.root)
    preview_window.grab_set()

    srt_text = scrolledtext.ScrolledText(preview_window, wrap="word", height=20, width=70)
    srt_text.pack(padx=5, pady=5, fill="both", expand=True)
    srt_text.insert("end", srt_content)
    srt_text.config(state="normal")

    button_frame = tk.Frame(preview_window)
    button_frame.pack(pady=10)

    tk.Button(
        button_frame,
        text="Cập nhật và Đóng",
        command=lambda: [save_callback(srt_text.get("1.0", "end")), preview_window.destroy()],
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        button_frame,
        text="Hủy",
        command=lambda: [save_callback(srt_content), preview_window.destroy()],
    ).pack(side=tk.LEFT, padx=5)

    preview_window.update_idletasks()
    x = gui.root.winfo_x() + (gui.root.winfo_width() - preview_window.winfo_width()) // 2
    y = gui.root.winfo_y() + (gui.root.winfo_height() - preview_window.winfo_height()) // 2
    preview_window.geometry(f"+{x}+{y}")
    preview_window.attributes("-topmost", True)
    preview_window.focus_set()


def finalize_processing(
    gui,
    subtitle_path: Path,
    delete_raw_texts: bool,
    delete_texts: bool,
    nen_raw_texts: bool,
    raw_texts_dir: Path,
    texts_dir: Path,
):
    """Handle clean-up tasks after OCR completes."""
    if nen_raw_texts:
        try:
            zip_file_path = shutil.make_archive(str(subtitle_path), "zip", str(raw_texts_dir))
            new_zip_file_path = zip_file_path.replace(".srt.zip", ".zip")
            os.rename(zip_file_path, new_zip_file_path)
            LOGGER.log(f"✅ Đã nén thư mục: {raw_texts_dir}")
        except Exception as exc:
            LOGGER.log(f"❌ Lỗi khi nén thư mục {raw_texts_dir}: {exc}")
            messagebox.showerror("Lỗi", f"Không thể nén thư mục {raw_texts_dir}: {exc}")

    if delete_raw_texts:
        try:
            shutil.rmtree(raw_texts_dir)
            LOGGER.log(f"✅ Đã xóa thư mục: {raw_texts_dir}")
        except Exception as exc:
            LOGGER.log(f"❌ Lỗi: {exc}")
            messagebox.showerror("Lỗi", f"Không thể xóa thư mục raw_texts: {exc}")

    if delete_texts:
        try:
            shutil.rmtree(texts_dir)
            LOGGER.log(f"✅ Đã xóa thư mục: {texts_dir}")
        except Exception as exc:
            LOGGER.log(f"❌ Lỗi: {exc}")
            messagebox.showerror("Lỗi", f"Không thể xóa thư mục texts: {exc}")

    total_time = time.time() - START_TIME
    formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_time))

    gui.status_label.config(text=f"✅ Hoàn thành OCR {TOTAL_IMAGES} ảnh. Tổng thời gian: {formatted_time}")
    gui.start_button.config(state=tk.NORMAL)
    gui.VSF_button.config(state=tk.NORMAL)
    gui.stop_button.config(state=tk.DISABLED)
    gui.subtitle_button.config(state=tk.NORMAL)
    gui.images_button.config(state=tk.NORMAL)
    LOGGER.log(f"✅ Hoàn thành OCR {TOTAL_IMAGES} hình ảnh.")
    LOGGER.log(f"✅ Thời gian xử lý OCR: {formatted_time}")


def start_processing(
    gui,
    file_sub: str,
    images_dirr: str,
    delete_raw_texts: bool,
    delete_texts: bool,
    nen_raw_texts: bool,
    flags,
):
    """Main OCR orchestrator."""
    global TOTAL_IMAGES, COMPLETED_SCANS, START_TIME, STOP_FLAG

    reset_state()
    START_TIME = time.time()

    (
        _,
        _delete_raw_texts,
        _delete_texts,
        _nen_raw_texts,
        _,
        threads,
        _,
    ) = load_config()

    credentials = auth.get_credentials(flags)

    current_directory = Path(Path.cwd())
    images_dir = Path(images_dirr)
    raw_texts_dir = current_directory / "raw_texts"
    texts_dir = current_directory / "texts"

    subtitle_path = Path(file_sub)
    if subtitle_path.suffix != ".srt":
        subtitle_path = subtitle_path.with_suffix(".srt")

    try:
        if not images_dir.exists():
            LOGGER.log(f"❌ Lỗi: Thư mục {images_dir} không tồn tại.")
            messagebox.showerror(
                "Lỗi",
                f"Thư mục hình ảnh '{images_dirr}' không tồn tại.\nVui lòng kiểm tra lại đường dẫn.",
            )
            return

        raw_texts_dir.mkdir(exist_ok=True)
        texts_dir.mkdir(exist_ok=True)

        images = []
        for extension in ("*.jpeg", "*.jpg", "*.png", "*.bmp", "*.gif"):
            images.extend(Path(images_dirr).rglob(extension))

        TOTAL_IMAGES = len(images)
        LOGGER.log(f"|| Số luồng xử lý cùng lúc: {threads}")
        LOGGER.log(f"👀 Tổng số ảnh tìm thấy trong thư mục '{images_dirr}': {TOTAL_IMAGES}")

        if TOTAL_IMAGES == 0:
            messagebox.showerror(
                "Lỗi",
                f"Thư mục '{images_dirr}' không chứa hình ảnh hợp lệ.\n"
                "Hãy kiểm tra định dạng: JPEG, PNG, BMP, GIF.",
            )
            LOGGER.log(f"❌ Lỗi: Thư mục '{images_dirr}' không chứa hình ảnh hợp lệ.")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_image = {
                executor.submit(
                    ocr_image,
                    gui,
                    image,
                    index + 1,
                    credentials,
                    gui.folder_id,
                    current_directory,
                ): image
                for index, image in enumerate(images)
            }

            for future in concurrent.futures.as_completed(future_to_image):
                if STOP_FLAG:
                    break
                try:
                    future.result()
                except Exception as exc:
                    LOGGER.log(f"{future_to_image[future]} generated an exception: {exc}")
                else:
                    with PROGRESS_LOCK:
                        global COMPLETED_SCANS
                        COMPLETED_SCANS += 1
                        _progress_callback(gui)

        if STOP_FLAG:
            LOGGER.log("✅ Quá trình đã được dừng.")
            messagebox.showinfo("Dừng", "Quá trình đã dừng lại.")
            return

        srt_content = ""
        for i in sorted(SRT_FILE_LIST):
            srt_content += "".join(SRT_FILE_LIST[i])

        def save_srt_content(content):
            try:
                with open(subtitle_path, "w", encoding="utf-8") as srt_file:
                    srt_file.write(content)
                LOGGER.log(f"✅ Đã lưu file SRT: {subtitle_path}")
            except Exception as exc:
                LOGGER.log(f"❌ Lỗi khi lưu file SRT: {exc}")
                messagebox.showerror("Lỗi", f"Không thể lưu file SRT: {exc}")
            finally:
                finalize_processing(
                    gui,
                    subtitle_path,
                    delete_raw_texts,
                    delete_texts,
                    nen_raw_texts,
                    raw_texts_dir,
                    texts_dir,
                )

        preview_srt(gui, srt_content, save_srt_content)

    except Exception as exc:
        LOGGER.log(f"❌ Lỗi trong quá trình xử lý: {exc}")
        messagebox.showerror("Lỗi", f"Xảy ra lỗi trong quá trình xử lý: {exc}")
        finalize_processing(
            gui,
            subtitle_path,
            delete_raw_texts,
            delete_texts,
            nen_raw_texts,
            raw_texts_dir,
            texts_dir,
        )
