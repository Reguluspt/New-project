from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time

import streamlit as st
import streamlit.components.v1 as components


LOGIN_USERNAME_ENV = "APP_LOGIN_USERNAME"
LOGIN_PASSWORD_ENV = "APP_LOGIN_PASSWORD"
AUTH_COOKIE_NAME = "thamdinh_auth"
AUTH_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _configured_credentials() -> tuple[str, str]:
    return (
        os.getenv(LOGIN_USERNAME_ENV, "").strip(),
        os.getenv(LOGIN_PASSWORD_ENV, ""),
    )


def authenticate(username: str, password: str) -> bool:
    expected_username, expected_password = _configured_credentials()
    if not expected_username or not expected_password:
        return False
    return hmac.compare_digest(username.strip(), expected_username) and hmac.compare_digest(
        password,
        expected_password,
    )


def _create_auth_token(username: str, *, now: int | None = None) -> str:
    _, password = _configured_credentials()
    expires_at = (int(time.time()) if now is None else now) + AUTH_COOKIE_MAX_AGE_SECONDS
    payload = f"{username}|{expires_at}"
    encoded_payload = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(password.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def _validate_auth_token(token: str, *, now: int | None = None) -> str | None:
    expected_username, password = _configured_credentials()
    if not expected_username or not password:
        return None
    try:
        encoded_payload, signature = token.split(".", 1)
        expected_signature = hmac.new(
            password.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        padding = "=" * (-len(encoded_payload) % 4)
        payload = base64.urlsafe_b64decode(encoded_payload + padding).decode("utf-8")
        username, expires_at_value = payload.rsplit("|", 1)
        expires_at = int(expires_at_value)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    current_time = int(time.time()) if now is None else now
    if expires_at < current_time or not hmac.compare_digest(username, expected_username):
        return None
    return username


def _render_cookie_script(token: str | None) -> None:
    if token:
        cookie_value = f"{AUTH_COOKIE_NAME}={token}; Path=/; Max-Age={AUTH_COOKIE_MAX_AGE_SECONDS}; SameSite=Strict"
    else:
        cookie_value = f"{AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Strict"
    components.html(
        f"""
        <script>
        const cookie = {json.dumps(cookie_value)};
        document.cookie = cookie + (window.location.protocol === "https:" ? "; Secure" : "");
        </script>
        """,
        height=0,
        width=0,
    )


def logout() -> None:
    st.session_state.pop("app_authenticated", None)
    st.session_state.pop("app_login_username", None)
    st.session_state.pop("active_view", None)
    st.session_state["clear_auth_cookie"] = True


def render_login_gate() -> bool:
    if st.session_state.get("app_authenticated") is True:
        username = str(st.session_state.get("app_login_username") or "")
        _render_cookie_script(_create_auth_token(username))
        return True
    if st.session_state.pop("clear_auth_cookie", False):
        _render_cookie_script(None)
    else:
        cookie_username = _validate_auth_token(st.context.cookies.get(AUTH_COOKIE_NAME, ""))
        if cookie_username:
            st.session_state["app_authenticated"] = True
            st.session_state["app_login_username"] = cookie_username
            st.session_state.setdefault("active_view", "dashboard")
            _render_cookie_script(_create_auth_token(cookie_username))
            return True

    st.markdown(
        """
        <div class="login-brand">
            <div class="login-title">Hệ Thống Thẩm Định</div>
            <div class="login-subtitle">Đăng nhập để tiếp tục quản lý hồ sơ</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="login_panel"):
        st.subheader("Đăng nhập")
        with st.form("app_login_form", clear_on_submit=False):
            username = st.text_input("Tên tài khoản", autocomplete="username")
            password = st.text_input("Mật khẩu", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")

        if submitted:
            if authenticate(username, password):
                st.session_state["app_authenticated"] = True
                st.session_state["app_login_username"] = username.strip()
                st.session_state["active_view"] = "dashboard"
                st.rerun()
            st.error("Tên tài khoản hoặc mật khẩu không đúng.")

    return False
