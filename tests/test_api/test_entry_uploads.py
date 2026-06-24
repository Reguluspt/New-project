from __future__ import annotations

import io

import fitz

from api.blueprints import entry as entry_module


def _pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def _upload_two_pdfs(auth_client, monkeypatch, tmp_path):
    monkeypatch.setattr(entry_module, "PROJECT_ROOT", tmp_path)
    response = auth_client.post(
        "/api/entry/upload",
        data={
            "files": [
                (io.BytesIO(_pdf_bytes("FIRST PDF")), "first.pdf"),
                (io.BytesIO(_pdf_bytes("SECOND PDF")), "second.pdf"),
            ]
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    return response.get_json()


def test_entry_upload_keeps_each_pdf_in_a_separate_directory(auth_client, monkeypatch, tmp_path):
    payload = _upload_two_pdfs(auth_client, monkeypatch, tmp_path)

    assert len(payload["files"]) == 2
    first, second = payload["files"]
    assert first["file_id"] != second["file_id"]
    assert first["thumbnails"][0] != second["thumbnails"][0]

    for uploaded_file in (first, second):
        preview = auth_client.get(uploaded_file["thumbnails"][0])
        assert preview.status_code == 200
        assert preview.content_type == "image/jpeg"


def test_entry_extract_uses_the_selected_pdf(auth_client, monkeypatch, tmp_path):
    payload = _upload_two_pdfs(auth_client, monkeypatch, tmp_path)
    selected = payload["files"][1]
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_extract(path, *, api_key, model):
        with fitz.open(path) as document:
            marker = document[0].get_text().strip()

        class Extraction:
            def model_dump(self):
                return {"assets": [{"marker": marker}]}

        return Extraction()

    monkeypatch.setattr(
        "src.gemini_extractor.extract_land_certificate_with_gemini",
        fake_extract,
    )

    response = auth_client.post(
        "/api/entry/extract",
        json={
            "upload_id": payload["upload_id"],
            "file_id": selected["file_id"],
            "pages": [1],
            "provider": "Gemini",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["extraction"] == {"marker": "SECOND PDF"}


def test_entry_extract_all_files(auth_client, monkeypatch, tmp_path):
    payload = _upload_two_pdfs(auth_client, monkeypatch, tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    calls = []
    def fake_extract(path, *, api_key, model):
        with fitz.open(path) as document:
            marker = document[0].get_text().strip()
        calls.append(marker)
        
        class Extraction:
            def model_dump(self):
                return {
                    "assets": [{
                        "so_thua_dat": {"value": f"thua-{marker}", "confidence": 0.9, "evidence": ""},
                        "so_to_ban_do": {"value": f"to-{marker}", "confidence": 0.9, "evidence": ""},
                        "dia_chi_thua_dat": {"value": "", "confidence": 0.0, "evidence": ""},
                        "ten_chu_so_huu_cuoi_cung": {"value": "", "confidence": 0.0, "evidence": ""},
                        "dia_chi_chu_so_huu_cuoi_cung": {"value": "", "confidence": 0.0, "evidence": ""},
                        "so_cccd_chu_so_huu_cuoi_cung": {"value": "", "confidence": 0.0, "evidence": ""},
                    }]
                }

        return Extraction()

    monkeypatch.setattr(
        "src.gemini_extractor.extract_land_certificate_with_gemini",
        fake_extract,
    )

    response = auth_client.post(
        "/api/entry/extract",
        json={
            "upload_id": payload["upload_id"],
            "provider": "Gemini",
            "model": "gemini-2.5-flash",
            "extract_all": True,
        },
    )

    assert response.status_code == 200
    res_json = response.get_json()
    assert "FIRST PDF" in calls
    assert "SECOND PDF" in calls
    
    assert "so_thua_dat" in res_json["extraction"]
    assert res_json["extraction"]["so_thua_dat"]["value"] in ("thua-FIRST PDF", "thua-SECOND PDF")

