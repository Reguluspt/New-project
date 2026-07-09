
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from src.sqlite_store import get_case
from src.web_automation import (
    PROJECT_ROOT,
    UPLOAD_DIR,
    _asset_web_values,
    _bank_web_value,
    _check_by_label_text,
    _select_dropdown,
    fill_asset_info,
    fill_basic_info,
    start_browser_and_login,
)

CASE_ID = 2285
RUNS = int(os.getenv("DRY_RUN_COUNT", "3"))
OUT_DIR = PROJECT_ROOT / "logs" / "dry_run_web_entry"
OUT_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(PROJECT_ROOT / "API.env", override=True)


def split_value(raw_val, index):
    parts = [p.strip() for p in str(raw_val or "").split("\n") if p.strip()]
    if not parts:
        return ""
    if index < len(parts):
        return parts[index]
    return parts[-1]


def make_sub_record(record, index):
    sub = dict(record)
    sub["asset_description"] = split_value(record.get("asset_description"), index)
    sub["dia_chi"] = split_value(record.get("dia_chi"), index)
    sub["so_thua"] = split_value(record.get("so_thua"), index)
    sub["so_to"] = split_value(record.get("so_to"), index)
    for common_field in ["customer_info", "customer_address", "citizen_id", "chu_so_huu"]:
        if sub.get(common_field):
            sub[common_field] = str(sub[common_field]).replace("\n", ", ")
    return sub


async def fill_credit_until_submit(page, data):
    file_path = UPLOAD_DIR / "blank_document.pdf"
    if not file_path.exists():
        import fitz
        doc = fitz.open(); doc.new_page(); doc.save(str(file_path)); doc.close()
    await page.locator("input[type='file']").first.set_input_files(str(file_path))
    try:
        await page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass

    await _select_dropdown(page, "Ng?n H?ng", _bank_web_value(str(data.get("source") or "")))
    try:
        await page.locator("#input-sdtTinDung").fill("0905226968", timeout=5000)
    except Exception:
        pass
    try:
        await page.locator("#input-emailTinDung").fill(os.getenv("ADMIN_EMAIL", "truongpham.sacc@gmail.com"), timeout=5000)
    except Exception:
        pass

    contract_number = str(data.get("contract_number") or "").strip()
    if contract_number:
        try:
            input_so_hop_dong = page.locator("#input-soHopDong")
            if await input_so_hop_dong.count() > 0 and await input_so_hop_dong.first.is_visible():
                await input_so_hop_dong.first.fill(contract_number, timeout=5000)
            else:
                input_fallback = page.locator("xpath=//label[contains(text(), 'S? h?p ??ng')]/following-sibling::*//input | //label[contains(text(), 'S? h?p ??ng')]/..//input[not(@type='hidden')]").first
                if await input_fallback.count() > 0 and await input_fallback.is_visible():
                    await input_fallback.fill(contract_number, timeout=5000)
        except Exception:
            pass

    try:
        await page.locator("#input-phi").fill("3000000", timeout=5000)
    except Exception:
        pass
    await _check_by_label_text(page, "C? bao g?m ph? kh?o s?t")
    try:
        await page.locator("#input-phiTamUngCanThu").fill("0", timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(1000)


async def inspect_submit(page):
    submit_btn = page.locator(
        "button:has-text('Y?u C?u Th?m ??nh'), "
        "button:has-text('Y?U C?U TH?M ??NH'), "
        "input[type='submit'][value*='Th?m ??nh'], "
        "button[type='submit']:has-text('Th?m ??nh')"
    ).first
    count = await submit_btn.count()
    if count == 0:
        return {"found": False}
    try:
        await submit_btn.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    return await submit_btn.evaluate("""el => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
            found: true,
            text: (el.innerText || el.value || el.textContent || '').trim(),
            disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled'),
            visible: rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none',
            className: el.className || '',
            pointerEvents: style.pointerEvents,
            width: rect.width,
            height: rect.height
        };
    }""")


async def inspect_fields(page):
    return await page.evaluate("""() => {
        const val = (sel) => document.querySelector(sel)?.value || '';
        const txt = (sel) => document.querySelector(sel)?.innerText || document.querySelector(sel)?.textContent || '';
        return {
            customer: val('#input-tenKhachHang'),
            phone: val('#input-soDienThoai'),
            email: val('#input-email'),
            address: val('#input-diachi'),
            asset: val('#input-taisanthamdinh'),
            fee: val('#input-phi'),
            advance: val('#input-phiTamUngCanThu'),
            sourceText: txt('#input-nguonDoiTac'),
            bankText: txt('#input-nganHang'),
            assetTypeText: txt('#input-loaiTaiSanDesk'),
            assetGroupText: txt('#input-nhomTaiSan')
        };
    }""")


async def run_once(run_index, record, asset_count):
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1365, "height": 900})
        page = None
        try:
            for i in range(asset_count):
                sub = make_sub_record(record, i)
                if page is None:
                    page = await context.new_page()
                page = await start_browser_and_login(context, page=page)
                await fill_basic_info(page, sub)
                await fill_asset_info(page, sub)
                await fill_credit_until_submit(page, sub)
                submit = await inspect_submit(page)
                fields = await inspect_fields(page)
                shot = OUT_DIR / f"case_{CASE_ID}_run_{run_index}_asset_{i+1}_{int(time.time())}.png"
                await page.screenshot(path=str(shot), full_page=True)
                ok = bool(submit.get("found") and submit.get("visible") and not submit.get("disabled"))
                results.append({
                    "run": run_index,
                    "asset_index": i + 1,
                    "ok_to_click_submit": ok,
                    "url": page.url,
                    "submit": submit,
                    "fields": fields,
                    "screenshot": str(shot),
                })
                await page.close()
                page = None
        finally:
            if page:
                await page.close()
            await browser.close()
    return results


async def main():
    record = get_case(PROJECT_ROOT / "data" / "cases.db", CASE_ID)
    if not record:
        raise SystemExit(f"case {CASE_ID} not found")
    asset_count = max(
        len([p for p in str(record.get("asset_description") or "").split("\n") if p.strip()]),
        len([p for p in str(record.get("dia_chi") or "").split("\n") if p.strip()]),
        1,
    )
    all_results = []
    for run_index in range(1, RUNS + 1):
        print(f"DRY_RUN_START run={run_index} assets={asset_count}", flush=True)
        res = await run_once(run_index, record, asset_count)
        all_results.extend(res)
        for item in res:
            print("DRY_RUN_RESULT " + json.dumps(item, ensure_ascii=False), flush=True)
    summary_path = OUT_DIR / f"case_{CASE_ID}_summary_{int(time.time())}.json"
    summary_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DRY_RUN_SUMMARY {summary_path}", flush=True)
    failed = [r for r in all_results if not r.get("ok_to_click_submit")]
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
