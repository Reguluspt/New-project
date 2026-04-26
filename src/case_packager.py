from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build_case_zip(case_folder: str | Path, *, zip_name: str | None = None) -> Path:
    root = Path(case_folder)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(root)

    package_dir = root / "package"
    package_dir.mkdir(parents=True, exist_ok=True)
    archive_name = zip_name or f"{root.name}_full_package.zip"
    archive_path = package_dir / archive_name

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as handle:
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            if package_dir in file_path.parents:
                continue
            handle.write(file_path, arcname=str(file_path.relative_to(root)))

    return archive_path
