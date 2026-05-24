import logging
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class SoboEmailResult:
    success: bool
    user_message: str = ""
    technical_error: str = ""

    def __bool__(self) -> bool:
        return self.success


def _load_env() -> None:
    load_dotenv(os.path.join(PROJECT_ROOT, "API.env"), override=True)


def _smtp_auth_error_message() -> str:
    return (
        "Gmail tu choi dang nhap SMTP. Vui long kiem tra lai tai khoan gui "
        "va tao/cap nhat Gmail App Password trong API.env."
    )


def _attach_sobo_logo(msg: EmailMessage) -> None:
    logo_path = os.path.join(PROJECT_ROOT, "src", "templates", "logo.jpg")
    if not os.path.exists(logo_path):
        return
    try:
        with open(logo_path, "rb") as logo_file:
            msg.get_payload()[1].add_related(
                logo_file.read(),
                maintype="image",
                subtype="jpeg",
                cid="<cenvalue_logo>",
                filename="logo.jpg",
            )
    except Exception as exc:
        logger.error(f"Loi khi dinh kem logo email so bo: {exc}")


async def send_sobo_email_with_result(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    attachment_path: str | list[str] = None,
    cc_emails: list[str] = None,
) -> SoboEmailResult:
    _load_env()
    
    attachment_paths = []
    if attachment_path:
        if isinstance(attachment_path, list):
            attachment_paths = attachment_path
        else:
            attachment_paths = [attachment_path]
    
    # --- TÍCH HỢP OAUTH2 ---
    from .oauth2_service import is_oauth_enabled, get_valid_access_token_async
    
    provider = None
    if is_oauth_enabled("google"):
        provider = "google"
    elif is_oauth_enabled("outlook"):
        provider = "outlook"
        
    user = os.getenv("SMTP_USERNAME", os.getenv("MAIL_USERNAME", os.getenv("EMAIL_USER", ""))).strip()
    mail_from_name = os.getenv("MAIL_FROM", "").strip()
    
    if provider:
        try:
            print(f"Sending sobo email using OAuth2 API for provider: {provider}")
            
            # Xây dựng đối tượng MIME message chuẩn chứa đính kèm và logo
            msg = EmailMessage()
            msg["Subject"] = subject
            if mail_from_name and "@" not in mail_from_name:
                msg["From"] = formataddr((mail_from_name, user))
            else:
                msg["From"] = mail_from_name or user
            msg["To"] = to_email
            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)
            msg.set_content(body)
            
            if html_body:
                msg.add_alternative(html_body, subtype="html")
                _attach_sobo_logo(msg)
                        
            for path in attachment_paths:
                if path and os.path.exists(path):
                    filename = os.path.basename(path)
                    with open(path, "rb") as f:
                        file_data = f.read()
                    maintype = "application"
                    subtype = "octet-stream"
                    if filename.lower().endswith(".pdf"):
                        subtype = "pdf"
                    elif filename.lower().endswith((".jpg", ".jpeg", ".png")):
                        maintype = "image"
                        subtype = "jpeg" if filename.lower().endswith(".jpg") else filename.lower().split(".")[-1]
                    msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)
                
            access_token = await get_valid_access_token_async(provider)
            
            if provider == "google":
                import base64
                import httpx
                raw_bytes = msg.as_bytes()
                raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    }
                    send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                    response = await client.post(send_url, headers=headers, json={"raw": raw_b64})
                    if response.status_code not in [200, 201]:
                        raise RuntimeError(f"Gửi sobo qua Gmail API thất bại: {response.text}")
                return SoboEmailResult(True)
                
            elif provider == "outlook":
                import base64
                import httpx
                to_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in to_email.split(",") if addr.strip()]
                cc_recipients = []
                if cc_emails:
                    cc_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in cc_emails if addr.strip()]
                    
                attachments_payload = []
                if html_body:
                    logo_path = os.path.join(PROJECT_ROOT, "src", "templates", "logo.jpg")
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as logo_file:
                            logo_bytes = base64.b64encode(logo_file.read()).decode("utf-8")
                        attachments_payload.append({
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": "logo.jpg",
                            "contentType": "image/jpeg",
                            "contentBytes": logo_bytes,
                            "isInline": True,
                            "contentId": "cenvalue_logo",
                        })
                for path in attachment_paths:
                    if path and os.path.exists(path):
                        filename = os.path.basename(path)
                        content_bytes = base64.b64encode(open(path, "rb").read()).decode("utf-8")
                        attachments_payload.append({
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename,
                            "contentType": "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg",
                            "contentBytes": content_bytes
                        })
                    
                email_payload = {
                    "message": {
                        "subject": subject,
                        "body": {
                            "contentType": "HTML" if html_body else "Text",
                            "content": html_body or body
                        },
                        "toRecipients": to_recipients,
                        "ccRecipients": cc_recipients,
                        "attachments": attachments_payload
                    }
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    }
                    send_url = "https://graph.microsoft.com/v1.0/me/sendMail"
                    response = await client.post(send_url, headers=headers, json=email_payload)
                    if response.status_code not in [200, 202]:
                        raise RuntimeError(f"Gửi sobo qua Microsoft Graph API thất bại: {response.text}")
                return SoboEmailResult(True)
                
        except Exception as exc:
            logger.error(f"OAuth2 sending failed for Sobo: {exc}, falling back to SMTP.")
            
    # --- PHẦN SMTP GỐC ---
    host = os.getenv("SMTP_HOST", os.getenv("MAIL_SERVER", os.getenv("EMAIL_HOST", "smtp.gmail.com"))).strip()
    port = int(os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", os.getenv("EMAIL_PORT", "587"))))
    password = os.getenv("SMTP_PASSWORD", os.getenv("MAIL_PASSWORD", os.getenv("EMAIL_PASSWORD", ""))).strip().replace(" ", "")

    if not user or not password:
        message = "Chua cau hinh MAIL_USERNAME/SMTP_USERNAME hoac MAIL_PASSWORD/SMTP_PASSWORD trong API.env."
        logger.error(message)
        return SoboEmailResult(False, message)

    msg = EmailMessage()
    msg["Subject"] = subject

    if mail_from_name and "@" not in mail_from_name:
        msg["From"] = formataddr((mail_from_name, user))
    else:
        msg["From"] = mail_from_name or user

    msg["To"] = to_email
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    msg.set_content(body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")
        _attach_sobo_logo(msg)

    for path in attachment_paths:
        if path and os.path.exists(path):
            filename = os.path.basename(path)
            try:
                with open(path, "rb") as f:
                    file_data = f.read()
                    maintype = "application"
                    if filename.lower().endswith(".pdf"):
                        subtype = "pdf"
                    elif filename.lower().endswith((".jpg", ".jpeg", ".png")):
                        maintype = "image"
                        subtype = filename.lower().split(".")[-1]
                        if subtype == "jpg":
                            subtype = "jpeg"
                    else:
                        subtype = "octet-stream"

                    msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)
            except Exception as e:
                logger.error(f"Loi khi doc file dinh kem {path}: {e}")

    try:
        logger.info(f"Dang gui email so bo toi {to_email}...")
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
        logger.info("Gui email thanh cong.")
        return SoboEmailResult(True)
    except smtplib.SMTPAuthenticationError as e:
        message = _smtp_auth_error_message()
        logger.error(f"Loi xac thuc SMTP khi gui email: {e}")
        return SoboEmailResult(False, message, str(e))
    except Exception as e:
        logger.error(f"Loi khi gui email: {e}")
        return SoboEmailResult(False, f"Viec gui email that bai: {e}", str(e))


async def send_sobo_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    attachment_path: str | list[str] = None,
    cc_emails: list[str] = None,
) -> bool:
    result = await send_sobo_email_with_result(
        to_email,
        subject,
        body,
        html_body=html_body,
        attachment_path=attachment_path,
        cc_emails=cc_emails,
    )
    return result.success


def format_recipient_info(text: str) -> str:
    if not text:
        return ""
    import re
    # Normalize spaces and newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    
    # Try to find keywords for "Địa chỉ" and "Điện thoại"
    addr_match = re.search(r"(?:Địa chỉ|Đ\/c|Đc)[:\s]*", text, re.IGNORECASE)
    phone_match = re.search(r"(?:Điện thoại|Đt|Sđt|Sđt:|Mobile|Hotline|Tel)[:\s]*", text, re.IGNORECASE)
    
    parts = []
    
    # If both matches exist
    if addr_match and phone_match:
        addr_start = addr_match.start()
        phone_start = phone_match.start()
        
        if addr_start < phone_start:
            name = text[:addr_start].strip(", \n\t")
            addr = text[addr_start:phone_start].strip(", \n\t")
            phone = text[phone_start:].strip(", \n\t")
        else:
            name = text[:phone_start].strip(", \n\t")
            phone = text[phone_start:addr_start].strip(", \n\t")
            addr = text[addr_start:].strip(", \n\t")
            
        if name:
            parts.append(name)
        if addr:
            # Ensure proper prefix
            if not addr.lower().startswith("địa chỉ"):
                addr = "Địa chỉ: " + addr
            parts.append(addr)
        if phone:
            # Ensure proper prefix
            if not any(phone.lower().startswith(x) for x in ["điện thoại", "đt", "sđt", "mobile", "hotline", "tel"]):
                phone = "Điện thoại: " + phone
            parts.append(phone)
            
    elif addr_match:
        addr_start = addr_match.start()
        name = text[:addr_start].strip(", \n\t")
        addr = text[addr_start:].strip(", \n\t")
        if name:
            parts.append(name)
        if addr:
            if not addr.lower().startswith("địa chỉ"):
                addr = "Địa chỉ: " + addr
            parts.append(addr)
            
    elif phone_match:
        phone_start = phone_match.start()
        name = text[:phone_start].strip(", \n\t")
        phone = text[phone_start:].strip(", \n\t")
        if name:
            parts.append(name)
        if phone:
            if not any(phone.lower().startswith(x) for x in ["điện thoại", "đt", "sđt", "mobile", "hotline", "tel"]):
                phone = "Điện thoại: " + phone
            parts.append(phone)
    else:
        # If no keywords but has comma-separated pieces:
        # e.g., "Company A, 90 Truong Chinh, 0905226968"
        subparts = [p.strip() for p in text.split(",") if p.strip()]
        if len(subparts) >= 3:
            last_part = subparts[-1]
            digits_only = "".join([c for c in last_part if c.isdigit()])
            if len(digits_only) >= 9:
                name = ", ".join(subparts[:-2])
                addr = "Địa chỉ: " + subparts[-2]
                phone = "Điện thoại: " + last_part
                return f"{name}\n{addr}\n{phone}"
        return text
        
    return "\n".join(parts)
