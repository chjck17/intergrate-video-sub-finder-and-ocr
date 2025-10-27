"""Entry point for the OCR application."""

from __future__ import annotations

try:
    import argparse

    from oauth2client import tools

    FLAGS = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except Exception:
    FLAGS = None

from app.gui import OCRGui


def main():
    gui = OCRGui(FLAGS)
    gui.run()


if __name__ == "__main__":
    main()
