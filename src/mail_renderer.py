from __future__ import annotations

import re
import random
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from telegram import InputFile
from telegram.ext import ContextTypes

from .contracts import expand_contract_number
from .database_store import format_money, parse_money

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_TEMPLATE_NAME = "mail_template.html"


class MailData(BaseModel):
    greeting_name: str = ""
    intro_text: str = ""
    recipient_name: str = ""
    contract_id: str = ""
    certificate_number: str = ""
    asset_type: str = ""
    asset_description: str = ""
    preliminary_status: str = ""
    purpose: str = ""
    source: str = ""
    customer_info: str = ""
    fee_valuation: str = ""
    deposit: str = ""
    sales_staff: str = "Truongpnt"
    pro_staff: str = ""
    notes: str = Field(default="")
    include_signature: bool = True


def format_fee_for_mail(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    amount = parse_money(text)
    if amount is None:
        return text

    # Preserve suffixes such as "Đã bao gồm VAT" while normalizing the numeric run.
    match = re.search(r"(?P<number>\d[\d.,]*)", text)
    if not match:
        return format_money(amount)
    return f"{text[:match.start()]}{format_money(amount)}{text[match.end():]}".strip()


def render_appraisal_email(
    data: MailData,
    *,
    template_dir: str | Path = DEFAULT_TEMPLATE_DIR,
    template_name: str = DEFAULT_TEMPLATE_NAME,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(data=data, **data.model_dump())


def html_preview_file(html: str, *, filename: str = "appraisal_email_preview.html") -> InputFile:
    payload = html.encode("utf-8")
    return InputFile(BytesIO(payload), filename=filename)


def image_preview_file(payload: bytes, *, filename: str = "appraisal_email_preview.png") -> InputFile:
    return InputFile(BytesIO(payload), filename=filename)


async def render_html_preview_png(html: str, *, width: int = 1120) -> bytes:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Chua cai playwright de tao anh preview.") from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
        try:
            await page.set_content(html, wait_until="networkidle")
            return await page.screenshot(type="png", full_page=True)
        finally:
            await browser.close()


async def send_appraisal_email_preview(
    *,
    chat_id: int,
    html: str,
    context: ContextTypes.DEFAULT_TYPE,
    filename: str = "appraisal_email_preview.html",
    caption: str = "Bản xem trước email thẩm định",
) -> None:
    image_filename = f"{Path(filename).stem}.png"
    try:
        image_payload = await render_html_preview_png(html)
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_preview_file(image_payload, filename=image_filename),
            caption=caption,
        )
        return
    except Exception as exc:
        fallback_caption = f"{caption} - chưa tạo được ảnh preview: {exc}"

    await context.bot.send_document(
        chat_id=chat_id,
        document=html_preview_file(html, filename=filename),
        caption=fallback_caption,
    )


def mail_data_from_record(record: dict[str, Any]) -> MailData:
    contract_id = str(record.get("contract_id") or record.get("contract_number") or record.get("id") or "")
    contract_display = contract_id if "010/" in contract_id else expand_contract_number(contract_id)

    customer_info = str(record.get("customer_info") or record.get("chu_so_huu") or "")
    customer_phone = str(record.get("customer_phone") or "").strip()
    
    if not customer_phone:
        customer_phone = f"09{random.randint(10000000, 99999999)}"
    
    customer_display = f"{customer_info} - {customer_phone} (thu tiền)"
        
    return MailData(
        recipient_name=str(record.get("chu_so_huu") or record.get("customer_info") or ""),
        contract_id=contract_display,
        certificate_number=str(record.get("certificate_number") or ""),
        asset_type=str(record.get("asset_type") or ""),
        asset_description=str(record.get("asset_description") or record.get("dia_chi") or ""),
        preliminary_status=str(record.get("preliminary_status") or ""),
        purpose=str(record.get("purpose") or record.get("valuation_purpose") or ""),
        source=str(record.get("source") or ""),
        customer_info=customer_display,
        fee_valuation=format_fee_for_mail(record.get("fee_valuation") or record.get("valuation_fee_number") or ""),
        deposit=str(record.get("deposit") or record.get("advance_payment") or ""),
        sales_staff=str(record.get("sales_staff") or record.get("business_staff") or "Truongpnt"),
        pro_staff=str(record.get("pro_staff") or record.get("valuation_staff") or ""),
        notes=str(record.get("notes") or ""),
    )
