from pathlib import Path

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def get_upload_root() -> str:
    settings = get_settings()
    root = Path(settings.upload_root).expanduser() if settings.upload_root else BACKEND_ROOT / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return str(root.resolve())


def get_resume_dir() -> str:
    resume_dir = Path(get_upload_root()) / "resumes"
    resume_dir.mkdir(parents=True, exist_ok=True)
    return str(resume_dir.resolve())
