"""Файловое хранилище за тонкой абстракцией.

Сейчас — локальная файловая система (docker volume). Замена на S3/MinIO,
когда появится объектное хранилище (открытый вопрос №6 контракта), — это
одна новая реализация тех же трёх функций, ключи file_key не меняются.
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO

STORAGE_ROOT = Path(os.getenv("FILE_STORAGE_ROOT", "/data/files"))

CHUNK_SIZE = 1024 * 1024


class LocalFileStorage:
    def __init__(self, root: Path | None = None):
        self.root = root or STORAGE_ROOT

    def save(self, source: BinaryIO, original_name: str) -> tuple[str, int]:
        """Сохраняет поток, возвращает (file_key, размер в байтах)."""
        ext = Path(original_name).suffix[:10]
        key = f"{uuid.uuid4().hex}{ext}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with open(path, "wb") as dst:
            while chunk := source.read(CHUNK_SIZE):
                dst.write(chunk)
                size += len(chunk)
        return key, size

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def _path(self, key: str) -> Path:
        # Ключ генерируется сервисом (hex uuid + расширение) — path traversal исключён,
        # но на всякий случай нормализуем
        safe = os.path.basename(key)
        return self.root / safe


storage = LocalFileStorage()
