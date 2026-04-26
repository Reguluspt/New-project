from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


COMMON_SOFFICE_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def find_soffice_path() -> Path | None:
    which_result = shutil.which("soffice")
    if which_result:
        return Path(which_result)

    for path in COMMON_SOFFICE_PATHS:
        if path.exists():
            return path
    return None


def export_docx_to_pdf(docx_path: str | Path, *, soffice_path: str | Path | None = None) -> Path:
    source = Path(docx_path)
    if not source.exists():
        raise FileNotFoundError(source)

    binary = Path(soffice_path) if soffice_path else find_soffice_path()
    if binary is None or not binary.exists():
        raise FileNotFoundError("Khong tim thay soffice.exe de chuyen PDF.")

    output_dir = source.parent
    subprocess.run(
        [
            str(binary),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    pdf_path = output_dir / f"{source.stem}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    return pdf_path


def export_docx_set_to_pdf(paths: list[str | Path], *, soffice_path: str | Path | None = None) -> list[Path]:
    pdf_paths: list[Path] = []
    for path in paths:
        pdf_paths.append(export_docx_to_pdf(path, soffice_path=soffice_path))
    return pdf_paths
