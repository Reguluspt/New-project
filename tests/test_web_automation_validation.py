import asyncio
from types import SimpleNamespace

from src.web_automation import (
    WEB_STATUS_TABLE_TIMEOUT,
    WEB_SUBMIT_TIMEOUT,
    _bank_web_value,
    _is_submit_response,
    _purpose_web_value,
    _source_web_candidates,
    find_created_web_case_id,
    missing_web_entry_fields,
)


def test_missing_web_entry_fields_reports_required_labels() -> None:
    missing = missing_web_entry_fields({"customer_info": "Nguyen Van A"})

    labels = {item["label"] for item in missing}

    assert "Tên khách hàng" not in labels
    assert "Số hợp đồng" in labels
    assert "Tài sản thẩm định" in labels
    assert "Nguồn/ngân hàng" in labels


def test_missing_web_entry_fields_accepts_asset_address_fallback() -> None:
    missing = missing_web_entry_fields(
        {
            "contract_number": "N05-0833",
            "customer_info": "Nguyen Van A",
            "customer_address": "Gia Lai",
            "dia_chi_thua_dat": "Thua dat so 1",
            "valuation_purpose": "Vay vốn",
            "asset_type": "Bất động sản",
            "source": "BIDV",
        }
    )

    assert missing == []


def test_web_dropdown_value_mapping_for_common_entry_values() -> None:
    assert _purpose_web_value("Làm cơ sở tham khảo để thế chấp vay vốn tại ngân hàng BIDV") == "Thẩm định vay vốn ngân hàng"
    assert _purpose_web_value("Làm cơ sở tham khảo để xử lý tài sản đảm bảo tại ngân hàng") == "Thanh lý, phát mãi tài sản"
    assert _bank_web_value("BIDV Nam Gia Lai - Mr. Dương - 0902155345") == "BIDV"


def test_source_web_candidates_try_original_source_before_bank_fallback() -> None:
    assert _source_web_candidates("BIDV Nam Gia Lai - Mr. Dương - 0902155345") == [
        "BIDV Nam Gia Lai - Mr. Dương - 0902155345",
        "BIDV",
    ]


def test_submit_response_tracks_submit_api_and_waits_120_seconds() -> None:
    assert WEB_SUBMIT_TIMEOUT == 120_000
    assert _is_submit_response(SimpleNamespace(url="https://gapi.cenhomes.vn/api/submit-yeu-cau-tham-dinh"))
    assert not _is_submit_response(SimpleNamespace(url="https://gapi.cenhomes.vn/api/other"))


class _StatusTab:
    @property
    def first(self):
        return self

    async def count(self) -> int:
        return 1

    async def click(self, timeout: int) -> None:
        return None


class _LoadingStatusPage:
    def __init__(self) -> None:
        self.values = ["", "", "98765"]
        self.waits: list[int] = []

    def get_by_role(self, role: str, name):
        return _StatusTab()

    def get_by_text(self, text: str, exact: bool = False):
        return _StatusTab()

    async def wait_for_load_state(self, state: str) -> None:
        return None

    async def wait_for_timeout(self, timeout: int) -> None:
        self.waits.append(timeout)

    async def evaluate(self, script: str) -> str:
        return self.values.pop(0)


def test_find_created_web_case_id_keeps_polling_while_table_is_loading() -> None:
    page = _LoadingStatusPage()

    web_case_id = asyncio.run(find_created_web_case_id(page, {}))

    assert WEB_STATUS_TABLE_TIMEOUT == 120_000
    assert web_case_id == "98765"
    assert page.waits == [800, 500, 500]
