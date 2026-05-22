from src.web_automation import missing_web_entry_fields


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
