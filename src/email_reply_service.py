

import imaplib
import email
from email.header import decode_header
import smtplib
import html
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
import os
import re
import asyncio
from pathlib import Path
from .mail_service import load_gmail_smtp_settings, _parse_email_list, _clean_header

DEFAULT_PHATHANH_RECIPIENT = (
    "CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI\n"
    "Địa chỉ: 90/60/3 Trường Chinh, phường Pleiku, tỉnh Gia Lai\n"
    "Điện thoại 0905226968"
)


def gemini_keys_with_backups(primary_key: str | None = None, backup_keys: str | None = None) -> list[str]:
    keys: list[str] = []
    backup_value = backup_keys if backup_keys is not None else os.getenv("GEMINI_BACKUP_KEYS", "")
    for key in [primary_key or os.getenv("GEMINI_API_KEY", ""), *backup_value.split(",")]:
        clean_key = str(key or "").strip()
        if clean_key and clean_key not in keys:
            keys.append(clean_key)
    return keys


def build_phathanh_browser_tools(html_body: str):
    from browser_use import Tools
    from browser_use.agent.views import ActionResult

    tools = Tools()

    @tools.action("Insert the prepared certificate release HTML into the currently open OWA reply editor.")
    async def insert_phathanh_html(browser_session):
        page = await browser_session.must_get_current_page()
        result = await page.evaluate(
            """
            async (html) => {
              const isVisible = (el) => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
              };

              const candidates = Array.from(document.querySelectorAll([
                '[contenteditable="true"]',
                '[role="textbox"]',
                '[aria-label*="Nội dung"]',
                '[aria-label*="Message body"]',
                '[aria-label*="body"]'
              ].join(','))).filter(isVisible);

              let editor = null;
              const active = document.activeElement;
              if (active && candidates.includes(active)) {
                editor = active;
              }
              if (!editor && active && active.closest) {
                editor = candidates.find((candidate) => candidate.contains(active) || active.contains(candidate));
              }
              if (!editor) {
                editor = candidates[candidates.length - 1];
              }
              if (!editor) {
                return { ok: false, reason: 'reply editor not found' };
              }

              editor.focus();
              const selection = window.getSelection();
              const range = document.createRange();
              range.selectNodeContents(editor);
              range.collapse(false);
              selection.removeAllRanges();
              selection.addRange(range);

              let inserted = false;
              try {
                inserted = document.execCommand('insertHTML', false, html);
              } catch (error) {
                inserted = false;
              }
              if (!inserted) {
                editor.innerHTML = html;
              }

              editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertHTML', data: html }));
              editor.dispatchEvent(new Event('change', { bubbles: true }));

              const renderedText = (editor.innerText || editor.textContent || '').trim();
              return {
                ok: renderedText.includes('Dear all') || editor.innerHTML.includes('Dear all'),
                reason: renderedText.slice(0, 160),
              };
            }
            """,
            html_body,
        )
        if result.get("ok"):
            return ActionResult(extracted_content="Inserted phathanh HTML into the OWA reply editor.")
        return ActionResult(error=f"Could not insert phathanh HTML: {result.get('reason')}")

    return tools


def format_phathanh_recipient_html(recipient: str | None) -> str:
    from src.email_utils import format_recipient_info

    recipient_clean = format_recipient_info(recipient or DEFAULT_PHATHANH_RECIPIENT)
    recipient_html = html.escape(recipient_clean).replace("\n", "<br>")
    if "Địa chỉ:" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ:", "<strong>Địa chỉ:</strong>")
    elif "Địa chỉ" in recipient_html:
        recipient_html = recipient_html.replace("Địa chỉ", "<strong>Địa chỉ</strong>")

    if "Điện thoại:" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại:", "<strong>Điện thoại:</strong>")
    elif "Điện thoại" in recipient_html:
        recipient_html = recipient_html.replace("Điện thoại", "<strong>Điện thoại</strong>")
    return recipient_html


def phathanh_send_mode() -> str:
    return os.getenv("PHATHANH_SEND_MODE", "").strip().casefold()


def build_phathanh_email_html(case: dict, recipient: str | None = None) -> str:
    from datetime import datetime, timedelta

    template_path = Path("src/templates/phathanh_template.html")
    if not template_path.exists():
        template_path = Path(__file__).parent / "templates" / "phathanh_template.html"
    if not template_path.exists():
        raise FileNotFoundError("Thiáº¿u file template: src/templates/phathanh_template.html")

    html_template = template_path.read_text(encoding="utf-8")

    now = datetime.now()
    date_receive = (now + timedelta(days=1)).strftime("%d/%m/%Y")
    date_payment = now.strftime("%d/%m/%Y")

    signature = os.getenv("MAIL_SIGNATURE", "TrÃ¢n trá»ng,<br>Century Appraisal")

    customer_extra_html = ""
    if case.get("customer_type") == "individual":
        citizen_id = case.get("citizen_id")
        if citizen_id:
            customer_extra_html = f'<br><i style="color: #7f8c8d; font-size: 12px;">(CCCD: {citizen_id})</i>'

    recipient_html = format_phathanh_recipient_html(recipient)

    replacements = {
        "{{ customer_name }}": case.get("customer_info", case.get("owner_name", "N/A")),
        "{{ customer_address }}": case.get("customer_address", case.get("dia_chi_thua_dat", "N/A")),
        "{{ customer_extra_html }}": customer_extra_html,
        "{{ recipient_info }}": recipient_html,
        "{{ date_receive }}": date_receive,
        "{{ date_payment }}": date_payment,
        "{{ personal_note }}": "",
        "{{ email_signature }}": signature,
    }

    html_body = html_template
    for placeholder, value in replacements.items():
        html_body = html_body.replace(placeholder, str(value))
    return html_body


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
    from src.oauth2_service import get_enabled_oauth_provider, send_email_via_oauth2
    from email.utils import parseaddr
    
    provider = get_enabled_oauth_provider()
        
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
            raise RuntimeError(f"Gửi mail phát hành qua {provider.upper()} OAuth2 thất bại: {exc}") from exc
            
    return await asyncio.to_thread(_send_phathanh_reply_sync, original_mail, html_body, settings)


async def send_phathanh_email_for_case(case: dict, recipient: str = None) -> str:
    """Gửi email phát hành chứng thư cho một hồ sơ."""
    contract_number = case.get("contract_number")
    if not contract_number:
        raise ValueError("Hồ sơ không có số hợp đồng.")

    html_body = build_phathanh_email_html(case, recipient)
    if phathanh_send_mode() == "playwright":
        return await send_phathanh_email_via_playwright_raw(case, html_body)

    from src.oauth2_service import get_enabled_oauth_provider, fetch_emails_via_oauth2, send_email_via_oauth2

    provider = get_enabled_oauth_provider()

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
            raise RuntimeError(f"Đọc mail gốc qua {provider.upper()} OAuth2 thất bại: {exc}") from exc

    if provider and not original_mail:
        raise RuntimeError(f"Không tìm thấy email nào trên {provider.upper()} có tiêu đề chứa số hợp đồng: {contract_number}.")
    if not provider:
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
            
    recipient_html = format_phathanh_recipient_html(recipient)
    
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
            raise RuntimeError(f"Gửi mail phát hành qua {provider.upper()} OAuth2 thất bại: {exc}") from exc

    if not success:
        success = await send_phathanh_reply(original_mail, html_body, settings)
        if not success:
            raise RuntimeError("Gửi email SMTP thất bại.")
        
    return original_mail.get("to") or original_mail.get("from")


async def send_phathanh_email_via_browser_use(case_data: dict, html_body: str) -> str:
    """Gửi email phát hành chứng thư thông qua Webmail (OWA/Outlook) bằng Browser Use và Gemini API."""
    import os
    import asyncio
    from browser_use import Agent, Browser, ChatGoogle
    api_keys = gemini_keys_with_backups()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    user_data_dir = os.getenv("CHROME_USER_DATA_DIR")
    webmail_url = os.getenv("WEBMAIL_URL", "https://owa.cengroup.vn/").strip()
    
    contract_number = str(case_data.get("contract_number") or "").strip()
    if not contract_number:
        raise ValueError("Hồ sơ không có số hợp đồng để tìm kiếm email.")
        
    if not api_keys:
        raise RuntimeError("Thiếu biến môi trường GEMINI_API_KEY để chạy AI Agent.")

    llm = ChatGoogle(
        model=model,
        api_key=api_keys[0]
    )
    fallback_llm = None
    if len(api_keys) > 1:
        fallback_llm = ChatGoogle(
            model=model,
            api_key=api_keys[1]
        )

    # Khởi tạo Browser ẩn danh (headless=True trên Linux/VPS, False trên Windows để test trực quan)
    is_headless = os.getenv("PLAYWRIGHT_HEADLESS", "true" if os.name != "nt" else "false").strip().casefold() in ("true", "1", "yes")
    
    # Chrome arguments required for Linux root context execution
    chrome_args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    
    browser_kwargs = {
        "headless": is_headless,
        "args": chrome_args,
        "enable_default_extensions": False
    }
    if user_data_dir and os.path.exists(user_data_dir):
        browser_kwargs["user_data_dir"] = user_data_dir

    browser = Browser(**browser_kwargs)
    tools = build_phathanh_browser_tools(html_body)
    
    # Prompt chỉ dẫn chi tiết cho AI Agent điều khiển OWA
    prompt = (
        f"Hãy thực hiện các bước sau để gửi email phát hành chứng thư:\n"
        f"1. Truy cập vào trang Webmail {webmail_url}.\n"
        f"2. Nếu chưa đăng nhập, sử dụng tài khoản '{username}' và mật khẩu '{password}' để đăng nhập.\n"
        f"3. Nhập từ khóa số hợp đồng '{contract_number}' vào ô tìm kiếm (Search) ở trên cùng và nhấn Enter.\n"
        f"4. Click mở email mới nhất trong kết quả tìm kiếm.\n"
        f"5. Tìm và click nút 'Trả lời tất cả' (Reply All).\n"
        f"6. Tìm ô soạn thảo nội dung trả lời (thường là ô nhập liệu contenteditable='true' hoặc role='textbox').\n"
        f"7. Nhập nội dung sau vào ô soạn thảo: 'Dear all, Mọi người cho phát hành chứng thư giúp mình nhé, mình cảm ơn!' "
        f"và dán bảng thông tin này vào. Để dán bảng thông tin một cách chuẩn xác nhất, hãy thực hiện chạy JavaScript (execute_javascript) để đặt `innerHTML` của ô soạn thảo bằng đoạn mã HTML sau:\n"
        f"\"\"\"{html_body}\"\"\"\n"
        f"8. Sau khi đã chèn thành công nội dung và bảng thông tin xuất hiện chính xác trên giao diện, hãy click nút 'Gửi' (Send) để hoàn thành gửi mail."
    )

    prompt = (
        f"Use OWA Webmail at {webmail_url} to send the certificate release reply.\n"
        f"1. Log in with the username '{username}' and password '{password}' if needed.\n"
        f"2. Search for the email whose subject contains this contract number: {contract_number}.\n"
        f"3. Click on the first/newest email item in the search results list to open its details. Wait for the email details pane to load completely.\n"
        f"4. Look for and click the 'Reply All' button (or 'Trả lời tất cả' in Vietnamese) inside the opened email pane.\n"
        f"5. Once the reply editor opens, click the editor body to focus it, then call the `insert_phathanh_html` tool exactly once to insert the prepared release content.\n"
        f"6. Confirm the content is inserted correctly, then click the 'Send' button (or 'Gửi' in Vietnamese) to send the email."
    )

    try:
        agent = None
        try:
            agent = Agent(
                task=prompt,
                llm=llm,
                fallback_llm=fallback_llm,
                browser=browser,
                tools=tools
            )
            history = await agent.run()
            if not history or not history.is_successful():
                raise RuntimeError("AI Agent execution was not successful (likely rate limited or failed).")
        except Exception as e:
            # Catch inner exceptions (like rate limits / API errors during run)
            raise e
        finally:
            try:
                await browser.stop()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to stop browser: {e}")
    except Exception as agent_exc:
        import logging
        logging.getLogger(__name__).error(f"Browser Use agent failed: {agent_exc}. Falling back to raw Playwright flow...")
        try:
            # Ensure the browser session is fully stopped before starting fallback
            await browser.stop()
        except Exception:
            pass
        return await send_phathanh_email_via_playwright_raw(case_data, html_body)
        
    return case_data.get("to") or case_data.get("from") or "Webmail AI Agent"


async def send_phathanh_email_via_playwright_raw(case_data: dict, html_body: str) -> str:
    """Fallback method using raw Playwright commands to reply to the certificate release email."""
    import os
    import asyncio
    from playwright.async_api import async_playwright
    
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    user_data_dir = os.getenv("CHROME_USER_DATA_DIR")
    webmail_url = os.getenv("WEBMAIL_URL", "https://owa.cengroup.vn/").strip()
    is_headless = os.getenv("PLAYWRIGHT_HEADLESS", "true" if os.name != "nt" else "false").strip().casefold() in ("true", "1", "yes")
    
    contract_number = str(case_data.get("contract_number") or "").strip()
    if not contract_number:
        raise ValueError("Hồ sơ không có số hợp đồng để tìm kiếm email.")
        
    chrome_args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    
    print(f"[Playwright Raw Fallback] Starting raw Playwright flow for contract {contract_number}")
    
    async with async_playwright() as p:
        if user_data_dir and os.path.exists(user_data_dir):
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=is_headless,
                args=chrome_args,
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(
                headless=is_headless,
                args=chrome_args,
            )
            context = await browser.new_context()
            page = await context.new_page()
            
        try:
            # 1. Navigate to the login page
            print(f"[Playwright Raw Fallback] Navigating to {webmail_url}")
            await page.goto(webmail_url, timeout=60000)
            await page.wait_for_load_state("load")
            
            # Check if we are already logged in
            username_selector = "input#username, input[name='username'], input[type='email'], input[type='text']"
            try:
                await page.wait_for_selector(username_selector, timeout=5000)
                needs_login = True
            except Exception:
                needs_login = False
                
            if needs_login:
                print("[Playwright Raw Fallback] Login form detected. Logging in...")
                await page.fill("input#username, input[name='username'], input[type='email']", username)
                await page.fill("input#password, input[name='password'], input[type='password']", password)
                signin_btn_selector = "input[type='submit'], button[type='submit'], button:has-text('Sign in'), button:has-text('Đăng nhập'), div[role='button']:has-text('Sign in')"
                await page.click(signin_btn_selector)
                print("[Playwright Raw Fallback] Submitted login form. Waiting for navigation/dashboard...")
                await page.wait_for_load_state("networkidle", timeout=15000)
            else:
                print("[Playwright Raw Fallback] Already logged in or login form not visible.")

            # 2. Wait for search input
            search_selector = "input[placeholder*='Tìm kiếm'], input[placeholder*='Search'], input[aria-label*='Search'], input[aria-label*='Tìm kiếm'], input#sb"
            print("[Playwright Raw Fallback] Waiting for search input...")
            search_input = await page.wait_for_selector(search_selector, timeout=30000)
            
            # 3. Input contract number and press Enter
            print(f"[Playwright Raw Fallback] Inputting contract number: {contract_number}")
            await search_input.click()
            await search_input.press("Control+A")
            await search_input.press("Delete")
            await search_input.fill(contract_number)
            await search_input.press("Enter")
            
            # Wait for search results
            print("[Playwright Raw Fallback] Waiting for search results to load...")
            await page.wait_for_timeout(5000)
            
            # Click first search result
            item_selector = "div[role='listitem'], div[role='option'], div.customListItem, tr.read, tr.unread, div[aria-label*='Message List'] div[role='button']"
            try:
                first_item = await page.wait_for_selector(item_selector, timeout=15000)
                print("[Playwright Raw Fallback] Clicking the first search result...")
                await first_item.click()
            except Exception as e:
                print(f"[Playwright Raw Fallback] Warning: Could not find mail item by selector: {e}. Trying fallback click on list...")
                await page.click("div[role='listitem'] >> nth=0")
                
            await page.wait_for_timeout(3000)
            
            # 4. Click 'Reply All'
            reply_all_selector = (
                "button:has-text('Reply All'), button:has-text('Trả lời tất cả'), "
                "[aria-label*='Reply all'], [aria-label*='Trả lời tất cả'], "
                "[aria-label*='Reply All'], "
                "[title*='Reply all'], [title*='Trả lời tất cả'], "
                "[title*='Reply All'], "
                "div[role='button']:has-text('Reply All'), div[role='button']:has-text('Trả lời tất cả'), "
                "span:has-text('Reply All'), span:has-text('Trả lời tất cả')"
            )
            print("[Playwright Raw Fallback] Waiting for Reply All button...")
            reply_all_btn = await page.wait_for_selector(reply_all_selector, timeout=20000)
            print("[Playwright Raw Fallback] Clicking Reply All button...")
            await reply_all_btn.click()
            
            await page.wait_for_timeout(3000)
            
            # 5. Use JS to insert the html_body into the active editor
            editor_selector = "[contenteditable='true'], [role='textbox'], [aria-label*='Nội dung'], [aria-label*='Message body'], [aria-label*='body']"
            print("[Playwright Raw Fallback] Waiting for reply editor...")
            await page.wait_for_selector(editor_selector, timeout=20000)
            
            print("[Playwright Raw Fallback] Evaluating JS to insert HTML into editor...")
            result = await page.evaluate(
                """
                async (html) => {
                  const isVisible = (el) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                  };

                  const candidates = Array.from(document.querySelectorAll([
                    '[contenteditable="true"]',
                    '[role="textbox"]',
                    '[aria-label*="Nội dung"]',
                    '[aria-label*="Message body"]',
                    '[aria-label*="body"]'
                  ].join(','))).filter(isVisible);

                  let editor = null;
                  const active = document.activeElement;
                  if (active && candidates.includes(active)) {
                    editor = active;
                  }
                  if (!editor && active && active.closest) {
                    editor = candidates.find((candidate) => candidate.contains(active) || active.contains(candidate));
                  }
                  if (!editor) {
                    editor = candidates[candidates.length - 1];
                  }
                  if (!editor) {
                    return { ok: false, reason: 'reply editor not found' };
                  }

                  editor.focus();
                  const selection = window.getSelection();
                  const range = document.createRange();
                  range.selectNodeContents(editor);
                  range.collapse(false);
                  selection.removeAllRanges();
                  selection.addRange(range);

                  let inserted = false;
                  try {
                    inserted = document.execCommand('insertHTML', false, html);
                  } catch (error) {
                    inserted = false;
                  }
                  if (!inserted) {
                    editor.innerHTML = html;
                  }

                  editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertHTML', data: html }));
                  editor.dispatchEvent(new Event('change', { bubbles: true }));

                  const renderedText = (editor.innerText || editor.textContent || '').trim();
                  return {
                    ok: renderedText.includes('Dear all') || editor.innerHTML.includes('Dear all'),
                    reason: renderedText.slice(0, 160),
                  };
                }
                """,
                html_body
            )
            print(f"[Playwright Raw Fallback] Editor insertion result: {result}")
            await page.wait_for_timeout(2000)
            
            # 6. Click Send button
            send_btn_selector = (
                "button:has-text('Send'), button:has-text('Gửi'), "
                "[aria-label*='Send'], [aria-label*='Gửi'], "
                "[title*='Send'], [title*='Gửi'], "
                "div[role='button']:has-text('Send'), div[role='button']:has-text('Gửi'), "
                "span:has-text('Send'), span:has-text('Gửi')"
            )
            print("[Playwright Raw Fallback] Locating Send button...")
            send_btn = await page.wait_for_selector(send_btn_selector, timeout=15000)
            print("[Playwright Raw Fallback] Clicking Send button...")
            await send_btn.click()
            
            await page.wait_for_timeout(5000)
            print("[Playwright Raw Fallback] Email sent successfully.")
            
        finally:
            await context.close()
            
    return case_data.get("to") or case_data.get("from") or "Webmail Playwright Raw Fallback"
