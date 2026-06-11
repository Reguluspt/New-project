from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.app_config import (
    ROOT,
    adjust_manual_rotation,
    ensure_uploaded_file_saved,
    get_auto_rotation,
    get_manual_rotation,
    is_rotation_locked,
    refresh_auto_rotation,
    reset_manual_rotation,
    select_pdf_preview_page,
    set_rotation_lock,
)
from src.preview import get_pdf_metadata, normalize_image_for_preview, pdf_page_count, pdf_page_png, pdf_thumbnail_png


def get_preview_context(uploaded_file) -> tuple[Path | None, bool]:
    preview_path: Path | None = None
    using_sample = False
    if uploaded_file is None:
        sample_pdf = ROOT / "samples" / "gcn.pdf"
        if sample_pdf.exists():
            using_sample = True
            preview_path = sample_pdf
    else:
        preview_path = ensure_uploaded_file_saved(uploaded_file)
    return preview_path, using_sample


def render(
    uploaded_file,
    *,
    preview_path: Path | None = None,
    using_sample: bool | None = None,
) -> tuple[Path | None, bool]:
    st.subheader("Tài liệu đầu vào")
    if preview_path is None or using_sample is None:
        preview_path, using_sample = get_preview_context(uploaded_file)

    if uploaded_file is None:
        if using_sample and preview_path is not None:
            st.info("Chưa tải file mới. Đang hiển thị preview PDF mẫu trong thư mục samples.")
        else:
            st.info("Hãy tải lên file PDF/ảnh GCN để bắt đầu.")

    if preview_path is not None:
        try:
            if preview_path.suffix.lower() == ".pdf":
                _render_pdf_preview(preview_path)
            else:
                _render_image_preview(preview_path)
        except Exception as exc:
            st.warning(f"Không tạo được preview: {exc}")
    return preview_path, using_sample


def _document_page_key(preview_path: Path, page_number: int) -> str:
    return f"{preview_path.resolve()}::{page_number}"


def _ensure_pdf_viewer_state() -> None:
    rotations = st.session_state.setdefault("page_rotations", {})
    if not isinstance(rotations, dict):
        st.session_state["page_rotations"] = {}
    zoom_level = st.session_state.setdefault("zoom_level", 1.4)
    if not isinstance(zoom_level, (int, float)):
        st.session_state["zoom_level"] = 1.4
    st.session_state["zoom_level"] = max(1.0, min(float(st.session_state["zoom_level"]), 2.5))


def _metadata_page(metadata: dict[str, object], page_number: int) -> dict[str, object]:
    pages = metadata.get("pages", {})
    if isinstance(pages, dict):
        page_data = pages.get(page_number, {})
        if isinstance(page_data, dict):
            return page_data
    return {}


def _base_page_rotation(metadata: dict[str, object], page_number: int) -> int:
    return int(_metadata_page(metadata, page_number).get("rotation") or 0) % 360


def _manual_page_rotation(preview_path: Path, page_number: int) -> int:
    rotations = st.session_state.setdefault("page_rotations", {})
    return int(rotations.get(_document_page_key(preview_path, page_number), 0)) % 360


def _display_page_rotation(preview_path: Path, metadata: dict[str, object], page_number: int) -> int:
    return (_base_page_rotation(metadata, page_number) + _manual_page_rotation(preview_path, page_number)) % 360


def _adjust_page_rotations(preview_path: Path, visible_pages: list[int], delta: int) -> None:
    rotations = st.session_state.setdefault("page_rotations", {})
    for page_number in visible_pages:
        key = _document_page_key(preview_path, page_number)
        rotations[key] = (int(rotations.get(key, 0)) + delta) % 360


def _render_pdf_toolbar(preview_path: Path, visible_pages: list[int], metadata: dict[str, object]) -> float:
    _ensure_pdf_viewer_state()

    scanned_pages = [
        page_number
        for page_number in visible_pages
        if bool(_metadata_page(metadata, page_number).get("is_scanned"))
    ]
    if scanned_pages:
        st.info(
            "Trang "
            + ", ".join(str(page_number) for page_number in scanned_pages)
            + " được xác định là Ảnh quét và đang chờ AI căn chỉnh."
        )

    toolbar_cols = st.columns([1, 1, 4])
    with toolbar_cols[0]:
        if st.button("↺ Xoay trái", key=f"toolbar_rotate_left_{preview_path.name}", width="stretch"):
            _adjust_page_rotations(preview_path, visible_pages, -90)
            st.rerun()
    with toolbar_cols[1]:
        if st.button("↻ Xoay phải", key=f"toolbar_rotate_right_{preview_path.name}", width="stretch"):
            _adjust_page_rotations(preview_path, visible_pages, 90)
            st.rerun()
    with toolbar_cols[2]:
        rotation_notes = [
            f"T{page_number}: {_display_page_rotation(preview_path, metadata, page_number)}°"
            for page_number in visible_pages
        ]
        st.caption(" | ".join(rotation_notes))

    return 1.4


def _render_pdf_preview(preview_path: Path) -> None:
    total_pages = pdf_page_count(preview_path)
    metadata = get_pdf_metadata(preview_path)
    _ensure_pdf_viewer_state()
    thumb_col, viewer_col = st.columns([0.22, 0.78], gap="medium")

    with viewer_col:
        view_mode = st.radio(
            "Chế độ xem PDF",
            ["1 trang", "2 trang"],
            horizontal=True,
            key=f"preview_mode_{preview_path.name}",
        )
        start_page_max = max(1, total_pages - 1) if view_mode == "2 trang" and total_pages > 1 else max(total_pages, 1)
        page_key = f"preview_page_{preview_path.name}"
        st.session_state[page_key] = max(1, min(int(st.session_state.get(page_key, 1)), start_page_max))
        page_number = st.slider(
            "Trang tài liệu" if view_mode == "1 trang" else "Trang bắt đầu",
            min_value=1,
            max_value=start_page_max,
            key=page_key,
        )

        visible_pages = [page_number]
        if view_mode == "2 trang" and total_pages > 1:
            visible_pages = [page_number, min(page_number + 1, total_pages)]

        zoom_scale = _render_pdf_toolbar(preview_path, visible_pages, metadata)

        warning_pages = [
            visible_page
            for visible_page in visible_pages
            if _base_page_rotation(metadata, visible_page) in {180, 270}
        ]
        if warning_pages:
            st.warning(
                "Cần kiểm tra lại hướng chữ ở trang: "
                + ", ".join(str(item) for item in warning_pages)
                + " vì ứng dụng đang tự xoay 180°/270°."
            )

        page_images: dict[int, bytes] = {}
        for visible_page in visible_pages:
            page_images[visible_page] = pdf_page_png(
                preview_path,
                page_number=visible_page,
                scale=zoom_scale,
                rotation=_display_page_rotation(preview_path, metadata, visible_page),
            )

        if view_mode == "2 trang" and len(visible_pages) == 2:
            _render_dual_page_view(visible_pages, page_images, total_pages)
        else:
            _render_single_page_view(visible_pages[0], page_images, total_pages)

    with thumb_col:
        st.caption("Ảnh thu nhỏ theo trang")
        for thumb_page in range(1, total_pages + 1):
            is_current_thumb = thumb_page in visible_pages
            if is_current_thumb:
                st.caption(f"Đang xem trang {thumb_page}")
            st.image(
                pdf_thumbnail_png(
                    preview_path,
                    page_number=thumb_page,
                    rotation=_display_page_rotation(preview_path, metadata, thumb_page),
                ),
                width="stretch",
            )
            if st.button(
                f"Mở trang {thumb_page}",
                key=f"thumb_page_{preview_path.name}_{thumb_page}",
                width="stretch",
                on_click=select_pdf_preview_page,
                args=(preview_path.name,),
                kwargs={"thumb_page": thumb_page, "total_pages": total_pages},
            ):
                pass


def _render_dual_page_view(visible_pages: list[int], page_images: dict[int, bytes], total_pages: int) -> None:
    left_page_number, right_page_number = visible_pages
    left_page, right_page = st.columns(2)
    with left_page:
        st.image(page_images[left_page_number], width="stretch")
        st.caption(f"Trang {left_page_number}/{total_pages}")
    with right_page:
        st.image(page_images[right_page_number], width="stretch")
        st.caption(f"Trang {right_page_number}/{total_pages}")


def _render_single_page_view(current_page: int, page_images: dict[int, bytes], total_pages: int) -> None:
    st.image(page_images[current_page], width="stretch")
    st.caption(f"Trang {current_page}/{total_pages}")


def _render_image_preview(preview_path: Path) -> None:
    zoom_scale = 1.4
    auto_rotation = get_auto_rotation(preview_path, page_number=1)
    manual_rotation = get_manual_rotation(preview_path, page_number=1)
    rotation = (auto_rotation + manual_rotation) % 360
    st.caption(f"Tự xoay {auto_rotation}° | Xoay tay {manual_rotation}°")
    if auto_rotation in {180, 270}:
        st.warning("Cần kiểm tra lại hướng chữ của ảnh vì ứng dụng đang tự xoay 180°/270°.")
    st.image(
        normalize_image_for_preview(preview_path, rotation=rotation, scale=zoom_scale),
        width="stretch",
    )
    rotate_image_cols = st.columns(4)
    with rotate_image_cols[0]:
        if st.button("Tự xoay lại", key=f"rerotate_image_{preview_path.name}", width="stretch"):
            reset_manual_rotation(preview_path, page_number=1)
            refresh_auto_rotation(preview_path, page_number=1)
            st.rerun()
    with rotate_image_cols[1]:
        if st.button("Xoay trái ảnh", key=f"rotate_left_image_{preview_path.name}", width="stretch"):
            adjust_manual_rotation(preview_path, page_number=1, delta=-90)
            st.rerun()
    with rotate_image_cols[2]:
        if st.button("Xoay phải ảnh", key=f"rotate_right_image_{preview_path.name}", width="stretch"):
            adjust_manual_rotation(preview_path, page_number=1, delta=90)
            st.rerun()
    with rotate_image_cols[3]:
        locked = is_rotation_locked(preview_path, page_number=1)
        if st.button("Mở khóa" if locked else "Khóa xoay", key=f"lock_image_{preview_path.name}", width="stretch"):
            set_rotation_lock(preview_path, page_number=1, locked=not locked)
            st.rerun()
