from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st


def render_app_theme() -> None:
    """Apply the Stitch/Figma enterprise visual system to Streamlit widgets."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
        <style>
            :root {
                --app-bg: #faf9ff;
                --app-surface: #ffffff;
                --app-surface-low: #f1f3ff;
                --app-surface-container: #e9edff;
                --app-surface-high: #d8e2ff;
                --app-primary: #0052cc;
                --app-primary-strong: #003d9b;
                --app-primary-soft: #dae2ff;
                --app-text: #051a3e;
                --app-muted: #434654;
                --app-outline: #c3c6d6;
                --app-outline-soft: #e2e8f0;
                --app-error: #ba1a1a;
                --app-error-soft: #ffdad6;
                --app-shadow: 0 8px 24px -8px rgba(9, 30, 66, 0.16);
                --app-shadow-soft: 0 4px 18px -8px rgba(9, 30, 66, 0.18);
                --app-radius: 12px;
            }

            html, body, [class*="css"] {
                font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
                letter-spacing: 0 !important;
            }

            .material-symbols-outlined {
                font-family: "Material Symbols Outlined";
                font-weight: normal;
                font-style: normal;
                font-size: 20px;
                line-height: 1;
                letter-spacing: normal;
                text-transform: none;
                display: inline-flex;
                white-space: nowrap;
                direction: ltr;
                -webkit-font-feature-settings: "liga";
                -webkit-font-smoothing: antialiased;
                font-variation-settings: "FILL" 0, "wght" 500, "GRAD" 0, "opsz" 24;
            }

            .stApp {
                background: var(--app-bg);
                color: var(--app-text);
            }

            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stStatusWidget"],
            #MainMenu {
                display: none !important;
            }

            section[data-testid="stSidebar"] {
                background: var(--app-surface);
                border-right: 1px solid var(--app-outline-soft);
                box-shadow: var(--app-shadow-soft);
            }

            section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
            section[data-testid="stSidebar"] label {
                color: var(--app-muted);
                font-size: 13px;
            }

            .block-container {
                padding-top: 5.6rem !important;
                padding-left: 1.9rem !important;
                padding-right: 1.9rem !important;
                padding-bottom: 2rem !important;
                max-width: 100% !important;
            }

            h1, h2, h3, h4 {
                color: var(--app-text) !important;
                letter-spacing: 0 !important;
            }

            h2 {
                font-size: 30px !important;
                line-height: 38px !important;
                font-weight: 700 !important;
                margin-top: 0.5rem !important;
            }

            h3 {
                font-size: 22px !important;
                line-height: 30px !important;
                font-weight: 650 !important;
            }

            div[data-testid="stTabs"] > div[role="tablist"] {
                position: sticky;
                top: 64px;
                z-index: 45;
                background: var(--app-surface);
                border-bottom: 1px solid var(--app-outline);
                border-radius: 0;
                box-shadow: 0 2px 8px -8px rgba(9, 30, 66, 0.24);
                padding: 0 0 0 1.9rem;
                gap: 8px;
                margin: -1.2rem -1.9rem 24px;
            }

            button[data-baseweb="tab"] {
                border-radius: 8px 8px 0 0 !important;
                padding: 12px 18px !important;
                color: #50627e !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                height: 52px !important;
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                background: var(--app-surface-high) !important;
                color: var(--app-primary) !important;
                border-bottom: 4px solid var(--app-primary) !important;
            }

            div[data-testid="stMetric"] {
                background: var(--app-surface);
                border: 1px solid rgba(195, 198, 214, 0.45);
                border-radius: var(--app-radius);
                box-shadow: var(--app-shadow);
                padding: 22px 24px;
                min-height: 128px;
            }

            div[data-testid="stMetric"] label {
                color: var(--app-muted) !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 0.04em !important;
            }

            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: var(--app-text) !important;
                font-size: 34px !important;
                line-height: 42px !important;
                font-weight: 750 !important;
            }

            div[data-testid="stMetric"]:has([data-testid="stMetricValue"]) {
                overflow: hidden;
            }

            div[data-testid="stExpander"],
            div[data-testid="stForm"],
            div[data-testid="stDataFrame"],
            div[data-testid="stVegaLiteChart"] {
                border-radius: var(--app-radius) !important;
            }

            div[data-testid="stExpander"] details,
            div[data-testid="stForm"] {
                background: var(--app-surface) !important;
                border: 1px solid var(--app-outline-soft) !important;
                box-shadow: var(--app-shadow-soft);
            }

            div[data-testid="stVegaLiteChart"],
            div[data-testid="stDataFrame"] {
                background: var(--app-surface);
                border: 1px solid var(--app-outline-soft);
                box-shadow: var(--app-shadow-soft);
                padding: 8px;
            }

            div[data-testid="stDataFrame"] thead tr th {
                background: var(--app-surface-low) !important;
                color: #5d6b82 !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 0.04em !important;
            }

            div[data-baseweb="select"] > div,
            div[data-testid="stTextInput"] input,
            div[data-testid="stNumberInput"] input,
            textarea {
                border-radius: 8px !important;
                border-color: var(--app-outline) !important;
                background: var(--app-surface) !important;
                color: var(--app-text) !important;
                min-height: 42px;
            }

            div[data-baseweb="select"] > div:focus-within,
            div[data-testid="stTextInput"] input:focus,
            div[data-testid="stNumberInput"] input:focus,
            textarea:focus {
                border-color: var(--app-primary) !important;
                box-shadow: 0 0 0 3px rgba(0, 82, 204, 0.16) !important;
            }

            [data-testid="InputInstructions"] {
                display: none !important;
            }

            input[type="password"]::-ms-reveal,
            input[type="password"]::-ms-clear {
                display: none;
            }

            label, div[data-testid="stWidgetLabel"] p {
                color: var(--app-text) !important;
                font-size: 13px !important;
                font-weight: 600 !important;
            }

            .stButton > button,
            .stDownloadButton > button,
            button[kind="primary"],
            button[data-testid="stBaseButton-primaryFormSubmit"] {
                border-radius: 8px !important;
                border: 1px solid var(--app-primary) !important;
                background: var(--app-primary) !important;
                color: #ffffff !important;
                font-weight: 650 !important;
                min-height: 40px;
                box-shadow: 0 6px 16px -10px rgba(0, 82, 204, 0.55);
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover,
            button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
                background: var(--app-primary-strong) !important;
                border-color: var(--app-primary-strong) !important;
                color: #ffffff !important;
            }

            .stButton > button:disabled,
            .stDownloadButton > button:disabled {
                background: #edf1fb !important;
                border-color: #d5dcec !important;
                color: #7a8498 !important;
                box-shadow: none !important;
            }

            div[data-testid="stAlert"] {
                border-radius: var(--app-radius) !important;
                border: 1px solid var(--app-outline-soft) !important;
            }

            .st-key-app_header {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                z-index: 60;
                background: var(--app-surface);
                border-bottom: 1px solid var(--app-outline-soft);
                box-shadow: 0 1px 6px -5px rgba(9, 30, 66, 0.2);
                min-height: 64px;
                padding: 0 24px;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
                flex-wrap: nowrap !important;
                overflow-x: auto;
                overflow-y: hidden;
                height: 64px;
                box-sizing: border-box;
            }

            .st-key-app_header [data-testid="stVerticalBlock"] {
                gap: 0;
            }

            .st-key-app_header > * {
                flex: 0 0 auto;
            }

            .app-brand {
                display: flex;
                align-items: center;
                gap: 18px;
                min-width: 0;
            }

            .app-brand-main {
                font-size: 18px;
                line-height: 22px;
                font-weight: 750;
                color: var(--app-primary);
                white-space: nowrap;
            }

            .app-brand-sub {
                font-size: 11px;
                line-height: 16px;
                font-weight: 600;
                color: #5d6b82;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .app-divider {
                width: 1px;
                height: 34px;
                background: var(--app-outline-soft);
            }

            .app-title {
                font-size: 20px;
                line-height: 28px;
                font-weight: 750;
                color: var(--app-text);
                white-space: nowrap;
            }

            .app-nav {
                display: flex;
                align-items: center;
                gap: 4px;
                overflow-x: auto;
                white-space: nowrap;
            }

            .app-nav-item {
                display: inline-flex;
                align-items: center;
                gap: 7px;
                padding: 7px 10px;
                border-radius: 8px;
                color: #5d6b82;
                font-size: 13px;
                font-weight: 650;
                text-decoration: none;
            }

            .app-nav-item.active {
                background: rgba(0, 82, 204, 0.1);
                color: var(--app-primary);
            }

            .app-nav-item.active .material-symbols-outlined {
                font-variation-settings: "FILL" 1, "wght" 500, "GRAD" 0, "opsz" 24;
            }

            .st-key-app_header .stButton > button {
                min-height: 42px !important;
                border: 0 !important;
                box-shadow: none !important;
                padding: 0 10px !important;
                white-space: nowrap;
            }

            .st-key-app_header .stButton > button[kind="secondary"] {
                background: transparent !important;
                color: #5d6b82 !important;
            }

            .st-key-app_header .stButton > button[kind="primary"] {
                background: rgba(0, 82, 204, 0.1) !important;
                color: var(--app-primary) !important;
            }

            .st-key-app_header .stButton > button:hover {
                background: var(--app-primary-soft) !important;
                color: var(--app-primary) !important;
            }

            .app-top-actions {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-left: auto;
                min-width: 0;
            }

            .app-search {
                min-width: 280px;
                height: 44px;
                border: 1px solid var(--app-outline);
                border-radius: 999px;
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 0 16px;
                color: #66758c;
                background: #fbfcff;
            }

            .app-icon {
                width: 40px;
                height: 40px;
                border-radius: 999px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: #364964;
                background: transparent;
            }

            .app-avatar {
                width: 36px;
                height: 36px;
                border-radius: 999px;
                background: var(--app-primary-soft);
                color: var(--app-primary-strong);
                font-weight: 750;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }

            .app-account {
                color: var(--app-primary);
                font-weight: 700;
                white-space: nowrap;
            }

            .login-brand {
                width: min(440px, calc(100vw - 32px));
                margin: clamp(3rem, 12vh, 8rem) auto 18px;
                text-align: center;
            }

            .login-title {
                color: var(--app-primary);
                font-size: 28px;
                line-height: 36px;
                font-weight: 750;
            }

            .login-subtitle {
                color: var(--app-muted);
                font-size: 14px;
                line-height: 22px;
                margin-top: 6px;
            }

            .st-key-login_panel {
                width: min(420px, calc(100vw - 32px));
                margin: 0 auto;
                padding: 26px 26px 18px;
                background: var(--app-surface);
                border: 1px solid var(--app-outline-soft);
                border-radius: 8px;
                box-shadow: var(--app-shadow);
            }

            .dashboard-kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 16px;
                margin: 18px 0 24px;
            }

            .dashboard-kpi-card {
                position: relative;
                min-height: 150px;
                padding: 24px;
                border-radius: 12px;
                background: #ffffff;
                box-shadow: var(--app-shadow);
                border: 1px solid rgba(226, 232, 240, 0.72);
                overflow: hidden;
            }

            .dashboard-kpi-card.primary {
                background: var(--app-primary);
                color: #ffffff;
                border-color: var(--app-primary);
            }

            .dashboard-kpi-label {
                color: var(--app-muted);
                font-size: 12px;
                line-height: 16px;
                font-weight: 750;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }

            .dashboard-kpi-card.primary .dashboard-kpi-label {
                color: rgba(255, 255, 255, 0.78);
            }

            .dashboard-kpi-value {
                color: var(--app-text);
                font-size: 36px;
                line-height: 44px;
                font-weight: 780;
                margin-top: 12px;
            }

            .dashboard-kpi-card.primary .dashboard-kpi-value {
                color: #ffffff;
            }

            .dashboard-kpi-unit {
                color: var(--app-muted);
                font-size: 18px;
                font-weight: 500;
                margin-left: 4px;
            }

            .dashboard-kpi-card.primary .dashboard-kpi-unit {
                color: rgba(255, 255, 255, 0.78);
            }

            .dashboard-kpi-note {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-top: 18px;
                color: var(--app-muted);
                font-size: 14px;
                line-height: 20px;
            }

            .dashboard-kpi-card.primary .dashboard-kpi-note {
                justify-content: space-between;
                color: rgba(255, 255, 255, 0.78);
            }

            .dashboard-kpi-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 8px;
                background: #ffffff;
                color: var(--app-primary);
                padding: 3px 9px;
                font-size: 12px;
                font-weight: 650;
            }

            .dashboard-kpi-watermark {
                position: absolute;
                right: -16px;
                top: -20px;
                color: rgba(255, 255, 255, 0.11);
                font-size: 118px;
            }

            .dashboard-progress {
                height: 8px;
                border-radius: 999px;
                background: var(--app-surface-container);
                margin: 20px 0 10px;
                overflow: hidden;
            }

            .dashboard-progress-fill {
                height: 100%;
                border-radius: 999px;
                background: var(--app-primary);
            }

            @media (max-width: 1200px) {
                .dashboard-kpi-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .app-nav .app-nav-item span:last-child {
                    display: none;
                }
            }

            @media (max-width: 900px) {
                .st-key-app_header {
                    align-items: center;
                    padding: 0 12px;
                }
                .app-title, .app-search, .app-divider, .app-brand-sub, .app-account {
                    display: none;
                }
                .app-top-actions {
                    width: auto;
                    justify-content: flex-end;
                }
                .block-container {
                    padding-top: 4.8rem !important;
                    padding-left: 1rem !important;
                    padding-right: 1rem !important;
                }
                div[data-testid="stTabs"] > div[role="tablist"] {
                    margin-left: -1rem;
                    margin-right: -1rem;
                    padding-left: 1rem;
                }
                .dashboard-kpi-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(current_user: str, active_view: str, *, on_logout: Callable[[], None]) -> str:
    import os
    guest_user = os.getenv("APP_GUEST_USERNAME", "khach").strip()
    is_guest = (st.session_state.get("app_login_username") == guest_user)

    if is_guest:
        initials = "KH"
        nav_items = (
            ("sobo", "Sơ bộ", ":material/pending_actions:"),
        )
    else:
        initials = "".join(part[:1] for part in current_user.split()[:2]).upper() or "AD"
        nav_items = (
            ("dashboard", "Dashboard", ":material/dashboard:"),
            ("entry", "Nhập hồ sơ", ":material/document_scanner:"),
            ("cases", "Quản lý hồ sơ", ":material/folder_shared:"),
            ("sobo", "Sơ bộ", ":material/pending_actions:"),
            ("organizations", "Tổ chức", ":material/corporate_fare:"),
            ("delivery", "Chuyển phát", ":material/local_shipping:"),
            ("templates", "Templates", ":material/description:"),
            ("settings", "Cấu hình", ":material/settings:"),
        )
    with st.container(key="app_header", horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(
            f"""
            <div class="app-brand">
                <div>
                    <div class="app-brand-main">Hệ Thống Thẩm Định</div>
                    <div class="app-brand-sub">Phòng Kinh Doanh</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for view_key, label, icon in nav_items:
            if st.button(
                label,
                icon=icon,
                type="primary" if active_view == view_key else "secondary",
                width="content",
                key=f"header_nav_{view_key}",
            ):
                st.session_state["active_view"] = view_key
                st.rerun()
        st.markdown(f'<span class="app-avatar">{html.escape(initials[:2])}</span>', unsafe_allow_html=True)
        if st.button(
            "Đăng xuất",
            icon=":material/logout:",
            type="secondary",
            width="content",
            key="header_logout",
        ):
            on_logout()
            st.rerun()
    return active_view


def _format_million(value: float) -> str:
    return f"{value / 1_000_000:,.0f}".replace(",", ".")


def render_dashboard_kpi_cards(
    *,
    year_projected: float,
    year_paid: float,
    year_unpaid: float,
    month_projected: float,
    selected_month: str,
) -> None:
    paid_ratio = 0 if year_projected <= 0 else min(100, round(year_paid / year_projected * 100))
    monthly_target = max(year_projected / 12, 1)
    target_ratio = 0 if month_projected <= 0 else min(100, round(month_projected / monthly_target * 100))
    st.markdown(
        f"""
        <div class="dashboard-kpi-grid">
            <div class="dashboard-kpi-card">
                <div class="dashboard-kpi-label">Doanh thu dự kiến cả năm</div>
                <div class="dashboard-kpi-value">{_format_million(year_projected)}<span class="dashboard-kpi-unit">Tr</span></div>
                <div class="dashboard-kpi-note">
                    <span class="material-symbols-outlined" style="font-size:16px;color:var(--app-primary)">trending_up</span>
                    <span>Dữ liệu theo bộ lọc hiện tại</span>
                </div>
            </div>
            <div class="dashboard-kpi-card">
                <div class="dashboard-kpi-label">Đã thanh toán cả năm</div>
                <div class="dashboard-kpi-value">{_format_million(year_paid)}<span class="dashboard-kpi-unit">Tr</span></div>
                <div class="dashboard-progress"><div class="dashboard-progress-fill" style="width:{paid_ratio}%"></div></div>
                <div class="dashboard-kpi-note" style="justify-content:flex-end;margin-top:0">Tỷ lệ thu: {paid_ratio}%</div>
            </div>
            <div class="dashboard-kpi-card">
                <div class="dashboard-kpi-label">Công nợ tồn cả năm</div>
                <div class="dashboard-kpi-value">{_format_million(year_unpaid)}<span class="dashboard-kpi-unit">Tr</span></div>
                <div class="dashboard-kpi-note">
                    <span class="material-symbols-outlined" style="font-size:16px;color:var(--app-error)">warning</span>
                    <span>Không tính hồ sơ trạng thái Hủy</span>
                </div>
            </div>
            <div class="dashboard-kpi-card primary">
                <span class="material-symbols-outlined dashboard-kpi-watermark">monetization_on</span>
                <div class="dashboard-kpi-label">Doanh thu dự kiến trong tháng</div>
                <div class="dashboard-kpi-value">{_format_million(month_projected)}<span class="dashboard-kpi-unit">Tr</span></div>
                <div class="dashboard-kpi-note">
                    <span>Tháng {html.escape(selected_month)}</span>
                    <span class="dashboard-kpi-badge">Đạt {target_ratio}% Target</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
