import os
import sys
import shutil

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

ASSET_DIR = os.path.join(_get_base_dir(), "assets")
SUPPORTED_EXTS = {".gif", ".mp4", ".webm", ".mov", ".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class AssetManager:
    def __init__(self):
        os.makedirs(ASSET_DIR, exist_ok=True)

    def get_all(self):
        try:
            return [f for f in os.listdir(ASSET_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS]
        except Exception:
            return []

    def get_path(self, filename):
        return os.path.join(ASSET_DIR, filename) if filename else ""

    def exists(self, filename):
        return os.path.isfile(self.get_path(filename)) if filename else False

    def add(self, src_path):
        try:
            dest = os.path.join(ASSET_DIR, os.path.basename(src_path))
            shutil.copy2(src_path, dest)
            return True
        except Exception:
            return False

    def delete(self, filename):
        try:
            path = self.get_path(filename)
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False
