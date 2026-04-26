from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedValue(BaseModel):
    value: str = Field(description="Gia tri da doc duoc, de chuoi rong neu khong thay.")
    confidence: float = Field(ge=0.0, le=1.0, description="Do tin cay tu 0 den 1.")
    evidence: str = Field(description="Cum tu/ngan canh ngan tren GCN lam bang chung.")


class LandCertificateExtraction(BaseModel):
    so_thua_dat: ExtractedValue
    so_to_ban_do: ExtractedValue
    dia_chi_thua_dat: ExtractedValue
    ten_chu_so_huu_cuoi_cung: ExtractedValue
    dia_chi_chu_so_huu_cuoi_cung: ExtractedValue
    so_cccd_chu_so_huu_cuoi_cung: ExtractedValue
    notes: list[str] = Field(description="Canh bao ngan gon ve phan khong doc duoc hoac nghi ngo.")


def blank_extraction() -> LandCertificateExtraction:
    empty = ExtractedValue(value="", confidence=0.0, evidence="")
    return LandCertificateExtraction(
        so_thua_dat=empty.model_copy(),
        so_to_ban_do=empty.model_copy(),
        dia_chi_thua_dat=empty.model_copy(),
        ten_chu_so_huu_cuoi_cung=empty.model_copy(),
        dia_chi_chu_so_huu_cuoi_cung=empty.model_copy(),
        so_cccd_chu_so_huu_cuoi_cung=empty.model_copy(),
        notes=[],
    )
