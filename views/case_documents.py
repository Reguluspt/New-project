from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.case_exports import (
    approve_case_documents_pdf,
    collect_template_errors,
    compare_case_documents,
    document_action_error,
    export_case_documents,
    package_case_documents,
    preview_case_documents,
    render_document_comparisons,
    render_document_previews,
)
from src.pdf_exporter import find_soffice_path


def render(
    *,
    selected_id: int,
    case: dict[str, object],
    refreshed_case: dict[str, object] | None,
    effective_case_folder: Path | None,
    individual_templates_dir: Path,
    organization_templates_dir: Path,
) -> None:
    st.subheader("Xuất bộ hồ sơ")
    st.caption(f"Thư mục hồ sơ: {effective_case_folder or 'Chưa tạo'}")
    if case.get("original_file_path"):
        st.caption(f"File GCN gốc: {case.get('original_file_path')}")

    customer_type_value = (refreshed_case.get("customer_type") or "individual") if refreshed_case else "individual"
    individual_template_errors = collect_template_errors(individual_templates_dir, "individual")
    organization_template_errors = collect_template_errors(organization_templates_dir, "organization")
    soffice_path = find_soffice_path()
    st.caption(f"Công cụ PDF: {soffice_path if soffice_path else 'Chưa tìm thấy soffice.exe'}")

    col1, col2 = st.columns(2)
    with col1:
        preview_individual_clicked = st.button("Xem trước bộ cá nhân", width="stretch")
        compare_individual_clicked = st.button("So sánh preview/file Word cá nhân", width="stretch")
        export_individual_clicked = st.button("Xuất HĐ + PYC + BBNT cá nhân", width="stretch")
        approve_individual_pdf_clicked = st.button(
            "Duyệt và xuất PDF cá nhân",
            width="stretch",
        )
    with col2:
        preview_organization_clicked = st.button("Xem trước bộ tổ chức", width="stretch")
        compare_organization_clicked = st.button("So sánh preview/file Word tổ chức", width="stretch")
        export_organization_clicked = st.button("Xuất bộ hồ sơ tổ chức", width="stretch")
        approve_organization_pdf_clicked = st.button(
            "Duyệt và xuất PDF tổ chức",
            width="stretch",
        )
    package_clicked = st.button("Đóng gói ZIP hồ sơ", width="stretch")

    if preview_individual_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        else:
            try:
                previews = preview_case_documents(refreshed_case, customer_type="individual", templates_dir=individual_templates_dir)
                render_document_previews(previews, f"individual_preview_{selected_id}")
            except Exception as exc:
                st.error(f"Xem trước thất bại: {exc}")

    if compare_individual_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        else:
            try:
                comparisons = compare_case_documents(refreshed_case, customer_type="individual", templates_dir=individual_templates_dir)
                render_document_comparisons(comparisons, f"individual_compare_{selected_id}")
            except Exception as exc:
                st.error(f"So sánh thất bại: {exc}")

    if export_individual_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        else:
            try:
                paths = export_case_documents(refreshed_case, customer_type="individual", templates_dir=individual_templates_dir)
                st.success("Đã xuất bộ hồ sơ cá nhân.")
                for path in paths:
                    st.caption(str(path))
            except Exception as exc:
                st.error(f"Xuất hồ sơ thất bại: {exc}")

    if approve_individual_pdf_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="individual",
            actual_customer_type=customer_type_value,
            template_errors=individual_template_errors,
            require_pdf=True,
            soffice_path=soffice_path,
        )
        if error:
            st.error(error)
            for item in individual_template_errors:
                st.caption(item)
        else:
            try:
                word_paths, pdf_paths = approve_case_documents_pdf(
                    refreshed_case,
                    customer_type="individual",
                    templates_dir=individual_templates_dir,
                    soffice_path=soffice_path,
                )
                st.success("Đã duyệt bộ cá nhân và xuất PDF.")
                for path in word_paths + pdf_paths:
                    st.caption(str(path))
            except Exception as exc:
                st.error(f"Duyệt và xuất PDF thất bại: {exc}")

    if preview_organization_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        else:
            try:
                previews = preview_case_documents(refreshed_case, customer_type="organization", templates_dir=organization_templates_dir)
                render_document_previews(previews, f"organization_preview_{selected_id}")
            except Exception as exc:
                st.error(f"Xem trước thất bại: {exc}")

    if compare_organization_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        else:
            try:
                comparisons = compare_case_documents(refreshed_case, customer_type="organization", templates_dir=organization_templates_dir)
                render_document_comparisons(comparisons, f"organization_compare_{selected_id}")
            except Exception as exc:
                st.error(f"So sánh thất bại: {exc}")

    if export_organization_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        else:
            try:
                paths = export_case_documents(refreshed_case, customer_type="organization", templates_dir=organization_templates_dir)
                st.success("Đã xuất bộ hồ sơ tổ chức.")
                for path in paths:
                    st.caption(str(path))
            except Exception as exc:
                st.error(f"Xuất hồ sơ tổ chức thất bại: {exc}")

    if approve_organization_pdf_clicked:
        error = document_action_error(
            case=refreshed_case,
            expected_customer_type="organization",
            actual_customer_type=customer_type_value,
            template_errors=organization_template_errors,
            require_pdf=True,
            soffice_path=soffice_path,
        )
        if error:
            st.error(error)
            for item in organization_template_errors:
                st.caption(item)
        else:
            try:
                word_paths, pdf_paths = approve_case_documents_pdf(
                    refreshed_case,
                    customer_type="organization",
                    templates_dir=organization_templates_dir,
                    soffice_path=soffice_path,
                )
                st.success("Đã duyệt bộ tổ chức và xuất PDF.")
                for path in word_paths + pdf_paths:
                    st.caption(str(path))
            except Exception as exc:
                st.error(f"Duyệt và xuất PDF thất bại: {exc}")

    if package_clicked:
        if not refreshed_case:
            st.error("Không tìm thấy hồ sơ để đóng gói.")
        else:
            try:
                archive_path = package_case_documents(effective_case_folder)
                st.success("Đã tạo gói ZIP hồ sơ.")
                st.caption(str(archive_path))
            except Exception as exc:
                st.error(f"Đóng gói ZIP thất bại: {exc}")
