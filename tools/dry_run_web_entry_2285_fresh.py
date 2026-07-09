
import asyncio, json, os, time
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from src.sqlite_store import get_case
from src.web_automation import PROJECT_ROOT, UPLOAD_DIR, _bank_web_value, _check_by_label_text, _select_dropdown, fill_asset_info, fill_basic_info, start_browser_and_login

CASE_ID=2285
RUNS=int(os.getenv('DRY_RUN_COUNT','2'))
OUT_DIR=PROJECT_ROOT/'logs'/'dry_run_web_entry'
OUT_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(PROJECT_ROOT/'API.env', override=True)

def split_value(raw, idx):
    parts=[p.strip() for p in str(raw or '').split('\n') if p.strip()]
    return parts[idx] if idx < len(parts) else (parts[-1] if parts else '')

def sub_record(record, idx):
    sub=dict(record)
    for key in ('asset_description','dia_chi','so_thua','so_to'):
        sub[key]=split_value(record.get(key), idx)
    for key in ('customer_info','customer_address','citizen_id','chu_so_huu'):
        if sub.get(key): sub[key]=str(sub[key]).replace('\n', ', ')
    return sub

async def fill_tail(page, data):
    file_path=UPLOAD_DIR/'blank_document.pdf'
    if not file_path.exists():
        import fitz
        doc=fitz.open(); doc.new_page(); doc.save(str(file_path)); doc.close()
    await page.locator("input[type='file']").first.set_input_files(str(file_path))
    try: await page.wait_for_load_state('networkidle', timeout=30000)
    except Exception: pass
    await _select_dropdown(page, 'Ng?n H?ng', _bank_web_value(str(data.get('source') or '')))
    for sel,val in (('#input-sdtTinDung','0905226968'),('#input-emailTinDung',os.getenv('ADMIN_EMAIL','truongpham.sacc@gmail.com')),('#input-phi','3000000'),('#input-phiTamUngCanThu','0')):
        try: await page.locator(sel).fill(val, timeout=5000)
        except Exception: pass
    contract=str(data.get('contract_number') or '').strip()
    if contract:
        for sel in ('#input-soHopDong', '#input-hopDongMobi'):
            try:
                loc=page.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    await loc.fill(contract, timeout=5000); break
            except Exception: pass
    await _check_by_label_text(page, 'C? bao g?m ph? kh?o s?t')
    await page.wait_for_timeout(1000)

async def inspect(page):
    submit=page.locator("button:has-text('Y?u C?u Th?m ??nh'), button:has-text('Y?U C?U TH?M ??NH'), input[type='submit'][value*='Th?m ??nh'], button[type='submit']:has-text('Th?m ??nh')").first
    if await submit.count()==0:
        submit_info={'found':False}
    else:
        try: await submit.scroll_into_view_if_needed(timeout=5000)
        except Exception: pass
        submit_info=await submit.evaluate("""el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return {found:true,text:(el.innerText||el.value||el.textContent||'').trim(),disabled:!!el.disabled||el.getAttribute('aria-disabled')==='true'||el.classList.contains('disabled'),visible:r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none',className:el.className||'',pointerEvents:s.pointerEvents,width:r.width,height:r.height}}""")
    fields=await page.evaluate("""()=>{const v=s=>document.querySelector(s)?.value||''; const t=s=>document.querySelector(s)?.innerText||document.querySelector(s)?.textContent||''; return {customer:v('#input-tenKhachHang'), phone:v('#input-soDienThoai'), email:v('#input-email'), address:v('#input-diachi'), asset:v('#input-taisanthamdinh'), fee:v('#input-phi'), advance:v('#input-phiTamUngCanThu'), sourceText:t('#input-nguonDoiTac'), bankText:t('#input-nganHang'), assetTypeText:t('#input-loaiTaiSanDesk'), assetGroupText:t('#input-nhomTaiSan')}}""")
    return submit_info, fields

async def main():
    record=get_case(PROJECT_ROOT/'data'/'cases.db', CASE_ID)
    n=max(len([p for p in str(record.get('asset_description') or '').split('\n') if p.strip()]), len([p for p in str(record.get('dia_chi') or '').split('\n') if p.strip()]), 1)
    results=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        try:
            for run in range(1,RUNS+1):
                print(f'DRY_RUN_START run={run} assets={n}', flush=True)
                for i in range(n):
                    context=await browser.new_context(viewport={'width':1365,'height':900})
                    page=await context.new_page()
                    try:
                        sub=sub_record(record,i)
                        await start_browser_and_login(context,page=page)
                        await fill_basic_info(page, sub)
                        await fill_asset_info(page, sub)
                        await fill_tail(page, sub)
                        submit,fields=await inspect(page)
                        shot=OUT_DIR/f'case_{CASE_ID}_fresh_run_{run}_asset_{i+1}_{int(time.time())}.png'
                        await page.screenshot(path=str(shot), full_page=True)
                        ok=bool(submit.get('found') and submit.get('visible') and not submit.get('disabled'))
                        item={'run':run,'asset_index':i+1,'ok_to_click_submit':ok,'url':page.url,'submit':submit,'fields':fields,'screenshot':str(shot)}
                        results.append(item)
                        print('DRY_RUN_RESULT '+json.dumps(item, ensure_ascii=False), flush=True)
                    except Exception as e:
                        shot=OUT_DIR/f'case_{CASE_ID}_fresh_run_{run}_asset_{i+1}_ERROR_{int(time.time())}.png'
                        try: await page.screenshot(path=str(shot), full_page=True)
                        except Exception: pass
                        item={'run':run,'asset_index':i+1,'ok_to_click_submit':False,'error':type(e).__name__+': '+str(e),'url':page.url,'screenshot':str(shot)}
                        results.append(item)
                        print('DRY_RUN_RESULT '+json.dumps(item, ensure_ascii=False), flush=True)
                    finally:
                        await page.close(); await context.close()
        finally:
            await browser.close()
    summary=OUT_DIR/f'case_{CASE_ID}_fresh_summary_{int(time.time())}.json'
    summary.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'DRY_RUN_SUMMARY {summary}', flush=True)
    if any(not r.get('ok_to_click_submit') for r in results): raise SystemExit(2)
asyncio.run(main())
