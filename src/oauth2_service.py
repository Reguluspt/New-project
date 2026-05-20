from __future__ import annotations

import base64
import json
import logging
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Mapping

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OAUTH_CONFIG_PATH = PROJECT_ROOT / "data" / "oauth_config.json"

logger = logging.getLogger(__name__)

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
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0.0,
        "enabled": False,
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
        for provider in ["google", "outlook"]:
            if provider not in data:
                data[provider] = dict(DEFAULT_OAUTH_CONFIG[provider])
            else:
                for k, v in DEFAULT_OAUTH_CONFIG[provider].items():
                    if k not in data[provider]:
                        data[provider][k] = v
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
    elif provider == "outlook":
        tenant = p_config.get("tenant", "common").strip() or "common"
        scope = "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access"
        return (
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            f"&scope={scope}"
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
    elif provider == "outlook":
        tenant = p_config.get("tenant", "common").strip() or "common"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
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
    elif provider == "outlook":
        tenant = p_config.get("tenant", "common").strip() or "common"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access",
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
    elif provider == "outlook":
        tenant = p_config.get("tenant", "common").strip() or "common"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access",
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
    references: str | None = None
) -> EmailMessage:
    """Xây dựng đối tượng EmailMessage chuẩn RFC822."""
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    if reply_to_msg_id:
        msg["In-Reply-To"] = reply_to_msg_id
        if references:
            msg["References"] = f"{references} {reply_to_msg_id}".strip()
        else:
            msg["References"] = reply_to_msg_id

    msg.set_content("Vui lòng sử dụng trình đọc HTML để xem email này.")
    msg.add_alternative(html_body, subtype="html")
    
    # Inline image embedding (CID) for the logo
    logo_path = Path("src/templates/logo.jpg")
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
            html_part.add_related(img_data, maintype=maintype, subtype=subtype, cid='logo_cenvalue')
        except Exception as img_err:
            logger.error(f"Error embedding logo in OAuth MIME msg: {img_err}")
            
    return msg


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
) -> str:
    """Gửi email thông qua API REST của Google Workspace hoặc Outlook sử dụng OAuth2."""
    access_token = await get_valid_access_token_async(provider)

    if provider == "google":
        msg = _build_mime_message(from_email, to_email, subject, html_body, cc_emails, reply_to_msg_id, references)
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
        # Build recipient JSON payload
        to_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in to_email.split(",") if addr.strip()]
        cc_recipients = []
        if cc_emails:
            cc_recipients = [{"emailAddress": {"address": addr.strip()}} for addr in cc_emails if addr.strip()]

        email_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": to_recipients,
                "ccRecipients": cc_recipients,
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            send_url = "https://graph.microsoft.com/v1.0/me/sendMail"
            response = await client.post(send_url, headers=headers, json=email_payload)
            if response.status_code not in [200, 202]:
                raise RuntimeError(f"Gửi mail qua Microsoft Graph API thất bại: {response.text}")
            
            # Outlook 202 Accepted returns empty body, generate a random message id
            return response.headers.get("client-request-id", "outlook-msg-sent")

    else:
        raise ValueError("Provider không hợp lệ.")


async def fetch_emails_via_oauth2(
    provider: str,
    query_contract: str | None = None,
    limit: int = 15
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
            q_parts = ["is:unread", "label:INBOX"]
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
            params = {
                "$top": limit,
                "$select": "id,subject",
                "$orderby": "receivedDateTime desc"
            }
            filter_parts = ["isRead eq false"]
            if query_contract:
                filter_parts.append(f"contains(subject, '{query_contract}')")
            params["$filter"] = " and ".join(filter_parts)

            response = await client.get(search_url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(f"Microsoft Graph API Search thất bại: {response.text}")
                return []

            messages = response.json().get("value", [])
            for msg in messages:
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

    return emails_list
