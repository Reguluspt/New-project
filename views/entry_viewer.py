from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.app_config import (
    ROOT,
    adjust_manual_rotation,
    ensure_auto_rotations,
    ensure_uploaded_file_saved,
    get_auto_rotation,
    get_manual_rotation,
    is_rotation_locked,
    refresh_all_auto_rotations,
    refresh_auto_rotation,
    reset_all_manual_rotations,
    reset_manual_rotation,
    select_pdf_preview_page,
    set_rotation_lock,
)
from src.preview import normalize_image_for_preview, pdf_page_count, pdf_page_png, pdf_thumbnail_png


def render(uploaded_file) -> tuple[Path | None, bool]:
    st.subheader("Tài liệu đầu vào")
    preview_path: Path | None = None
    using_sample = False
    if uploaded_file is None:
        sample_pdf = ROOT / "samples" / "gcn.pdf"
        if sample_pdf.exists():
            using_sample = True
            preview_path = sample_pdf
            st.info("Chưa tải file mới. Đang hiển thị preview PDF mẫu trong thư mục samples.")
        else:
            st.info("Hãy tải lên file PDF/ảnh GCN để bắt đầu.")
    else:
        preview_path = ensure_uploaded_file_saved(uploaded_file)

    if preview_path is not None:
        try:
            if preview_path.suffix.lower() == ".pdf":
                _render_pdf_preview(preview_path)
            else:
                _render_image_preview(preview_path)
        except Exception as exc:
            st.warning(f"Không tạo được preview: {exc}")
    return preview_path, using_sample


# PDF/image preview helpers

def _render_pdf_preview(preview_path: Path) -> None:
    total_pages = pdf_page_count(preview_path)
    ensure_auto_rotations(preview_path, total_pages=total_pages)
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

        zoom_key = f"preview_zoom_{preview_path.name}"
        st.session_state.setdefault(zoom_key, 140)
        zoom_col1, zoom_col2, zoom_col3 = st.columns([1, 2, 1])
        with zoom_col1:
            if st.button("Thu nhỏ", key=f"zoom_out_{preview_path.name}", width="stretch"):
                st.session_state[zoom_key] = max(60, int(st.session_state[zoom_key]) - 20)
        with zoom_col2:
            st.slider("Độ phóng", min_value=60, max_value=240, step=10, key=zoom_key)
        with zoom_col3:
            if st.button("Phóng to", key=f"zoom_in_{preview_path.name}", width="stretch"):
                st.session_state[zoom_key] = min(240, int(st.session_state[zoom_key]) + 20)
        zoom_scale = float(st.session_state[zoom_key]) / 100.0

        visible_pages = [page_number]
        if view_mode == "2 trang" and total_pages > 1:
            visible_pages = [page_number, min(page_number + 1, total_pages)]

        control_cols = st.columns([1, 1, 2])
        with control_cols[0]:
            if st.button("Tự xoay từng trang", key=f"rerotate_{preview_path.name}", width="stretch"):
                reset_all_manual_rotations(preview_path, total_pages=total_pages)
                refresh_all_auto_rotations(preview_path, total_pages=total_pages)
                st.rerun()
        with control_cols[1]:
            st.caption("Tự tính góc riêng cho từng trang và đặt lại góc xoay tay.")
        with control_cols[2]:
            auto_notes = []
            for visible_page in visible_pages:
                auto_rotation = get_auto_rotation(preview_path, page_number=visible_page)
                manual_rotation = get_manual_rotation(preview_path, page_number=visible_page)
                lock_status = "khóa" if is_rotation_locked(preview_path, page_number=visible_page) else "mở"
                auto_notes.append(f"T{visible_page}: tự xoay {auto_rotation}°, xoay tay {manual_rotation}°, {lock_status}")
            st.caption(" | ".join(auto_notes))

        warning_pages = [
            visible_page
            for visible_page in visible_pages
            if get_auto_rotation(preview_path, page_number=visible_page) in {180, 270}
        ]
        if warning_pages:
            st.warning(
                "Cần kiểm tra lại hướng chữ ở trang: "
                + ", ".join(str(item) for item in warning_pages)
                + " vì ứng dụng đang tự xoay 180°/270°."
            )

        page_images: dict[int, bytes] = {}
        page_rotations: dict[int, int] = {}
        for visible_page in visible_pages:
            page_rotations[visible_page] = (
                get_auto_rotation(preview_path, page_number=visible_page)
                + get_manual_rotation(preview_path, page_number=visible_page)
            ) % 360
            page_images[visible_page] = pdf_page_png(
                preview_path,
                page_number=visible_page,
                scale=zoom_scale,
                rotation=page_rotations[visible_page],
            )

        if view_mode == "2 trang" and len(visible_pages) == 2:
            _render_dual_page_view(preview_path, visible_pages, page_images, total_pages)
        else:
            _render_single_page_view(preview_path, visible_pages[0], page_images, total_pages)

    with thumb_col:
        st.caption("Ảnh thu nhỏ theo trang")
        for thumb_page in range(1, total_pages + 1):
            thumb_rotation = (
                get_auto_rotation(preview_path, page_number=thumb_page)
                + get_manual_rotation(preview_path, page_number=thumb_page)
            ) % 360
            is_current_thumb = thumb_page in visible_pages
            if is_current_thumb:
                st.caption(f"Đang xem trang {thumb_page}")
            st.image(
                pdf_thumbnail_png(preview_path, page_number=thumb_page, rotation=thumb_rotation),
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


def _render_dual_page_view(preview_path: Path, visible_pages: list[int], page_images: dict[int, bytes], total_pages: int) -> None:
    left_page_number, right_page_number = visible_pages
    left_page, right_page = st.columns(2)
    with left_page:
        st.image(page_images[left_page_number], width="stretch")
        st.caption(f"Trang {left_page_number}/{total_pages}")
        _render_page_rotation_controls(preview_path, left_page_number, "left")
    with right_page:
        st.image(page_images[right_page_number], width="stretch")
        st.caption(f"Trang {right_page_number}/{total_pages}")
        _render_page_rotation_controls(preview_path, right_page_number, "right")


def _render_single_page_view(preview_path: Path, current_page: int, page_images: dict[int, bytes], total_pages: int) -> None:
    st.image(page_images[current_page], width="stretch")
    st.caption(f"Trang {current_page}/{total_pages}")
    _render_page_rotation_controls(preview_path, current_page, "single")


def _render_page_rotation_controls(preview_path: Path, page_number: int, side: str) -> None:
    cols = st.columns(3)
    with cols[0]:
        if st.button(f"Xoay trái trang {side}", key=f"rotate_left_{side}_{preview_path.name}_{page_number}", width="stretch"):
            adjust_manual_rotation(preview_path, page_number=page_number, delta=-90)
            st.rerun()
    with cols[1]:
        if st.button(f"Xoay phải trang {side}", key=f"rotate_right_{side}_{preview_path.name}_{page_number}", width="stretch"):
            adjust_manual_rotation(preview_path, page_number=page_number, delta=90)
            st.rerun()
    with cols[2]:
        locked = is_rotation_locked(preview_path, page_number=page_number)
        if st.button("Mở khóa" if locked else "Khóa xoay", key=f"lock_{side}_{preview_path.name}_{page_number}", width="stretch"):
            set_rotation_lock(preview_path, page_number=page_number, locked=not locked)
            st.rerun()


def _render_image_preview(preview_path: Path) -> None:
    zoom_key = f"preview_zoom_{preview_path.name}"
    st.session_state.setdefault(zoom_key, 140)
    zoom_col1, zoom_col2, zoom_col3 = st.columns([1, 2, 1])
    with zoom_col1:
        if st.button("Thu nhỏ", key=f"zoom_out_{preview_path.name}", width="stretch"):
            st.session_state[zoom_key] = max(60, int(st.session_state[zoom_key]) - 20)
    with zoom_col2:
        st.slider("Độ phóng", min_value=60, max_value=240, step=10, key=zoom_key)
    with zoom_col3:
        if st.button("Phóng to", key=f"zoom_in_{preview_path.name}", width="stretch"):
            st.session_state[zoom_key] = min(240, int(st.session_state[zoom_key]) + 20)
    zoom_scale = float(st.session_state[zoom_key]) / 100.0
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
