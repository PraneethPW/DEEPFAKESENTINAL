import re
import shutil
from pathlib import Path

from app.config import settings


class LocalStorageService:
    """Private local storage. Paths are never mounted as public static content."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_name(filename: str) -> str:
        base = Path(filename).name
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:180]
        return stem or "media.bin"

    def analysis_dir(self, user_id: str, analysis_id: str) -> Path:
        path = (self.root / user_id / analysis_id).resolve()
        if self.root not in path.parents:
            raise ValueError("unsafe storage path")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, user_id: str, analysis_id: str, name: str, content: bytes) -> Path:
        path = self.analysis_dir(user_id, analysis_id) / self.safe_name(name)
        path.write_bytes(content)
        return path

    def asset_path(self, user_id: str, analysis_id: str, relative_name: str) -> Path:
        base = self.analysis_dir(user_id, analysis_id)
        path = (base / relative_name).resolve()
        if base != path.parent and base not in path.parents:
            raise ValueError("unsafe asset path")
        return path

    def delete_analysis(self, user_id: str, analysis_id: str) -> None:
        path = (self.root / user_id / analysis_id).resolve()
        if self.root in path.parents and path.exists():
            shutil.rmtree(path)


storage = LocalStorageService()

