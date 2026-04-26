from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.app_config import CASE_FILES_DIR
from src.case_packager import build_case_zip
from src.document_exporter import (
    compare_preview_with_export,
    export_individual_document_set,
    export_organization_document_set,
    preview_individual_document_set,
    preview_organization_document_set,
)
from src.pdf_exporter import export_docx_set_to_pdf
from src.template_manager import TEMPLATE_REQUIREMENTS, list_docx_templates, validate_template_placeholders


def collect_template_errors(directory: Path, customer_type: str) -> list[str]:
    errors: list[str] = []
    if not directory.exists():
        return [f"{directory}: thư mục template không tồn tại"]
    if not directory.is_dir():
        return [f"{directory}: đường dẫn không phải thư mục"]

    template_files = list_docx_templates(directory)
    required_template_names = sorted(TEMPLATE_REQUIREMENTS.get(customer_type, {}))
    if not template_files and not required_template_names:
        return [f"{directory}: không tìm thấy file .docx"]

    existing_names = {path.name.lower() for path in template_files}
    for template_name in required_template_names:
        if template_name.lower() not in existing_names:
            errors.append(f"{template_name}: thiếu file template bắt buộc")

    for path in template_files:
        validation = validate_template_placeholders(path, customer_type)
        if validation["missing"]:
            missing = ", ".join(f"{{{{{name}}}}}" for name in validation["missing"])
            errors.append(f"{path.name}: thiếu {missing}")
    return errors


def render_document_previews(previews: list[dict[str, str]], prefix: str) -> None:
    st.subheader("Xem trước nội dung đã render")
    for index, item in enumerate(previews, start=1):
        with st.expander(item["name"], expanded=index == 1):
            st.caption(item["template"])
            if item.get("html"):
                components.html(item["html"], height=720, scrolling=True)
            else:
                st.text_area(
                    f"Nội dung {item['name']}",
                    value=item["content"],
                    height=260,
                    key=f"{prefix}_{index}",
                )


def render_document_comparisons(comparisons: list[dict[str, object]], prefix: str) -> None:
    st.subheader("So sánh preview với file Word đã xuất")
    for index, item in enumerate(comparisons, start=1):
        with st.expander(str(item["name"]), expanded=index == 1):
            st.caption(str(item["output_path"]))
            if item["matched"]:
                st.success("Nội dung trùng khớp.")
            else:
                st.error(str(item["reason"]))
            left, right = st.columns(2)
            with left:
                st.text_area(
                    "Preview",
                    value=str(item["preview_content"]),
                    height=220,
                    key=f"{prefix}_preview_{index}",
                )
            with right:
                st.text_area(
                    "File đã xuất",
                    value=str(item["exported_content"]),
                    height=220,
                    key=f"{prefix}_exported_{index}",
                )


def document_action_error(
    *,
    case: dict[str, object] | None,
    expected_customer_type: str,
    actual_customer_type: str,
    template_errors: list[str],
    require_pdf: bool = False,
    soffice_path: str | Path | None = None,
) -> str | None:
    if not case:
        return "Không tìm thấy hồ sơ."
    if actual_customer_type != expected_customer_type:
        return "Hồ sơ này đang là khách hàng tổ chức." if expected_customer_type == "individual" else "Hồ sơ này đang là khách hàng cá nhân."
    if template_errors:
        return "Template đang thiếu placeholder bắt buộc."
    if require_pdf and not soffice_path:
        return "Không tìm thấy soffice.exe để xuất PDF."
    return None


def preview_case_documents(
    case: dict[str, object],
    *,
    customer_type: str,
    templates_dir: Path,
) -> list[dict[str, str]]:
    if customer_type == "individual":
        return preview_individual_document_set(case, templates_dir=templates_dir, case_files_dir=CASE_FILES_DIR)
    return preview_organization_document_set(case, templates_dir=templates_dir, case_files_dir=CASE_FILES_DIR)


def compare_case_documents(
    case: dict[str, object],
    *,
    customer_type: str,
    templates_dir: Path,
) -> list[dict[str, object]]:
    previews = preview_case_documents(case, customer_type=customer_type, templates_dir=templates_dir)
    return compare_preview_with_export(previews)


def export_case_documents(
    case: dict[str, object],
    *,
    customer_type: str,
    templates_dir: Path,
) -> list[Path]:
    if customer_type == "individual":
        return export_individual_document_set(case, templates_dir=templates_dir, case_files_dir=CASE_FILES_DIR)
    return export_organization_document_set(case, templates_dir=templates_dir, case_files_dir=CASE_FILES_DIR)


def approve_case_documents_pdf(
    case: dict[str, object],
    *,
    customer_type: str,
    templates_dir: Path,
    soffice_path: str | Path,
) -> tuple[list[Path], list[Path]]:
    word_paths = export_case_documents(case, customer_type=customer_type, templates_dir=templates_dir)
    pdf_paths = export_docx_set_to_pdf(word_paths, soffice_path=soffice_path)
    return word_paths, pdf_paths


def package_case_documents(case_folder: Path | None) -> Path:
    if case_folder is None:
        raise ValueError("Chưa có thư mục hồ sơ để đóng gói.")
    return build_case_zip(case_folder)
