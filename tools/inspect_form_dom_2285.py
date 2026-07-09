
import asyncio, json, os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from src.sqlite_store import get_case
from src.web_automation import PROJECT_ROOT, start_browser_and_login, fill_basic_info, fill_asset_info, _bank_web_value
from tools.dry_run_web_entry_2285_fresh import sub_record, fill_tail
load_dotenv(PROJECT_ROOT/'API.env', override=True)
async def main():
    rec=get_case(PROJECT_ROOT/'data'/'cases.db',2285)
    sub=sub_record(rec,0)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        ctx=await browser.new_context(viewport={'width':1365,'height':900})
        page=await ctx.new_page()
        await start_browser_and_login(ctx,page=page)
        await fill_basic_info(page,sub); await fill_asset_info(page,sub); await fill_tail(page,sub)
        data=await page.evaluate("""() => {
          const norm=s=>(s||'').replace(/\s+/g,' ').trim();
          const items=[];
          document.querySelectorAll('input,textarea,select,ng-select,button,a,[role=button]').forEach((el,idx)=>{
            const r=el.getBoundingClientRect(); if(r.width<=0||r.height<=0) return;
            let label=''; let p=el; for(let i=0;i<4&&p;i++,p=p.parentElement){ label = norm(p.innerText||p.textContent); if(label) break; }
            items.push({idx, tag:el.tagName, id:el.id, name:el.getAttribute('name'), type:el.getAttribute('type'), role:el.getAttribute('role'), text:norm(el.innerText||el.textContent||el.value), value:el.value||'', cls:el.className||'', label:label.slice(0,180)});
          });
          return items;
        }""")
        print(json.dumps({'bank_target':_bank_web_value(str(sub.get('source') or '')), 'items':data}, ensure_ascii=False, indent=2))
        await browser.close()
asyncio.run(main())
