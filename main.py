"""Bulb Flow — Free, open-source AI voice-typing and notetaker desktop application.

Supports:
  python main.py                        Launch Bulb Flow normally
  python main.py --screenshot out.png   Render ~120 frames unfocused, save PNG, and exit
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from bulb_flow.ui.main_window import BulbFlowMainWindow
from bulb_flow.win_integration import lower_window_without_activating


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulb Flow — Free Open-Source AI Voice Dictation")
    parser.add_argument(
        "--screenshot",
        metavar="FILE.PNG",
        default="",
        help="Start unfocused, draw ~120 frames, save window screenshot as PNG, and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    screenshot_path = args.screenshot.strip()
    is_screenshot = bool(screenshot_path)

    # High-DPI crisp scaling on Windows
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Bulb Flow")
    app.setOrganizationName("BulbFlowOpenSource")

    window = BulbFlowMainWindow(screenshot_mode=is_screenshot)

    if is_screenshot:
        window.show()
        # Keep unfocused and behind other windows on Windows so checks never interrupt the user
        lower_window_without_activating(int(window.winId()))

        frames = {"count": 0}
        target_frames = 120
        timer = QTimer()
        timer.setInterval(8)

        def _step() -> None:
            frames["count"] += 1
            window.repaint()
            if frames["count"] >= target_frames:
                timer.stop()
                out = Path(screenshot_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                pixmap = window.grab()
                pixmap.save(str(out), "PNG")
                app.quit()

        timer.timeout.connect(_step)
        timer.start()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
