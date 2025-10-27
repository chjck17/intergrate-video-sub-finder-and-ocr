"""Persistence helpers for application configuration."""

from __future__ import annotations

import configparser
from copy import deepcopy
from pathlib import Path
from typing import Dict, Tuple

from .constants import (
    DEFAULT_FOLDER_ID,
    DEFAULT_THREADS,
    DEFAULT_VIDEOSUBFINDER_PATH,
)

# Default crop profile definitions shared across the UI.
DEFAULT_CROP_PROFILES = {
    "vlxx, javhd": {"top": 0.1692, "bottom": 0.0058, "left": 0, "right": 1},
    "sextop": {"top": 0.3052, "bottom": 0.0545, "left": 0, "right": 1},
    "phimKK": {"top": 0.1861, "bottom": 0.0198, "left": 0, "right": 1},
    "titdam": {"top": 0.2455, "bottom": 0.0746, "left": 0.1743, "right": 0.8322},
    "tiktok": {"top": 0.45, "bottom": 0.05, "left": 0.0, "right": 1.0},
}


def _default_vsf_path() -> str:
    candidate = Path(DEFAULT_VIDEOSUBFINDER_PATH)
    return str(candidate) if candidate.exists() else ""


def load_config() -> Tuple[str, bool, bool, bool, str, int, Dict[str, Dict[str, float]]]:
    """Read persisted configuration values, falling back to sane defaults."""
    config = configparser.ConfigParser()
    config_path = Path("config.ini")
    if config_path.exists():
        config.read(config_path)

    if "settings" in config:
        folder_id = config["settings"].get("folder_id", DEFAULT_FOLDER_ID)
        delete_raw_texts = config.getboolean("settings", "delete_raw_texts", fallback=False)
        delete_texts = config.getboolean("settings", "delete_texts", fallback=False)
        nen_raw_texts = config.getboolean("settings", "nen_raw_texts", fallback=False)
        videosubfinder_path = config["settings"].get("videosubfinder_path", _default_vsf_path())
        threads = config["settings"].getint("threads", fallback=DEFAULT_THREADS)
    else:
        folder_id = DEFAULT_FOLDER_ID
        delete_raw_texts = False
        delete_texts = False
        nen_raw_texts = False
        videosubfinder_path = _default_vsf_path()
        threads = DEFAULT_THREADS

    if not videosubfinder_path:
        default_candidate = _default_vsf_path()
        if default_candidate:
            videosubfinder_path = default_candidate

    if threads <= 0:
        threads = DEFAULT_THREADS

    crop_profiles = deepcopy(DEFAULT_CROP_PROFILES)
    if "crop_profiles" in config:
        for profile_name, defaults in DEFAULT_CROP_PROFILES.items():
            profile_key = profile_name.replace(", ", "_").lower()
            section = config["crop_profiles"]
            crop_profiles[profile_name]["top"] = section.getfloat(f"{profile_key}_top", fallback=defaults["top"])
            crop_profiles[profile_name]["bottom"] = section.getfloat(
                f"{profile_key}_bottom", fallback=defaults["bottom"]
            )
            crop_profiles[profile_name]["left"] = section.getfloat(
                f"{profile_key}_left", fallback=defaults["left"]
            )
            crop_profiles[profile_name]["right"] = section.getfloat(
                f"{profile_key}_right", fallback=defaults["right"]
            )

    return (
        folder_id,
        delete_raw_texts,
        delete_texts,
        nen_raw_texts,
        videosubfinder_path,
        threads,
        crop_profiles,
    )


def save_config(
    folder_id: str,
    delete_raw_texts: bool,
    delete_texts: bool,
    nen_raw_texts: bool,
    videosubfinder_path: str,
    threads: int,
    crop_profiles: Dict[str, Dict[str, float]],
    custom_crop: Dict[str, float] | None = None,
) -> None:
    """Persist the current configuration to disk."""
    config = configparser.ConfigParser()
    config_path = Path("config.ini")
    if config_path.exists():
        config.read(config_path)

    if "settings" not in config:
        config["settings"] = {}

    config["settings"]["folder_id"] = folder_id
    config["settings"]["delete_raw_texts"] = str(delete_raw_texts)
    config["settings"]["delete_texts"] = str(delete_texts)
    config["settings"]["nen_raw_texts"] = str(nen_raw_texts)
    config["settings"]["videosubfinder_path"] = videosubfinder_path
    config["settings"]["threads"] = str(max(1, threads))

    if "crop_profiles" not in config:
        config["crop_profiles"] = {}

    for profile_name, values in crop_profiles.items():
        profile_key = profile_name.replace(", ", "_").lower()
        config["crop_profiles"][f"{profile_key}_top"] = str(values["top"])
        config["crop_profiles"][f"{profile_key}_bottom"] = str(values["bottom"])
        config["crop_profiles"][f"{profile_key}_left"] = str(values["left"])
        config["crop_profiles"][f"{profile_key}_right"] = str(values["right"])

    if custom_crop:
        config["crop_profiles"]["custom_top"] = str(custom_crop.get("top", 0))
        config["crop_profiles"]["custom_bottom"] = str(custom_crop.get("bottom", 0))
        config["crop_profiles"]["custom_left"] = str(custom_crop.get("left", 0))
        config["crop_profiles"]["custom_right"] = str(custom_crop.get("right", 0))

    with config_path.open("w") as configfile:
        config.write(configfile)
