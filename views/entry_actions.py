from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
from typing import Any

import streamlit as st

from src.app_config import apply_extraction_collection_to_form, apply_extraction_to_form
from src.extractor import extract_land_certificate
from src.gemini_extractor import extract_land_certificate_with_gemini
from src.models import LandCertificateMultiExtraction
from src.ocr_accumulator import multi_extraction_to_form_state, normalize_multi_extraction


def _document_page_key(preview_path: Path, page_number: int) -> str:
    return f"{preview_path.resolve()}::{page_number}"


def _normalize_rotation(value: Any) -> int | None:
    try:
        angle = int(round(float(value))) % 360
    except (TypeError, ValueError):
        return None
    return angle if angle in {0, 90, 180, 270} else None


def apply_gemini_page_metadata_to_viewer(preview_path: Path, extraction: object) -> bool:
    metadata = getattr(extraction, "page_metadata", None)
    if not metadata:
        return False

    if isinstance(metadata, dict):
        items = metadata.items()
    elif isinstance(metadata, list):
        items = []
        for item in metadata:
            if isinstance(item, dict):
                items.append((item.get("page_number"), item.get("rotation")))
            else:
                items.append((getattr(item, "page_number", None), getattr(item, "rotation", None)))
    else:
        return False

    rotations = st.session_state.setdefault("page_rotations", {})
    updated = False
    for raw_page_number, raw_rotation in items:
        try:
            page_number = int(raw_page_number)
        except (TypeError, ValueError):
            continue
        if page_number < 1:
            continue
        rotation = _normalize_rotation(raw_rotation)
        if rotation is None:
            continue
        rotations[_document_page_key(preview_path, page_number)] = rotation
        updated = True
    return updated


def run_ocr_extraction(
    *,
    preview_path: Path,
    ai_provider: str,
    api_key: str,
    model: str,
    remember_ai_config: Callable[[], None],
):
    if ai_provider == "Gemini":
        extraction = extract_land_certificate_with_gemini(
            preview_path,
            api_key=api_key,
            model=model,
        )
    else:
        extraction = extract_land_certificate(
            preview_path,
            api_key=api_key,
            model=model,
        )
    if isinstance(extraction, LandCertificateMultiExtraction):
        from src.models import blank_extraction

        single_extraction = extraction.assets[0] if extraction.assets else blank_extraction()
    elif hasattr(extraction, "assets") and extraction.assets:
        single_extraction = extraction.assets[0]
    else:
        single_extraction = extraction

    apply_extraction_to_form(single_extraction)
    remember_ai_config()
    return single_extraction


def _is_temporary_model_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "503",
            "unavailable",
            "high demand",
            "resource_exhausted",
            "rate limit",
            "temporarily",
            "overloaded",
        )
    )


def _fallback_gemini_models(primary_model: str) -> list[str]:
    configured = [
        item.strip()
        for item in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",")
        if item.strip()
    ]
    defaults = ["gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    seen: set[str] = {primary_model}
    models: list[str] = []
    for model_name in [*configured, *defaults]:
        if model_name and model_name not in seen:
            models.append(model_name)
            seen.add(model_name)
    return models


def extract_with_fallback(
    *,
    preview_path: Path,
    ai_provider: str,
    api_key: str,
    model: str,
):
    attempts: list[tuple[str, str, Exception | None]] = []
    if ai_provider == "Gemini":
        candidate_models = [model, *_fallback_gemini_models(model)]
        for candidate_model in candidate_models:
            try:
                extraction = extract_land_certificate_with_gemini(
                    preview_path,
                    api_key=api_key,
                    model=candidate_model,
                )
                return {
                    "extraction": extraction,
                    "provider": "Gemini",
                    "model": candidate_model,
                    "attempts": len(attempts) + 1,
                    "message": "OK" if candidate_model == model else f"Đã dùng model thay thế: {candidate_model}",
                }
            except Exception as exc:
                attempts.append(("Gemini", candidate_model, exc))
                if not _is_temporary_model_error(exc):
                    raise

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        openai_model = (
            os.getenv("OPENAI_FALLBACK_MODEL", "").strip()
            or os.getenv("OPENAI_MODEL", "").strip()
            or "gpt-4.1-mini"
        )
        if openai_key:
            try:
                extraction = extract_land_certificate(
                    preview_path,
                    api_key=openai_key,
                    model=openai_model,
                )
                return {
                    "extraction": extraction,
                    "provider": "OpenAI",
                    "model": openai_model,
                    "attempts": len(attempts) + 1,
                    "message": "Gemini quá tải, đã chuyển sang OpenAI fallback.",
                }
            except Exception as exc:
                attempts.append(("OpenAI", openai_model, exc))

        last_error = attempts[-1][2] if attempts else RuntimeError("Không có lần thử OCR nào.")
        raise RuntimeError(f"AI đang quá tải hoặc không phản hồi sau {len(attempts)} lần thử: {last_error}")

    extraction = extract_land_certificate(
        preview_path,
        api_key=api_key,
        model=model,
    )
    return {
        "extraction": extraction,
        "provider": "OpenAI",
        "model": model,
        "attempts": 1,
        "message": "OK",
    }


def _queue_items() -> list[dict[str, object]]:
    return st.session_state.setdefault("entry_upload_queue", [])


def _select_upload(item_id: str) -> None:
    st.session_state["entry_selected_upload_id"] = item_id


def selected_upload_path() -> Path | None:
    selected_id = st.session_state.get("entry_selected_upload_id")
    for item in _queue_items():
        if item.get("id") == selected_id:
            path = Path(str(item.get("path") or ""))
            return path if path.exists() else None
    pending = [item for item in _queue_items() if Path(str(item.get("path") or "")).exists()]
    if pending:
        st.session_state["entry_selected_upload_id"] = pending[0]["id"]
        return Path(str(pending[0]["path"]))
    return None


def render_upload_queue() -> None:
    items = _queue_items()
    if not items:
        st.info("Chưa có file nào trong hàng đợi quét.")
        return

    st.caption("Hàng đợi file đã tải lên")
    for index, item in enumerate(items, start=1):
        names = ", ".join(str(name) for name in item.get("source_names", []))
        status = str(item.get("status") or "pending")
        cols = st.columns([0.09, 0.51, 0.18, 0.22])
        with cols[0]:
            st.write(f"#{index}")
        with cols[1]:
            st.write(names)
            if item.get("message"):
                st.caption(str(item["message"]))
        with cols[2]:
            st.write(status)
        with cols[3]:
            if st.button("Xem file", key=f"select_upload_{item['id']}", width="stretch"):
                _select_upload(str(item["id"]))
                st.rerun()


def _render_extraction_summary(extraction: object) -> None:
    multi = normalize_multi_extraction(extraction)
    state = multi_extraction_to_form_state(multi)
    st.caption(f"AI tìm thấy {len(multi.assets)} tài sản.")
    st.text_area(
        "Tài sản trích xuất",
        value=state.get("entry_asset_description", ""),
        height=120,
        key=f"review_assets_{id(extraction)}",
        disabled=True,
    )
    customer = state.get("entry_customer_info_ind", "")
    citizen_id = state.get("entry_citizen_id_ind", "")
    if customer or citizen_id:
        st.caption(f"Khách hàng gợi ý: {customer or 'Chưa có'} | CCCD/CMND: {citizen_id or 'Chưa có'}")


def render_review_items() -> None:
    review_items = [item for item in _queue_items() if item.get("status") == "review" and item.get("extraction") is not None]
    if not review_items:
        return

    st.subheader("Duyệt kết quả sau khi quét")
    for item in review_items:
        names = ", ".join(str(name) for name in item.get("source_names", []))
        with st.expander(f"{names} - chờ duyệt", expanded=True):
            _render_extraction_summary(item["extraction"])
            cols = st.columns(3)
            with cols[0]:
                if st.button("Xem file gốc", key=f"review_view_{item['id']}", width="stretch"):
                    _select_upload(str(item["id"]))
                    st.rerun()
            with cols[1]:
                if st.button("Đưa vào form", key=f"review_apply_{item['id']}", type="primary", width="stretch"):
                    count = apply_extraction_collection_to_form(item["extraction"], append=True)
                    item["status"] = "applied"
                    item["asset_count"] = count
                    approved = st.session_state.setdefault("entry_approved_documents", [])
                    original_name = names or Path(str(item.get("path"))).name
                    if item.get("kind") == "image_pdf":
                        original_name = "anh_gcn_ghep.pdf"
                    approved.append(
                        {
                            "path": item.get("path"),
                            "original_name": original_name,
                        }
                    )
                    st.success(f"Đã đưa {count} tài sản vào form.")
                    st.rerun()
            with cols[2]:
                if st.button("Bỏ qua", key=f"review_skip_{item['id']}", width="stretch"):
                    item["status"] = "skipped"
                    st.rerun()


def render_queue_ocr_action(
    *,
    preview_path: Path | None,
    ai_provider: str,
    api_key: str,
    model: str,
    api_key_label: str,
    remember_ai_config: Callable[[], None],
) -> None:
    items = _queue_items()
    render_upload_queue()
    if not items:
        return

    pending_count = sum(1 for item in items if item.get("status") in {"pending", "error"})
    if st.button(f"Quét {pending_count} file chờ xử lý bằng {ai_provider}", type="primary", width="stretch", disabled=pending_count == 0):
        if not api_key:
            st.error(f"Cần nhập {api_key_label} trước khi quét.")
            return
        progress = st.progress(0)
        for index, item in enumerate(items, start=1):
            if item.get("status") not in {"pending", "error"}:
                progress.progress(index / len(items))
                continue
            path = Path(str(item.get("path") or ""))
            if not path.exists():
                item["status"] = "error"
                item["message"] = "Không tìm thấy file tạm để quét."
                continue
            item["status"] = "processing"
            _select_upload(str(item["id"]))
            try:
                with st.spinner(f"Đang quét {', '.join(str(name) for name in item.get('source_names', []))}..."):
                    result = extract_with_fallback(
                        preview_path=path,
                        ai_provider=ai_provider,
                        api_key=api_key,
                        model=model,
                    )
                item["extraction"] = result["extraction"]
                item["status"] = "review"
                item["provider_used"] = result["provider"]
                item["model_used"] = result["model"]
                item["attempts"] = result["attempts"]
                item["message"] = result["message"]
                item["asset_count"] = len(normalize_multi_extraction(result["extraction"]).assets)
            except Exception as exc:
                item["status"] = "error"
                item["message"] = str(exc)
                st.error(f"Quét thất bại: {exc}")
            progress.progress(index / len(items))
        remember_ai_config()
        st.rerun()

    render_review_items()


def render_ocr_action(
    *,
    uploaded_file,
    preview_path: Path | None,
    using_sample: bool,
    ai_provider: str,
    api_key: str,
    model: str,
    api_key_label: str,
    remember_ai_config: Callable[[], None],
) -> None:
    if uploaded_file is not None and not using_sample:
        if st.button(f"Quét GCN bằng {ai_provider}", type="primary", width="stretch"):
            if not api_key:
                st.error(f"Cần nhập {api_key_label} trước khi quét.")
            else:
                with st.spinner("Đang gửi tài liệu đến AI và trích xuất dữ liệu..."):
                    try:
                        st.session_state.extraction = run_ocr_extraction(
                            preview_path=preview_path,
                            ai_provider=ai_provider,
                            api_key=api_key,
                            model=model,
                            remember_ai_config=remember_ai_config,
                        )
                        st.success("Đã trích xuất xong và tự điền vào form. Vui lòng kiểm tra lại bên phải.")
                    except Exception as exc:
                        st.error(f"Quét AI thất bại: {exc}")
