from __future__ import annotations

import base64
import asyncio
import json
import logging
import smtplib
import time
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid, parseaddr
from pathlib import Path
from typing import Any, Mapping

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OAUTH_CONFIG_PATH = PROJECT_ROOT / "data" / "oauth_config.json"

logger = logging.getLogger(__name__)
OUTLOOK_GRAPH_SCOPES = "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access"
OUTLOOK_SMTP_SCOPES = "https://outlook.office.com/SMTP.Send offline_access"

# Default config structure
DEFAULT_OAUTH_CONFIG = {
    "google": {
        "client_id": "",
        "client_secret": "",
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0.0,
        "enabled": False,
    },
    "outlook": {
        "client_id": "",
        "client_secret": "",
        "tenant": "common",
        "sender_email": "",
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0.0,
        "enabled": False,
    },
    "outlook_smtp": {
        "client_id": "",
        "client_secret": "",
        "tenant": "common",
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0.0,
        "enabled": False,
    },
    "sobo_email": {
        "provider": "google",
        "mail_username": "hostktpro@gmail.com",
        "mail_from": "hostktpro@gmail.com",
    },
    "redirect_uri": "http://localhost:8501/"
}


def load_oauth_config() -> dict[str, Any]:
    """Tải cấu hình và tokens OAuth2 từ file JSON."""
    if not OAUTH_CONFIG_PATH.exists():
        OAUTH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_oauth_config(DEFAULT_OAUTH_CONFIG)
        return dict(DEFAULT_OAUTH_CONFIG)
    try:
        data = json.loads(OAUTH_CONFIG_PATH.read_text(encoding="utf-8"))
        # Ensure deep merge with default keys to avoid KeyError
        for provider in ["google", "outlook", "outlook_smtp"]:
            if provider not in data:
                data[provider] = dict(DEFAULT_OAUTH_CONFIG[provider])
            else:
                for k, v in DEFAULT_OAUTH_CONFIG[provider].items():
                    if k not in data[provider]:
                        data[provider][k] = v
        if "sobo_email" not in data or not isinstance(data.get("sobo_email"), dict):
            data["sobo_email"] = dict(DEFAULT_OAUTH_CONFIG["sobo_email"])
        else:
            for k, v in DEFAULT_OAUTH_CONFIG["sobo_email"].items():
                if k not in data["sobo_email"]:
                    data["sobo_email"][k] = v
        # Ensure redirect_uri key is loaded
        if "redirect_uri" not in data:
            data["redirect_uri"] = DEFAULT_OAUTH_CONFIG["redirect_uri"]
        return data
    except Exception as exc:
        logger.error(f"Lỗi khi đọc file cấu hình OAuth2: {exc}")
        return dict(DEFAULT_OAUTH_CONFIG)


def save_oauth_config(config: dict[str, Any]) -> None:
    """Ghi đè cấu hình và tokens OAuth2 vào file JSON."""
    try:
        OAUTH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        OAUTH_CONFIG_PATH.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        logger.error(f"Lỗi khi lưu file cấu hình OAuth2: {exc}")


def is_oauth_enabled(provider: str) -> bool:
    """Kiểm tra xem nhà cung cấp OAuth2 cụ thể có đang bật và được cấu hình Client ID hay không."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    return bool(p_config.get("enabled", False) and p_config.get("client_id") and p_config.get("refresh_token"))


def get_enabled_oauth_provider() -> str | None:
    """Return the active mailbox provider, preferring Outlook during migration from Gmail."""
    if is_oauth_enabled("outlook"):
        return "outlook"
    if is_oauth_enabled("google"):
        return "google"
    return None


def get_outlook_sender_email() -> str:
    """Return the Outlook alias to expose as the sender when one is configured."""
    config = load_oauth_config()
    return str(config.get("outlook", {}).get("sender_email") or "").strip()


def get_sobo_email_config() -> dict[str, str]:
    """Return UI-managed Sơ bộ email settings."""
    config = load_oauth_config()
    sobo_config = config.get("sobo_email", {})
    if not isinstance(sobo_config, dict):
        sobo_config = {}
    provider = str(sobo_config.get("provider") or "google").strip().lower()
    if provider not in {"google", "outlook"}:
        provider = "google"
    return {
        "provider": provider,
        "mail_username": str(sobo_config.get("mail_username") or "hostktpro@gmail.com").strip(),
        "mail_from": str(sobo_config.get("mail_from") or "hostktpro@gmail.com").strip(),
    }


def is_outlook_smtp_enabled() -> bool:
    """Return whether SMTP OAuth sending is ready for an Outlook alias."""
    return bool(get_outlook_sender_email() and is_oauth_enabled("outlook_smtp"))


def _graph_error_detail(response: httpx.Response) -> str:
    request_id = response.headers.get("request-id") or response.headers.get("client-request-id") or ""
    try:
        body = response.json()
        error = body.get("error", {}) if isinstance(body, dict) else {}
        error_code = str(error.get("code") or "").strip()
        error_message = str(error.get("message") or "").strip()
        detail = " - ".join(part for part in (error_code, error_message) if part)
    except (ValueError, TypeError):
        detail = response.text.strip()
    parts = [f"HTTP {response.status_code}"]
    if detail:
        parts.append(detail)
    if request_id:
        parts.append(f"request-id={request_id}")
    return "; ".join(parts)


def _access_token_claim_summary(access_token: str) -> str:
    """Expose only Graph routing claims needed to diagnose a rejected token."""
    try:
        segments = str(access_token or "").split(".")
        if len(segments) < 2:
            return "token-claims=unavailable"
        encoded_payload = segments[1] + "=" * (-len(segments[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload).decode("utf-8"))
        if not isinstance(payload, dict):
            return "token-claims=unavailable"
        audience = str(payload.get("aud") or "<missing>")
        scopes = str(payload.get("scp") or "<missing>")
        tenant = str(payload.get("tid") or "<missing>")
        return f"aud={audience}; scp={scopes}; tid={tenant}"
    except Exception:
        # Diagnostics must never hide the original Graph response.
        return "token-claims=unavailable"


def get_auth_url(provider: str, redirect_uri: str, state: str | None = None) -> str:
    """Tạo đường dẫn Authorization URL cho Google hoặc Outlook."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    client_id = p_config.get("client_id", "").strip()
    if not client_id:
        raise ValueError(f"Thiếu Client ID cho {provider.upper()}. Vui lòng cấu hình trước.")

    state_str = f"&state={state}" if state else ""

    if provider == "google":
        scope = "https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send"
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            f"&scope={scope}"
            "&access_type=offline"
            "&prompt=consent"
            f"{state_str}"
        )
    elif provider in {"outlook", "outlook_smtp"}:
        tenant = p_config.get("tenant", "common").strip() or "common"
        scopes = OUTLOOK_SMTP_SCOPES if provider == "outlook_smtp" else OUTLOOK_GRAPH_SCOPES
        return (
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            f"&scope={scopes}"
            "&response_mode=query"
            f"{state_str}"
        )
    else:
        raise ValueError("Provider không hợp lệ.")


def exchange_code_for_tokens(provider: str, code: str, redirect_uri: str) -> dict[str, Any]:
    """Trao đổi Authorization Code lấy Access Token và Refresh Token."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    client_id = p_config.get("client_id", "").strip()
    client_secret = p_config.get("client_secret", "").strip()

    if not client_id or not client_secret:
        raise ValueError(f"Thiếu Client ID hoặc Client Secret cho {provider.upper()}.")

    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    elif provider in {"outlook", "outlook_smtp"}:
        tenant = p_config.get("tenant", "common").strip() or "common"
        scopes = OUTLOOK_SMTP_SCOPES if provider == "outlook_smtp" else OUTLOOK_GRAPH_SCOPES
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": scopes,
        }
    else:
        raise ValueError("Provider không hợp lệ.")

    with httpx.Client(timeout=15.0) as client:
        response = client.post(token_url, data=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Lỗi trao đổi token: {response.text}")

        res_data = response.json()
        access_token = res_data.get("access_token")
        refresh_token = res_data.get("refresh_token") or p_config.get("refresh_token")
        expires_in = res_data.get("expires_in", 3600)

        p_config["access_token"] = access_token
        if refresh_token:
            p_config["refresh_token"] = refresh_token
        p_config["expires_at"] = time.time() + expires_in
        p_config["enabled"] = True

        config[provider] = p_config
        save_oauth_config(config)
        return p_config


def refresh_access_token(provider: str) -> str:
    """Làm mới Access Token bằng Refresh Token (Sync)."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    client_id = p_config.get("client_id", "").strip()
    client_secret = p_config.get("client_secret", "").strip()
    refresh_token = p_config.get("refresh_token", "").strip()

    if not client_id or not client_secret or not refresh_token:
        raise ValueError(f"Thiếu thông tin kết nối OAuth2 cho {provider.upper()}.")

    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    elif provider in {"outlook", "outlook_smtp"}:
        tenant = p_config.get("tenant", "common").strip() or "common"
        scopes = OUTLOOK_SMTP_SCOPES if provider == "outlook_smtp" else OUTLOOK_GRAPH_SCOPES
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": scopes,
        }
    else:
        raise ValueError("Provider không hợp lệ.")

    with httpx.Client(timeout=15.0) as client:
        response = client.post(token_url, data=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Lỗi refresh token: {response.text}")

        res_data = response.json()
        access_token = res_data.get("access_token")
        new_refresh_token = res_data.get("refresh_token")
        expires_in = res_data.get("expires_in", 3600)

        p_config["access_token"] = access_token
        if new_refresh_token:
            p_config["refresh_token"] = new_refresh_token
        p_config["expires_at"] = time.time() + expires_in

        config[provider] = p_config
        save_oauth_config(config)
        return access_token


async def refresh_access_token_async(provider: str) -> str:
    """Làm mới Access Token bằng Refresh Token (Async)."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    client_id = p_config.get("client_id", "").strip()
    client_secret = p_config.get("client_secret", "").strip()
    refresh_token = p_config.get("refresh_token", "").strip()

    if not client_id or not client_secret or not refresh_token:
        raise ValueError(f"Thiếu thông tin kết nối OAuth2 cho {provider.upper()}.")

    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    elif provider in {"outlook", "outlook_smtp"}:
        tenant = p_config.get("tenant", "common").strip() or "common"
        scopes = OUTLOOK_SMTP_SCOPES if provider == "outlook_smtp" else OUTLOOK_GRAPH_SCOPES
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": scopes,
        }
    else:
        raise ValueError("Provider không hợp lệ.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(token_url, data=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Lỗi refresh token: {response.text}")

        res_data = response.json()
        access_token = res_data.get("access_token")
        new_refresh_token = res_data.get("refresh_token")
        expires_in = res_data.get("expires_in", 3600)

        p_config["access_token"] = access_token
        if new_refresh_token:
            p_config["refresh_token"] = new_refresh_token
        p_config["expires_at"] = time.time() + expires_in

        config[provider] = p_config
        save_oauth_config(config)
        return access_token


def get_valid_access_token(provider: str) -> str:
    """Lấy Access Token hợp lệ, tự động làm mới nếu sắp hết hạn (Sync)."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    access_token = p_config.get("access_token", "")
    expires_at = p_config.get("expires_at", 0.0)

    # Nếu sắp hết hạn (còn dưới 5 phút)
    if not access_token or time.time() > (expires_at - 300):
        return refresh_access_token(provider)
    return access_token


async def get_valid_access_token_async(provider: str) -> str:
    """Lấy Access Token hợp lệ, tự động làm mới nếu sắp hết hạn (Async)."""
    config = load_oauth_config()
    p_config = config.get(provider, {})
    access_token = p_config.get("access_token", "")
    expires_at = p_config.get("expires_at", 0.0)

    # Nếu sắp hết hạn (còn dưới 5 phút)
    if not access_token or time.time() > (expires_at - 300):
        return await refresh_access_token_async(provider)
    return access_token


def _build_mime_message(
    from_email: str,
    to_email: str,
    subject: str,
    html_body: str,
    cc_emails: list[str] | None = None,
    reply_to_msg_id: str | None = None,
    references: str | None = None,
    thread_topic: str | None = None,
    thread_index: str | None = None,
) -> EmailMessage:
    """Xây dựng đối tượng EmailMessage chuẩn RFC822."""
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    domain = (parseaddr(from_email)[1].split("@", 1)[1] if "@" in parseaddr(from_email)[1] else "outlook.com")
    msg["Message-ID"] = make_msgid(domain=domain)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    if reply_to_msg_id:
        msg["In-Reply-To"] = reply_to_msg_id
        if references:
            msg["References"] = f"{references} {reply_to_msg_id}".strip()
        else:
            msg["References"] = reply_to_msg_id
    if thread_topic:
        msg["Thread-Topic"] = thread_topic
    if thread_index:
        msg["Thread-Index"] = thread_index

    msg.set_content("Vui lòng sử dụng trình đọc HTML để xem email này.")
    msg.add_alternative(html_body, subtype="html")
    
    # Inline image embedding (CID) for the logo
    logo_path = Path(__file__).resolve().parent / "templates" / "logo.jpg"
    if logo_path.exists():
        import mimetypes
        ctype, _encoding = mimetypes.guess_type(str(logo_path))
        if ctype is None:
            ctype = 'image/jpeg'
        maintype, subtype = ctype.split('/', 1)
        try:
            with open(logo_path, 'rb') as f:
                img_data = f.read()
            html_part = msg.get_payload()[-1]
            html_part.add_related(img_data, maintype=maintype, subtype=subtype, cid='<logo_cenvalue>', filename='logo.jpg')
        except Exception as img_err:
            logger.error(f"Error embedding logo in OAuth MIME msg: {img_err}")
            
    return msg


def _send_outlook_smtp_sync(message: EmailMessage, sender_email: str, access_token: str) -> None:
    """Submit a MIME message through Outlook.com SMTP using OAuth2."""
    recipients = [
        address
        for _name, address in getaddresses([str(message.get("To") or ""), str(message.get("Cc") or "")])
        if address
    ]
    auth = base64.b64encode(
        f"user={sender_email}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
    ).decode("ascii")
    with smtplib.SMTP("smtp-mail.outlook.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        code, response = smtp.docmd("AUTH", f"XOAUTH2 {auth}")
        if code != 235:
            detail = response.decode("utf-8", errors="replace") if isinstance(response, bytes) else str(response)
            raise RuntimeError(f"Xac thuc Outlook SMTP OAuth2 that bai: SMTP {code}; {detail}")
        smtp.send_message(message, from_addr=sender_email, to_addrs=recipients)


async def send_outlook_message_via_smtp_oauth2(message: EmailMessage) -> str:
    """Send using Outlook SMTP OAuth when a personal Outlook alias is required."""
    sender_email = get_outlook_sender_email()
    if not sender_email:
        raise ValueError("Chua cau hinh dia chi gui Outlook (alias).")
    access_token = await get_valid_access_token_async("outlook_smtp")
    await asyncio.to_thread(_send_outlook_smtp_sync, message, sender_email, access_token)
    return str(message.get("Message-ID") or "outlook-smtp-sent")


async def send_email_via_oauth2(
    provider: str,
    from_email: str,
    to_email: str,
    subject: str,
    html_body: str,
    cc_emails: list[str] | None = None,
    reply_to_msg_id: str | None = None,
    references: str | None = None,
    thread_id: str | None = None,
    thread_topic: str | None = None,
    thread_index: str | None = None,
    mime_message: EmailMessage | None = None,
) -> str:
    """Gửi email thông qua API REST của Google Workspace hoặc Outlook sử dụng OAuth2."""
    if provider == "outlook" and is_outlook_smtp_enabled():
        message = mime_message or _build_mime_message(
            get_outlook_sender_email(),
            to_email,
            subject,
            html_body,
            cc_emails,
            reply_to_msg_id,
            references,
            thread_topic,
            thread_index,
        )
        sender_email = get_outlook_sender_email()
        if sender_email:
            if message.get("From"):
                message.replace_header("From", sender_email)
            else:
                message["From"] = sender_email
        return await send_outlook_message_via_smtp_oauth2(message)

    access_token = await get_valid_access_token_async(provider)

    if provider == "google":
        msg = mime_message or _build_mime_message(
            from_email,
            to_email,
            subject,
            html_body,
            cc_emails,
            reply_to_msg_id,
            references,
            thread_topic,
            thread_index,
        )
        raw_bytes = msg.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            payload: dict[str, Any] = {"raw": raw_b64}
            if thread_id:
                payload["threadId"] = thread_id
            response = await client.post(send_url, headers=headers, json=payload)
            if response.status_code not in [200, 201]:
                raise RuntimeError(f"Gửi mail qua Gmail API thất bại: {response.text}")
            res_data = response.json()
            return res_data.get("id", "")

    elif provider == "outlook":
        outlook_sender_email = get_outlook_sender_email()
        if mime_message is not None:
            if outlook_sender_email:
                if mime_message.get("From"):
                    mime_message.replace_header("From", outlook_sender_email)
                else:
                    mime_message["From"] = outlook_sender_email
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "text/plain",
                }
                response = await client.post(
                    "https://graph.microsoft.com/v1.0/me/sendMail",
                    headers=headers,
                    content=base64.b64encode(mime_message.as_bytes()).decode("ascii"),
                )
                if response.status_code not in [200, 202]:
                    detail = _graph_error_detail(response)
                    if response.status_code == 401:
                        detail = f"{detail}; {_access_token_claim_summary(access_token)}"
                    raise RuntimeError(f"Gửi mail qua Microsoft Graph API thất bại: {detail}")
                return response.headers.get("client-request-id", "outlook-msg-sent")

        # Build recipient JSON payload
        to_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in to_email.split(",") if addr.strip()]
        cc_recipients = []
        if cc_emails:
            cc_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in cc_emails if addr.strip()]

        attachments_payload = []
        logo_path = Path(__file__).resolve().parent / "templates" / "logo.jpg"
        if logo_path.exists():
            attachments_payload.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "logo.jpg",
                "contentType": "image/jpeg",
                "contentBytes": base64.b64encode(logo_path.read_bytes()).decode("utf-8"),
                "isInline": True,
                "contentId": "logo_cenvalue",
            })

        email_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": to_recipients,
                "ccRecipients": cc_recipients,
                "attachments": attachments_payload,
            }
        }
        # Threading for Outlook Graph API
        if reply_to_msg_id:
            email_payload["message"]["internetMessageHeaders"] = [
                {"name": "In-Reply-To", "value": reply_to_msg_id}
            ]
            if references:
                email_payload["message"]["internetMessageHeaders"].append(
                    {"name": "References", "value": f"{references} {reply_to_msg_id}".strip()}
                )
            if thread_topic:
                email_payload["message"]["internetMessageHeaders"].append(
                    {"name": "Thread-Topic", "value": thread_topic}
                )
            if thread_index:
                email_payload["message"]["internetMessageHeaders"].append(
                    {"name": "Thread-Index", "value": thread_index}
                )

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            send_url = "https://graph.microsoft.com/v1.0/me/sendMail"
            response = await client.post(send_url, headers=headers, json=email_payload)
            if response.status_code not in [200, 202]:
                detail = _graph_error_detail(response)
                if response.status_code == 401:
                    detail = f"{detail}; {_access_token_claim_summary(access_token)}"
                raise RuntimeError(f"Gửi mail qua Microsoft Graph API thất bại: {detail}")
            
            # Outlook 202 Accepted returns empty body, generate a random message id
            return response.headers.get("client-request-id", "outlook-msg-sent")

    else:
        raise ValueError("Provider không hợp lệ.")


async def fetch_emails_via_oauth2(
    provider: str,
    query_contract: str | None = None,
    limit: int = 15,
    unread_only: bool = True,
) -> list[dict[str, Any]]:
    """Tải và parse danh sách email thông qua REST API Google/Microsoft."""
    access_token = await get_valid_access_token_async(provider)
    emails_list = []

    if provider == "google":
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            # Search messages
            search_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params: dict[str, Any] = {"maxResults": limit}
            q_parts: list[str] = []
            if unread_only:
                q_parts.extend(["is:unread", "label:INBOX"])
            if query_contract:
                q_parts.append(f'subject:"{query_contract}"')
            params["q"] = " ".join(q_parts)
            
            response = await client.get(search_url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Gmail API Search thất bại: {response.text}")
                return []
            
            messages = response.json().get("messages", [])
            for msg_summary in messages:
                msg_id = msg_summary["id"]
                # Fetch raw MIME message
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                detail_response = await client.get(detail_url, headers=headers, params={"format": "raw"})
                if detail_response.status_code == 200:
                    raw_b64 = detail_response.json().get("raw", "")
                    raw_bytes = base64.urlsafe_b64decode(raw_b64)
                    emails_list.append({
                        "uid": msg_id,
                        "thread_id": str(msg_summary.get("threadId") or ""),
                        "raw_bytes": raw_bytes
                    })

    elif provider == "outlook":
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            search_url = "https://graph.microsoft.com/v1.0/me/messages"
            fetch_limit = max(limit, 50) if query_contract else limit
            params = {
                "$top": fetch_limit,
                "$select": "id,subject",
                "$orderby": "receivedDateTime desc"
            }
            filter_parts: list[str] = []
            if unread_only:
                filter_parts.append("isRead eq false")
            if filter_parts:
                params["$filter"] = " and ".join(filter_parts)

            response = await client.get(search_url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Microsoft Graph API Search thất bại: {response.text}")
                if query_contract:
                    raise RuntimeError(f"Microsoft Graph API Search thất bại: {_graph_error_detail(response)}")
                return []

            messages = response.json().get("value", [])
            for msg in messages:
                if query_contract and query_contract.lower() not in str(msg.get("subject") or "").lower():
                    continue
                msg_id = msg["id"]
                # Fetch raw MIME
                mime_url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}/$value"
                mime_response = await client.get(mime_url, headers=headers)
                if mime_response.status_code == 200:
                    emails_list.append({
                        "uid": msg_id,
                        "thread_id": msg_id,
                        "raw_bytes": mime_response.content
                    })
                    if query_contract and len(emails_list) >= limit:
                        break

    return emails_list
