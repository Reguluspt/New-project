

import imaplib
import email
from email.header import decode_header
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
import os
import re
import asyncio
from pathlib import Path
from .mail_service import load_gmail_smtp_settings, _parse_email_list, _clean_header

def _decode_header_str(header_value):
    if not header_value:
        return ""
    try:
        decoded_parts = decode_header(str(header_value))
        parts = []
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                parts.append(content.decode(encoding or 'utf-8', errors='replace'))
            else:
                parts.append(str(content))
        decoded = "".join(parts)
    except Exception:
        decoded = str(header_value)
    
    # Repair mojibake if any (e.g. UTF-8 interpreted as Latin-1 / CP1252)
    try:
        if any(c in decoded for c in "Æ°á»›º¡"):
            return decoded.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    try:
        if any(c in decoded for c in "Æ°á»›º¡"):
            return decoded.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return decoded

def _find_latest_email_by_subject_sync(contract_number: str):
    settings = load_gmail_smtp_settings()
    # imap.gmail.com
    imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
    
    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(settings.username, settings.password)
        mail.select("inbox")
        
        # Search for contract number in subject
        search_query = f'SUBJECT "{contract_number}"'
        status, messages = mail.search(None, search_query)
        
        if status != "OK" or not messages[0]:
            mail.logout()
            return None
        
        # Get latest message ID
        msg_ids = messages[0].split()
        latest_id = msg_ids[-1]
        
        # Fetch headers and Gmail thread ID (X-GM-THRID) for proper threading
        fetch_items = "(RFC822.HEADER)"
        if imap_host == "imap.gmail.com":
            fetch_items = "(X-GM-THRID RFC822.HEADER)"
        status, data = mail.fetch(latest_id, fetch_items)
        if status != "OK":
            mail.logout()
            return None

        # Extract Gmail thread ID from IMAP response metadata
        thread_id = ""
        if imap_host == "imap.gmail.com" and data[0][0]:
            import re as _re
            thrid_match = _re.search(rb'X-GM-THRID\s+(\d+)', data[0][0])
            if thrid_match:
                # Convert decimal X-GM-THRID to hex (Gmail API threadId format)
                thread_id = format(int(thrid_match.group(1)), 'x')

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        result = {
            "msg_id": _clean_header(msg.get("Message-ID")),
            "subject": _clean_header(_decode_header_str(msg.get("Subject"))),
            "from": _clean_header(_decode_header_str(msg.get("From"))),
            "to": _clean_header(_decode_header_str(msg.get("To"))),
            "cc": _clean_header(_decode_header_str(msg.get("Cc"))),
            "references": _clean_header(msg.get("References", "")),
            "thread_id": thread_id,
        }
        
        mail.logout()
        return result
    except Exception as e:
        print(f"IMAP Error: {e}")
        return None

async def find_latest_email_by_subject(contract_number: str):
    return await asyncio.to_thread(_find_latest_email_by_subject_sync, contract_number)

def _send_phathanh_reply_sync(original_mail, html_body, settings):
    msg = EmailMessage()
    
    # Subject: Re: Original Subject
    orig_subject = original_mail["subject"]
    if not orig_subject.lower().startswith("re:"):
        msg["Subject"] = f"Re: {orig_subject}"
    else:
        msg["Subject"] = orig_subject
        
    # Headers for threading
    msg["In-Reply-To"] = original_mail["msg_id"]
    references = original_mail["references"]
    msg["References"] = f"{references} {original_mail['msg_id']}".strip()
    
    # Recipients (Reply All logic)
    orig_from = original_mail["from"]
    orig_to = original_mail["to"] or ""
    orig_cc = original_mail["cc"] or ""
    
    all_to = _parse_email_list(orig_from)
    all_cc = _parse_email_list(orig_to) + _parse_email_list(orig_cc)
    
    # Deduplicate and remove self
    self_email = settings.username.lower()
    
    final_to = []
    seen = set()
    for addr in all_to:
        email_addr = parseaddr(addr)[1].lower()
        if email_addr and email_addr != self_email and email_addr not in seen:
            final_to.append(addr)
            seen.add(email_addr)
            
    final_cc = []
    for addr in all_cc:
        email_addr = parseaddr(addr)[1].lower()
        if email_addr and email_addr != self_email and email_addr not in seen:
            final_cc.append(addr)
            seen.add(email_addr)
            
    if not final_to:
        final_to = [orig_from] # Fallback
        
    msg["From"] = settings.mail_from
    msg["To"] = ", ".join(final_to)
    if final_cc:
        msg["Cc"] = ", ".join(final_cc)
        
    msg.set_content("Vui lòng xem nội dung trong định dạng HTML.")
    msg.add_alternative(html_body, subtype="html")
    
    # Inline image embedding (CID) for the logo
    parts = msg.get_payload()
    html_part = parts[-1]
    
    logo_path = Path(__file__).resolve().parent / "templates" / "logo.jpg"
    if logo_path.exists():
        import mimetypes
        ctype, encoding = mimetypes.guess_type(str(logo_path))
        if ctype is None or encoding is not None:
            ctype = 'image/jpeg'
        maintype, subtype = ctype.split('/', 1)
        
        try:
            with open(logo_path, 'rb') as f:
                img_data = f.read()
            html_part.add_related(img_data, maintype=maintype, subtype=subtype, cid='<logo_cenvalue>', filename='logo.jpg')
        except Exception as img_err:
            print(f"Error embedding logo image: {img_err}")
    
    # Send
    try:
        with smtplib.SMTP(settings.host, settings.port) as server:
            server.starttls()
            server.login(settings.username, settings.password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

async def send_phathanh_reply(original_mail, html_body, settings):
    from src.oauth2_service import is_oauth_enabled, send_email_via_oauth2
    from email.utils import parseaddr
    
    provider = None
    if is_oauth_enabled("google"):
        provider = "google"
    elif is_oauth_enabled("outlook"):
        provider = "outlook"
        
    if provider:
        try:
            # Recipients (Reply All logic)
            orig_from = original_mail["from"]
            orig_to = original_mail["to"] or ""
            orig_cc = original_mail["cc"] or ""
            
            all_to = _parse_email_list(orig_from)
            all_cc = _parse_email_list(orig_to) + _parse_email_list(orig_cc)
            
            self_email = (settings.username or "").lower()
            
            final_to = []
            seen = set()
            for addr in all_to:
                email_addr = parseaddr(addr)[1].lower()
                if email_addr and email_addr != self_email and email_addr not in seen:
                    final_to.append(addr)
                    seen.add(email_addr)
                    
            final_cc = []
            for addr in all_cc:
                email_addr = parseaddr(addr)[1].lower()
                if email_addr and email_addr != self_email and email_addr not in seen:
                    final_cc.append(addr)
                    seen.add(email_addr)
                    
            if not final_to:
                final_to = [orig_from] # Fallback
                
            orig_subject = original_mail["subject"]
            subject = orig_subject if orig_subject.lower().startswith("re:") else f"Re: {orig_subject}"

            print(f"Replying to email using OAuth2 API for provider: {provider}")
            await send_email_via_oauth2(
                provider=provider,
                from_email=_clean_header(settings.mail_from or settings.username),
                to_email=", ".join(final_to),
                subject=subject,
                html_body=html_body,
                cc_emails=final_cc,
                reply_to_msg_id=original_mail["msg_id"],
                references=original_mail["references"],
                thread_id=original_mail.get("thread_id") or None,
            )
            return True
        except Exception as exc:
            print(f"OAuth2 send reply failed: {exc}, falling back to SMTP.")
            
    return await asyncio.to_thread(_send_phathanh_reply_sync, original_mail, html_body, settings)


async def send_phathanh_email_for_case(case: dict, recipient: str = None) -> str:
    """Gửi email phát hành chứng thư cho một hồ sơ."""
    from datetime import datetime, timedelta
    
    contract_number = case.get("contract_number")
    if not contract_number:
        raise ValueError("Hồ sơ không có số hợp đồng.")

    from src.oauth2_service import is_oauth_enabled, fetch_emails_via_oauth2, send_email_via_oauth2
    
    provider = None
    if is_oauth_enabled("google"):
        provider = "google"
    elif is_oauth_enabled("outlook"):
        provider = "outlook"

    original_mail = None
    if provider:
        try:
            print(f"Finding original email for {contract_number} via OAuth2 API for provider: {provider}")
            # Search ALL emails (not just unread) to find the original thread
            oauth_emails = await fetch_emails_via_oauth2(
                provider, query_contract=contract_number, limit=5, unread_only=False
            )
            if oauth_emails:
                # Get latest raw email
                latest_item = oauth_emails[0]
                raw_email = latest_item["raw_bytes"]
                msg = email.message_from_bytes(raw_email)
                original_mail = {
                    "msg_id": _clean_header(msg.get("Message-ID")),
                    "subject": _clean_header(_decode_header_str(msg.get("Subject"))),
                    "from": _clean_header(_decode_header_str(msg.get("From"))),
                    "to": _clean_header(_decode_header_str(msg.get("To"))),
                    "cc": _clean_header(_decode_header_str(msg.get("Cc"))),
                    "references": _clean_header(msg.get("References", "")),
                    "thread_id": latest_item.get("thread_id", ""),
                }
                print(f"Found original email: subject='{original_mail['subject']}', thread_id='{original_mail.get('thread_id', '')}', msg_id='{original_mail['msg_id']}'")
        except Exception as exc:
            print(f"OAuth2 email lookup failed: {exc}, falling back to IMAP.")
            provider = None

    if not provider or not original_mail:
        # 1. Tìm mail cũ bằng IMAP (truyền thống)
        original_mail = await find_latest_email_by_subject(contract_number)
        if not original_mail:
            raise RuntimeError(f"Không tìm thấy email nào có tiêu đề chứa số hợp đồng: {contract_number}. Vui lòng gửi email yêu cầu định giá trước.")
        
    # 2. Chuẩn bị dữ liệu HTML
    template_path = Path("src/templates/phathanh_template.html")
    if not template_path.exists():
        template_path = Path(__file__).parent / "templates" / "phathanh_template.html"
    if not template_path.exists():
        raise FileNotFoundError("Thiếu file template: src/templates/phathanh_template.html")
        
    html_template = template_path.read_text(encoding="utf-8")
    
    # Tính toán ngày
    now = datetime.now()
    date_receive = (now + timedelta(days=1)).strftime("%d/%m/%Y")
    date_payment = now.strftime("%d/%m/%Y")
    
    # Lấy chữ ký từ môi trường
    signature = os.getenv("MAIL_SIGNATURE", "Trân trọng,<br>Century Appraisal")
    
    # Xử lý thông tin cá nhân/tổ chức
    customer_extra_html = ""
    if case.get("customer_type") == "individual":
        citizen_id = case.get('citizen_id')
        if citizen_id:
            customer_extra_html = f'<br><i style="color: #7f8c8d; font-size: 12px;">(CCCD: {citizen_id})</i>'
            
    # Bold the labels "Địa chỉ" and "Điện thoại" in recipient details
    if not recipient:
        recipient = (
            "CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI\n"
            "Địa chỉ: 90/60/3 Trường Chinh, phường Pleiku, tỉnh Gia Lai\n"
            "Điện thoại 0905226968"
        )
    
    from src.email_utils import format_recipient_info
    recipient_clean = format_recipient_info(recipient)
    recipient_html = recipient_clean.replace("\n", "<br>")
    if "Địa chỉ:" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ:", "<strong>Địa chỉ:</strong>")
    elif "Địa chỉ" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ", "<strong>Địa chỉ</strong>")
        
    if "Điện thoại:" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại:", "<strong>Điện thoại:</strong>")
    elif "Điện thoại" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại", "<strong>Điện thoại</strong>")
    
    replacements = {
        "{{ customer_name }}": case.get("customer_info", case.get("owner_name", "N/A")),
        "{{ customer_address }}": case.get("customer_address", case.get("dia_chi_thua_dat", "N/A")),
        "{{ customer_extra_html }}": customer_extra_html,
        "{{ recipient_info }}": recipient_html,
        "{{ date_receive }}": date_receive,
        "{{ date_payment }}": date_payment,
        "{{ personal_note }}": "",
        "{{ email_signature }}": signature
    }
    
    html_body = html_template
    for placeholder, value in replacements.items():
        html_body = html_body.replace(placeholder, str(value))
        
    # 3. Gửi mail
    settings = load_gmail_smtp_settings()
    
    success = False
    if provider:
        try:
            # Recipients (Reply All logic)
            orig_from = original_mail["from"]
            orig_to = original_mail["to"] or ""
            orig_cc = original_mail["cc"] or ""
            
            all_to = _parse_email_list(orig_from)
            all_cc = _parse_email_list(orig_to) + _parse_email_list(orig_cc)
            
            self_email = (settings.username or "").lower()
            
            final_to = []
            seen = set()
            for addr in all_to:
                email_addr = parseaddr(addr)[1].lower()
                if email_addr and email_addr != self_email and email_addr not in seen:
                    final_to.append(addr)
                    seen.add(email_addr)
                    
            final_cc = []
            for addr in all_cc:
                email_addr = parseaddr(addr)[1].lower()
                if email_addr and email_addr != self_email and email_addr not in seen:
                    final_cc.append(addr)
                    seen.add(email_addr)
                    
            if not final_to:
                final_to = [orig_from] # Fallback
                
            orig_subject = original_mail["subject"]
            subject = orig_subject if orig_subject.lower().startswith("re:") else f"Re: {orig_subject}"

            thread_id = original_mail.get("thread_id") or None
            print(f"Replying to email using OAuth2 API for provider: {provider}, thread_id={thread_id}")
            await send_email_via_oauth2(
                provider=provider,
                from_email=_clean_header(settings.mail_from or settings.username),
                to_email=", ".join(final_to),
                subject=subject,
                html_body=html_body,
                cc_emails=final_cc,
                reply_to_msg_id=original_mail["msg_id"],
                references=original_mail["references"],
                thread_id=thread_id,
            )
            success = True
        except Exception as exc:
            print(f"OAuth2 send reply failed: {exc}, falling back to SMTP.")
            success = False

    if not success:
        success = await send_phathanh_reply(original_mail, html_body, settings)
        if not success:
            raise RuntimeError("Gửi email SMTP thất bại.")
        
    return original_mail.get("to") or original_mail.get("from")
