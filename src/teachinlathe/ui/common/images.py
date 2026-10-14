"""The shared images folder, for Python code that needs a path or a URL."""

import os

from PyQt6.QtCore import QUrl

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def image_path(name: str) -> str:
    return os.path.join(IMAGES_DIR, name)


def image_url(name: str) -> str:
    return QUrl.fromLocalFile(image_path(name)).toString()
