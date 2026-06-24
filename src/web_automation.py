from __future__ import annotations

import logging
import asyncio
import os
import random
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv

from .database_manager import get_db_path, resolve_records_db_path
from .sqlite_store import update_case


PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)

# Timeout mặc định cho các thao tác Playwright (ms)
DEFAULT_NAVIGATION_TIMEOUT = 45_000
DEFAULT_ACTION_TIMEOUT = 25_000
WEB_SUBMIT_TIMEOUT = 120_000
WEB_STATUS_TABLE_TIMEOUT = 120_000
WEB_STATUS_TABLE_POLL_INTERVAL = 500
WEB_SUBMIT_API_PATH = "/submit-yeu-cau-tham-dinh"


async def _wait_until_dom_ready(page, *, timeout: int = 10_000) -> None:
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        logger.debug("Trang chua dat domcontentloaded sau %sms, tiep tuc xu ly.", timeout)


async def _fill_login_credentials(page, *, username: str, password: str) -> None:
    result = await page.evaluate(
        """({ username, password }) => {
            const normalize = (value) => (value || "")
                .replace(/\\u0110/g, "D")
                .replace(/\\u0111/g, "d")
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .toLowerCase();
            const isVisible = (el) => {
                const box = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
            };
            const setValue = (el, value) => {
                const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, "value")?.set;
                if (setter) {
                    setter.call(el, value);
                } else {
                    el.value = value;
                }
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
            };
            const describe = (el) => [
                el.tagName,
                el.type,
                el.name,
                el.id,
                el.placeholder,
                el.autocomplete,
            ].filter(Boolean).join("|");
            const inputs = Array.from(document.querySelectorAll("input"))
                .filter((el) => !el.disabled && !el.readOnly && isVisible(el));
            const passwordInput = inputs.find((el) => normalize(el.type) === "password");
            if (!passwordInput) {
                return { filledUsername: false, filledPassword: false, reason: "password_not_found" };
            }
            const passwordIndex = inputs.indexOf(passwordInput);
            const usernameInput = inputs.find((el, index) => {
                if (el === passwordInput || index > passwordIndex) {
                    return false;
                }
                const haystack = normalize([
                    el.type,
                    el.name,
                    el.id,
                    el.placeholder,
                    el.autocomplete,
                    el.getAttribute("aria-label"),
                ].filter(Boolean).join(" "));
                return (
                    ["", "text", "email", "search", "tel"].includes(normalize(el.type)) ||
                    haystack.includes("user") ||
                    haystack.includes("email") ||
                    haystack.includes("login") ||
                    haystack.includes("account") ||
                    haystack.includes("tai khoan") ||
                    haystack.includes("ten dang nhap")
                );
            }) || inputs.find((el, index) => el !== passwordInput && index < passwordIndex);
            if (!usernameInput) {
                return { filledUsername: false, filledPassword: false, reason: "username_not_found" };
            }
            setValue(usernameInput, username);
            setValue(passwordInput, password);
            return {
                filledUsername: usernameInput.value === username,
                filledPassword: passwordInput.value === password,
                usernameInput: describe(usernameInput),
                passwordInput: describe(passwordInput),
            };
        }""",
        {"username": username, "password": password},
    )
    if not result.get("filledUsername") or not result.get("filledPassword"):
        raise RuntimeError(f"Không điền được thông tin đăng nhập: {result}")
    logger.info(
        "Da dien thong tin dang nhap vao form: username=%s, password=%s",
        result.get("usernameInput"),
        result.get("passwordInput"),
    )


async def _visible_login_prompt_count(page) -> int:
    login_nav = page.locator("#login-nav").first
    if await login_nav.count() > 0 and await login_nav.is_visible():
        return 1

    return int(
        await page.evaluate(
            """() => {
                const normalize = (value) => (value || "")
                    .replace(/\\u0110/g, "D")
                    .replace(/\\u0111/g, "d")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();
                const isVisible = (el) => {
                    const box = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
                };
                return Array.from(document.querySelectorAll("button, a, [role='button']"))
                    .filter((el) => {
                        if (el.id === "login-nav") {
                            return isVisible(el);
                        }
                        const text = normalize(el.textContent);
                        return isVisible(el) && (
                            text === "dang nhap" ||
                            text === "login" ||
                            text === "log in" ||
                            text === "sign in"
                        );
                    }).length;
            }"""
        )
    )


async def _click_visible_login_prompt(page) -> bool:
    login_prompt = page.locator(
        "#login-nav, "
        "button:has-text('Đăng Nhập'), "
        "button:has-text('Đăng nhập'), "
        "button:has-text('Login'), "
        "button:has-text('Log in'), "
        "button:has-text('Sign in'), "
        "a:has-text('Đăng Nhập'), "
        "a:has-text('Đăng nhập'), "
        "a:has-text('Login'), "
        "a:has-text('Log in'), "
        "a:has-text('Sign in'), "
        "[role='button']:has-text('Đăng Nhập'), "
        "[role='button']:has-text('Đăng nhập'), "
        "[role='button']:has-text('Login'), "
        "[role='button']:has-text('Log in'), "
        "[role='button']:has-text('Sign in')"
    ).first
    if await login_prompt.count() > 0:
        await login_prompt.scroll_into_view_if_needed()
        await login_prompt.click(timeout=10_000, force=True)
        return True

    return bool(
        await page.evaluate(
            """() => {
                const normalize = (value) => (value || "")
                    .replace(/\\u0110/g, "D")
                    .replace(/\\u0111/g, "d")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLowerCase();
                const isVisible = (el) => {
                    const box = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
                };
                const candidates = Array.from(document.querySelectorAll("button, a, [role='button']"));
                const login = candidates.find((el) => {
                    const text = normalize(el.textContent).trim();
                    return isVisible(el) && ["dang nhap", "login", "log in", "sign in"].includes(text);
                });
                if (!login) {
                    return false;
                }
                login.click();
                return true;
            }"""
        )
    )


async def _wait_for_login_success(page, *, timeout_ms: int = 30_000) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        password_count = await page.locator("input[type='password']").count()
        login_prompt_count = await _visible_login_prompt_count(page)
        if password_count == 0 and login_prompt_count == 0:
            logger.info("Xac nhan dang nhap thanh cong, URL hien tai: %s", page.url)
            return
        await page.wait_for_timeout(500)

    raise RuntimeError(
        "Đăng nhập chưa thành công: trang vẫn hiển thị nút Đăng Nhập/Login "
        f"hoặc còn ô mật khẩu. URL hiện tại: {page.url}"
    )


async def _recover_from_callback_url(page) -> None:
    if "#/callback" not in page.url:
        return

    logger.info("Trang dang dung o callback sau dang nhap, refresh lai de vao ung dung.")
    await page.reload(wait_until="domcontentloaded")
    await _wait_until_dom_ready(page)
    await page.wait_for_timeout(2_000)


async def _click_yctd_navigation(page) -> bool:
    yctd_link = page.locator(
        "a:has-text('YCTD'), "
        "a:has-text('Yêu cầu thẩm định'), "
        "a:has-text('Appraisal request'), "
        "a:has-text('Valuation request'), "
        "a:has-text('Request appraisal'), "
        "button:has-text('YCTD'), "
        "button:has-text('Gửi Yêu Cầu Thẩm Định'), "
        "button:has-text('Yêu cầu thẩm định'), "
        "button:has-text('Appraisal request'), "
        "button:has-text('Valuation request'), "
        "[role='button']:has-text('YCTD'), "
        "[role='button']:has-text('Gửi Yêu Cầu Thẩm Định'), "
        "[role='button']:has-text('Yêu cầu thẩm định'), "
        "[role='button']:has-text('Appraisal request'), "
        "[role='button']:has-text('Valuation request'), "
        "a[href*='form-customer'], "
        "a[href*='yctd'], "
        "a[href*='YCTD'], "
        "a[href*='tham-dinh']"
    ).first
    if await yctd_link.count() == 0:
        return False
    await yctd_link.click()
    await _wait_until_dom_ready(page)
    return True


WEB_ENTRY_REQUIRED_FIELDS = [
    ("contract_number", "Số hợp đồng", ("contract_number",)),
    ("customer_info", "Tên khách hàng", ("customer_info", "customer_name")),
    ("customer_address", "Địa chỉ khách hàng", ("customer_address",)),
    ("asset_description", "Tài sản thẩm định", ("asset_description", "dia_chi", "dia_chi_thua_dat", "city")),
    ("valuation_purpose", "Mục đích thẩm định", ("valuation_purpose",)),
    ("asset_type", "Loại tài sản", ("asset_type",)),
    ("source", "Nguồn/ngân hàng", ("source",)),
]


def _has_value(data: Mapping[str, object], keys: tuple[str, ...]) -> bool:
    return any(str(data.get(key) or "").strip() for key in keys)


def missing_web_entry_fields(data: Mapping[str, object]) -> list[dict[str, str]]:
    """Return required app fields that should be completed before Web automation."""
    missing: list[dict[str, str]] = []
    for field_key, label, source_keys in WEB_ENTRY_REQUIRED_FIELDS:
        if not _has_value(data, source_keys):
            missing.append(
                {
                    "field": field_key,
                    "label": label,
                    "source": " / ".join(source_keys),
                }
            )
    return missing


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", without_marks.replace("\u0111", "d").replace("\u0110", "D").lower()).strip()


def _purpose_web_value(raw_purpose: str) -> str:
    purpose = _normalize_text(raw_purpose)
    if not purpose:
        return "Khác"
    if "xu ly tai san dam bao" in purpose:
        return "Thanh lý, phát mãi tài sản"
    if "vietcombank" in purpose or "vcb" in purpose:
        return "Tham khảo vay vốn tại Vietcombank"
    if "chinh sach" in purpose or "vbsp" in purpose:
        return "Thẩm định vay vốn ngân hàng"
    loan_banks = [
        "sacombank",
        "bidv",
        "chinh sach xa hoi",
        "agribank",
        "msb",
        "co-op bank",
        "coop bank",
        "vp bank",
        "vpbank",
        "seabank",
        "vietinbank",
        "esun bank",
        "mb bank",
        "mbbank",
    ]
    if any(bank in purpose for bank in loan_banks) or "vay von" in purpose or "the chap" in purpose:
        return "Thẩm định vay vốn ngân hàng"
    return "Khác"


def _asset_web_value(raw_asset_type: str) -> str:
    asset_type = _normalize_text(raw_asset_type)
    if asset_type == _normalize_text("BĐS đặc thù khác"):
        return "Bất động sản đặc thù"
    if asset_type == _normalize_text("Máy móc thiết bị"):
        return "Máy móc thiết bị"
    return ""


def _asset_web_values(raw_asset_type: str) -> tuple[str, str]:
    asset_type = _normalize_text(raw_asset_type)
    if "dac thu" in asset_type:
        return "Bất động sản đặc thù", "Bất động sản đặc thù"
    if any(token in asset_type for token in ("bds", "bat dong san")):
        return "Bất động sản", "Bất động sản đặc thù"
    if "may moc" in asset_type or "thiet bi" in asset_type:
        return "Máy móc thiết bị", "Máy móc thiết bị"
    return "", ""


def _bank_web_value(raw_source: str) -> str:
    source = _normalize_text(raw_source)
    if not source:
        return "KHN"
    rules = [
        ("mb amc", "MB AMC"),
        ("vcb", "VIETCOMBANK"),
        ("vietcombank", "VIETCOMBANK"),
        ("vietinbank", "VIETINBANK"),
        ("bidv", "BIDV"),
        ("agribank", "AGRIBANK"),
        ("seabank", "SeAbank"),
        ("mb", "MBBANK"),
        ("sacombank", "SACOMBANK"),
        ("nhcs", "VBSP"),
        ("shb", "SHB"),
        ("acb", "ACB"),
        ("vp bank", "VPBank"),
        ("vpbank", "VPBank"),
    ]
    for needle, web_value in rules:
        if needle in source:
            return web_value
    return "KHN"


def _source_web_candidates(raw_source: str) -> list[str]:
    source = str(raw_source or "").strip()
    candidates = [source, _bank_web_value(source)]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = _normalize_text(candidate)
        if candidate and key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def _is_submit_response(response) -> bool:
    return WEB_SUBMIT_API_PATH in response.url


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WebAutomationSettings:
    """Holds all configuration needed for web automation tasks."""

    internal_web_url: str
    web_username: str
    web_password: str
    records_db_path: str


def load_web_automation_settings() -> WebAutomationSettings:
    """Read INTERNAL_WEB_URL, WEB_USERNAME, WEB_PASSWORD and RECORDS_DB_PATH
    from environment variables (or ``.env`` / ``API.env``) and return a frozen
    settings object.

    ``records_db_path`` is resolved through :func:`get_db_path` so that every
    component in the project points at the same absolute SQLite file.
    """
    load_dotenv(PROJECT_ROOT / "API.env", override=True)

    internal_web_url = os.getenv("INTERNAL_WEB_URL", "").strip()
    web_username = os.getenv("WEB_USERNAME", "").strip()
    web_password = os.getenv("WEB_PASSWORD", "").strip()
    records_db_path = get_db_path()

    return WebAutomationSettings(
        internal_web_url=internal_web_url,
        web_username=web_username,
        web_password=web_password,
        records_db_path=records_db_path,
    )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def fetch_record_data(record_id: int | str) -> dict[str, str] | None:
    """Fetch all columns of a single record from the ``records`` table.

    Parameters
    ----------
    record_id:
        The primary‐key ``id`` of the record to retrieve.

    Returns
    -------
    dict[str, str] | None
        A dictionary mapping column names to their string values, or *None* if
        the record does not exist.
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM records WHERE id = ?",
            (int(record_id),),
        )
        row = await cursor.fetchone()

    if row is None:
        return None
    return {key: str(row[key] or "") for key in row.keys()}


# ---------------------------------------------------------------------------
# Browser login & navigation
# ---------------------------------------------------------------------------

async def start_browser_and_login(browser_context, page=None):
    """Mở trang INTERNAL_WEB_URL, đăng nhập và điều hướng đến form
    *Gửi Yêu Cầu Thẩm Định*.

    Parameters
    ----------
    browser_context : playwright.async_api.BrowserContext
        BrowserContext đã được tạo sẵn (headless=False) từ bên ngoài.
        Ví dụ::

            from playwright.async_api import async_playwright

            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await start_browser_and_login(context)

    Returns
    -------
    playwright.async_api.Page
        Đối tượng Page đã đăng nhập và đang hiển thị form
        *Gửi Yêu Cầu Thẩm Định*, sẵn sàng để điền dữ liệu.

    Raises
    ------
    RuntimeError
        Khi thiếu cấu hình hoặc đăng nhập thất bại.
    """
    settings = load_web_automation_settings()

    if not settings.internal_web_url:
        raise RuntimeError("Thiếu biến môi trường INTERNAL_WEB_URL.")
    if not settings.web_username or not settings.web_password:
        raise RuntimeError("Thiếu biến môi trường WEB_USERNAME hoặc WEB_PASSWORD.")

    if page is None:
        page = await browser_context.new_page()
    page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)
    page.set_default_timeout(DEFAULT_ACTION_TIMEOUT)

    # ---- 1. Truy cập trang chủ / trang đăng nhập ----
    logger.info("Đang truy cập %s ...", settings.internal_web_url)
    await page.goto(settings.internal_web_url, wait_until="domcontentloaded")

    # Trang chu chi hien nut "Dang Nhap"; form password nam o trang SSO sau khi click.
    password_input = page.locator("input[type='password']")
    if await password_input.count() == 0:
        clicked_login = await _click_visible_login_prompt(page)
        if clicked_login:
            logger.info("Da bam nut dang nhap.")
            await page.wait_for_timeout(1000)
            await _wait_until_dom_ready(page)
            try:
                await page.wait_for_selector("input[type='password']", timeout=10_000)
            except Exception:
                logger.debug("Chua thay o password sau khi bam Login, tiep tuc kiem tra trang hien tai.")

    # ---- 2. Đăng nhập nếu thấy form login ----
    password_input = page.locator("input[type='password']")
    if await password_input.count() > 0:
        logger.info("Phát hiện trang đăng nhập, đang điền thông tin...")

        await _fill_login_credentials(
            page,
            username=settings.web_username,
            password=settings.web_password,
        )

        # Nhấn nút đăng nhập
        submit_btn = page.locator(
            "button[type='submit'], "
            "input[type='submit'], "
            "button:has-text('Đăng nhập'), "
            "button:has-text('Login'), "
            "button:has-text('Sign in')"
        ).first
        await submit_btn.click()

        # Chờ trang chuyển hướng sau đăng nhập
        await _wait_until_dom_ready(page)
        await _wait_for_login_success(page)
    else:
        login_prompt_count = await _visible_login_prompt_count(page)
        if login_prompt_count > 0:
            raise RuntimeError(
                "Chưa đăng nhập: trang vẫn hiển thị nút Đăng Nhập/Login nhưng không mở được form mật khẩu."
            )
        logger.info("Không thấy form đăng nhập và không còn nút đăng nhập — có thể đã đăng nhập sẵn.")

    await _recover_from_callback_url(page)

    # ---- 3. Điều hướng trực tiếp đến trang Gửi Yêu Cầu Thẩm Định (YCTD) ----
    yctd_url = settings.internal_web_url.rstrip("/") + "/#/form-customer"
    logger.info("Đang điều hướng trực tiếp đến trang YCTD: %s", yctd_url)
    try:
        await page.goto(yctd_url, wait_until="networkidle", timeout=30_000)
    except Exception:
        logger.warning("Không thể đợi networkidle khi chuyển sang trang YCTD, tiếp tục bằng domcontentloaded")
        await page.goto(yctd_url, wait_until="domcontentloaded", timeout=20_000)

    await _wait_until_dom_ready(page)
    await page.wait_for_timeout(2_000)

    if "#/callback" in page.url:
        await _recover_from_callback_url(page)
        logger.info("Đang quay lại trang YCTD sau khi giải quyết callback: %s", yctd_url)
        await page.goto(yctd_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2_000)

    # ---- 4. Chọn tab "Thẩm định tài sản" nếu có ----
    tab_tham_dinh = page.locator(
        "a:has-text('Thẩm định tài sản'), "
        "a:has-text('Asset appraisal'), "
        "a:has-text('Asset valuation'), "
        "[role='tab']:has-text('Thẩm định tài sản'), "
        "[role='tab']:has-text('Asset appraisal'), "
        "[role='tab']:has-text('Asset valuation')"
    ).first
    if await tab_tham_dinh.count() > 0:
        await tab_tham_dinh.click()
        await _wait_until_dom_ready(page)
        logger.info("Đã chọn tab 'Thẩm định tài sản'.")

    # ---- 5. Xác nhận đã đến đúng trang ----
    heading = page.locator(
        "text='GỬI YÊU CẦU THẨM ĐỊNH', "
        "text='Gửi Yêu Cầu Thẩm Định', "
        "text='Appraisal Request', "
        "text='Valuation Request', "
        "h1:has-text('thẩm định'), "
        "h1:has-text('appraisal'), "
        "h1:has-text('valuation'), "
        "h2:has-text('thẩm định'), "
        "h2:has-text('appraisal'), "
        "h2:has-text('valuation'), "
        ".page-title:has-text('thẩm định')"
    ).first
    if await heading.count() > 0:
        logger.info("Đã vào trang Gửi Yêu Cầu Thẩm Định thành công.")
    else:
        logger.warning(
            "Không xác nhận được tiêu đề trang 'Gửi Yêu Cầu Thẩm Định'. "
            "URL hiện tại: %s — vui lòng kiểm tra thủ công.",
            page.url,
        )

    try:
        await page.wait_for_selector("#input-tenKhachHang", timeout=30_000)
    except Exception as exc:
        raise RuntimeError(f"Không mở được form Gửi Yêu Cầu Thẩm Định sau đăng nhập. URL hiện tại: {page.url}") from exc

    return page


# ---------------------------------------------------------------------------
# Form filling — THÔNG TIN KHÁCH HÀNG & THÔNG TIN THẨM ĐỊNH
# ---------------------------------------------------------------------------

async def _select_dropdown(page, label: str, value: str) -> bool:
    """Chọn một giá trị trong dropdown (``<select>``) theo label.

    Thử ba chiến lược lần lượt:
    1. ``select_option(label=...)`` — khớp chính xác text hiển thị.
    2. ``select_option(label=...)`` với giá trị viết hoa chuẩn hóa.
    3. Fallback: click dropdown → chọn ``<option>`` chứa text gần đúng.
    """
    if not value:
        return False

    select = page.get_by_label(label)

    # Chiến lược 1: khớp chính xác
    try:
        await select.select_option(label=value, timeout=3000)
        logger.info("Dropdown '%s' → '%s' (exact match)", label, value)
        return True
    except Exception:
        pass

    # Chiến lược 2: khớp không phân biệt hoa/thường
    try:
        options = await select.locator("option").all_text_contents()
        for option_text in options:
            if option_text.strip().casefold() == value.strip().casefold():
                await select.select_option(label=option_text)
                logger.info("Dropdown '%s' → '%s' (case-insensitive)", label, option_text)
                return True
    except Exception:
        pass

    # Chiến lược 3: khớp chứa chuỗi con (partial match)
    try:
        options = await select.locator("option").all_text_contents()
        needle = value.strip().casefold()
        for option_text in options:
            if needle in option_text.strip().casefold():
                await select.select_option(label=option_text)
                logger.info("Dropdown '%s' → '%s' (partial match for '%s')", label, option_text, value)
                return True
    except Exception:
        pass

    if await _select_ng_dropdown_by_label(page, label, value):
        return True

    logger.warning("Dropdown '%s': không tìm thấy giá trị '%s' trong danh sách.", label, value)
    return False


async def _open_ng_dropdown_by_label(page, label: str) -> bool:
    return bool(await page.evaluate(
        """(label) => {
            const normalize = (text) => (text || "")
                .replaceAll("Đ", "D")
                .replaceAll("đ", "d")
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .toLowerCase()
                .replace(/\\s+/g, " ")
                .trim();
            const wanted = normalize(label);
            const isVisible = (el) => {
                const box = el.getBoundingClientRect();
                return box.width > 0 && box.height > 0 && window.getComputedStyle(el).display !== "none" && window.getComputedStyle(el).visibility !== "hidden";
            };
            const labelNode = Array.from(document.querySelectorAll("label"))
                .find((node) => normalize(node.textContent).includes(wanted) && isVisible(node));
            if (!labelNode) return false;
            let container = labelNode;
            for (let i = 0; i < 6 && container; i += 1) {
                const ngSelect = container.querySelector?.("ng-select");
                if (ngSelect && isVisible(ngSelect)) {
                    ngSelect.scrollIntoView({ block: "center", inline: "center" });
                    ngSelect.click();
                    const input = ngSelect.querySelector("input");
                    if (input) input.focus();
                    return true;
                }
                container = container.parentElement;
            }
            const rect = labelNode.getBoundingClientRect();
            const candidate = Array.from(document.querySelectorAll("ng-select")).find((node) => {
                const box = node.getBoundingClientRect();
                return isVisible(node) && box.x > rect.x && Math.abs(box.y - rect.y) < 90;
            });
            if (!candidate) return false;
            candidate.scrollIntoView({ block: "center", inline: "center" });
            candidate.click();
            const input = candidate.querySelector("input");
            if (input) input.focus();
            return true;
        }""",
        label,
    ))


async def _visible_ng_options(page) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    options = page.locator(".ng-option")
    for index in range(await options.count()):
        option = options.nth(index)
        try:
            if await option.is_visible(timeout=300):
                text = (await option.inner_text()).strip()
                if text:
                    result.append((index, text))
        except Exception:
            continue
    return result


async def _select_ng_dropdown_by_label(page, label: str, value: str) -> bool:
    if not value:
        return False
    if not await _open_ng_dropdown_by_label(page, label):
        return False
    await page.wait_for_timeout(500)
    # Robust fallback: type text and press Enter
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(value, delay=50)
    await page.wait_for_timeout(1000)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(500)
    logger.info("Dropdown '%s' typed '%s' and pressed Enter", label, value)
    return True


async def _select_ng_dropdown_by_selector(page, selector: str, value: str, *, label: str) -> bool:
    if not value:
        return False

    dropdown = page.locator(selector).first
    try:
        await dropdown.wait_for(state="visible", timeout=10_000)
        await page.wait_for_function(
            """(selector) => {
                const el = document.querySelector(selector);
                return el && !el.className.includes("ng-select-disabled") && el.getAttribute("aria-disabled") !== "true";
            }""",
            arg=selector,
            timeout=10_000,
        )
        await dropdown.scroll_into_view_if_needed()
        await dropdown.click(timeout=5_000, force=True)
        await page.wait_for_timeout(500)
        normalized_value = _normalize_text(value)
        options = await _visible_ng_options(page)
        for index, option_text in options:
            normalized_option = _normalize_text(option_text)
            if normalized_option == normalized_value or normalized_value in normalized_option:
                await page.locator(".ng-option").nth(index).click()
                await page.wait_for_timeout(500)
                logger.info("Dropdown '%s' -> '%s' qua selector %s", label, option_text, selector)
                return True

        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(value, delay=50)
        await page.wait_for_timeout(1_000)
        options = await _visible_ng_options(page)
        for index, option_text in options:
            normalized_option = _normalize_text(option_text)
            if normalized_option == normalized_value or normalized_value in normalized_option:
                await page.locator(".ng-option").nth(index).click()
                await page.wait_for_timeout(500)
                logger.info("Dropdown '%s' -> '%s' qua selector %s", label, option_text, selector)
                return True
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        selected_text = (await dropdown.inner_text()).strip()
        if _normalize_text(value) in _normalize_text(selected_text):
            logger.info("Dropdown '%s' typed '%s' and selected via Enter", label, value)
            return True
    except Exception as exc:
        logger.warning("Dropdown '%s': khong chon duoc '%s' qua selector %s: %s", label, value, selector, exc)

    return False


async def _ng_dropdown_text(page, selector: str) -> str:
    try:
        return (await page.locator(selector).first.inner_text(timeout=1_000)).strip()
    except Exception:
        return ""


async def _ng_dropdown_is_disabled(page, selector: str) -> bool:
    try:
        dropdown = page.locator(selector).first
        return bool(await dropdown.evaluate(
            """(el) => el.className.includes("ng-select-disabled") || el.getAttribute("aria-disabled") === "true" """
        ))
    except Exception:
        return False


async def _select_ng_dropdown_matching_text(page, label: str, source_text: str) -> bool:
    if not source_text:
        return False
    if not await _open_ng_dropdown_by_label(page, label):
        return False
    await page.wait_for_timeout(500)
    # Robust fallback: type text and press Enter
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(source_text, delay=50)
    await page.wait_for_timeout(1500)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(500)
    logger.info("Dropdown '%s' typed '%s' and pressed Enter", label, source_text)
    return True


async def _select_random_ng_option_containing(page, label: str, needles: list[str]) -> bool:
    if not await _open_ng_dropdown_by_label(page, label):
        return False
    await page.wait_for_timeout(500)
    import random
    chosen_needle = random.choice(needles)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(chosen_needle, delay=50)
    await page.wait_for_timeout(1500)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(500)
    logger.info("Dropdown '%s' typed random needle '%s' and pressed Enter", label, chosen_needle)
    return True


async def _check_by_label_text(page, label: str) -> bool:
    return bool(await page.evaluate(
        """(label) => {
            const normalize = (text) => (text || "")
                .replaceAll("Đ", "D")
                .replaceAll("đ", "d")
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .toLowerCase()
                .replace(/\\s+/g, " ")
                .trim();
            const wanted = normalize(label);
            const labelNode = Array.from(document.querySelectorAll("label"))
                .find((node) => normalize(node.textContent).includes(wanted));
            if (!labelNode) return false;
            
            let input = labelNode.querySelector("input[type='checkbox'], input[type='radio']")
                || labelNode.parentElement?.querySelector("input[type='checkbox'], input[type='radio']");
            
            if (!input && labelNode.hasAttribute("for")) {
                input = document.getElementById(labelNode.getAttribute("for"));
            }
            
            if (input) {
                if (!input.checked) {
                    input.click();
                    // Fallback force click if simple click didn't check it
                    if (!input.checked) labelNode.click(); 
                }
                return true;
            }
            
            labelNode.click();
            return true;
        }""",
        label,
    ))


async def _hide_fields_by_label_text(page, labels: list[str]) -> list[str]:
    return list(await page.evaluate(
        """(labels) => {
            const normalize = (text) => (text || "")
                .replaceAll("Đ", "D")
                .replaceAll("đ", "d")
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .toLowerCase()
                .replace(/\\s+/g, " ")
                .trim();
            const wanted = labels.map(normalize);
            const hidden = [];
            const nodes = Array.from(document.querySelectorAll("label, .form-label, [class*='label']"));
            for (const node of nodes) {
                const text = normalize(node.textContent || "");
                const matchIndex = wanted.findIndex((label) => label && text.includes(label));
                if (matchIndex < 0) continue;

                let container = node;
                for (let i = 0; i < 5 && container; i += 1) {
                    const hasField = container.querySelector?.("input, textarea, select, ng-select");
                    const box = container.getBoundingClientRect();
                    if (hasField && box.width > 0 && box.height > 0) break;
                    container = container.parentElement;
                }
                if (!container) continue;

                for (const field of Array.from(container.querySelectorAll("input, textarea"))) {
                    if (field.type !== "hidden") {
                        field.value = "";
                        field.dispatchEvent(new Event("input", { bubbles: true }));
                        field.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                }
                container.style.display = "none";
                hidden.push(labels[matchIndex]);
            }
            return Array.from(new Set(hidden));
        }""",
        labels,
    ))


async def _hide_handover_authorization_fields(page) -> None:
    hidden = await _hide_fields_by_label_text(
        page,
        [
            "Người nhận bàn giao",
            "Chức vụ người nhận bàn giao",
            "Điện thoại người nhận bàn giao",
            "Căn cứ/giấy ủy quyền đại diện",
            "Căn cứ/ủy quyền đại diện",
        ],
    )
    if hidden:
        logger.info("Đã ẩn các trường bàn giao/ủy quyền: %s", ", ".join(hidden))


async def fill_basic_info(page, data: Mapping[str, str]) -> None:
    """Điền phần **THÔNG TIN KHÁCH HÀNG** và **THÔNG TIN THẨM ĐỊNH** trên
    form *Gửi Yêu Cầu Thẩm Định*.

    Parameters
    ----------
    page : playwright.async_api.Page
        Trang đã mở sẵn form YCTD (kết quả từ
        :func:`start_browser_and_login`).
    data : Mapping[str, str]
        Dữ liệu hồ sơ.  Các key được sử dụng:

        ========================  =========================================
        Key                       Trường trên form
        ========================  =========================================
        ``customer_info``         Họ tên *
        ``customer_phone``        Số điện thoại *
        ``customer_email``        Email *
        ``customer_address``      Địa chỉ *
        ``is_preliminary``        True → check "Định giá sơ bộ",
                                  False/missing → check "Thẩm định giá"
        ``branch``                Chi nhánh thẩm định *
        ``office``                Chọn Văn Phòng *
        ``note``                  Ghi chú
        ========================  =========================================
    """
    # ── THÔNG TIN KHÁCH HÀNG ──────────────────────────────────────────────
    # Họ tên (Dynamic)
    ho_ten = str(data.get("customer_info") or data.get("customer_name") or "").strip()
    if ho_ten:
        await page.locator("#input-tenKhachHang").fill(ho_ten)
        logger.info("Điền Họ tên: %s", ho_ten)

    # Số điện thoại (Fixed)
    await page.locator("#input-soDienThoai").fill("0905226968")
    logger.info("Điền Số điện thoại (Fixed): 0905226968")

    # Email (Fixed)
    admin_email = os.getenv("ADMIN_EMAIL", "truongpham.sacc@gmail.com")
    await page.locator("#input-email").fill(admin_email)
    logger.info(f"Điền Email (Env): {admin_email}")

    # Địa chỉ (Dynamic)
    dia_chi = str(data.get("customer_address") or "").strip()
    if dia_chi:
        await page.locator("#input-diachi").fill(dia_chi)
        logger.info("Điền Địa chỉ: %s", dia_chi)

    # ── THÔNG TIN THẨM ĐỊNH ──────────────────────────────────────────────

    # Kiểu thẩm định * (Fixed: Thẩm định giá)
    await _check_by_label_text(page, "Thẩm định giá")
    logger.info("Chọn Kiểu thẩm định: Thẩm định giá")
    
    # Chi nhánh thẩm định (Dynamic mapping)
    branch_val = str(data.get("valuation_branch") or data.get("branch") or "").strip()
    if branch_val.lower().startswith("cn "):
        branch_val = branch_val[3:].strip()
    if not branch_val:
        branch_val = "Đà Nẵng"
    branch_selected = await _select_ng_dropdown_by_selector(
        page,
        "#input-chiNhanh",
        branch_val,
        label="Chi nhánh thẩm định",
    ) or await _select_dropdown(page, "Chi nhánh thẩm định", branch_val)
    branch_text = _normalize_text(await _ng_dropdown_text(page, "#input-chiNhanh"))
    if not branch_selected or _normalize_text(branch_val) not in branch_text:
        raise RuntimeError(f"Không chọn được Chi nhánh thẩm định trên Web: {branch_val}")
    logger.info("Chọn Chi nhánh thẩm định: %s", branch_val)

    # Chọn Văn Phòng (Dynamic mapping)
    office_val = str(data.get("office") or "").strip()
    if office_val.lower().startswith("vp "):
        office_val = office_val[3:].strip()
    if not office_val:
        office_val = "Đà Nẵng"
    office_selected = await _select_ng_dropdown_by_selector(
        page,
        "#input-vanPhong",
        office_val,
        label="Chọn Văn Phòng",
    ) or await _select_dropdown(page, "Chọn Văn Phòng", office_val)
    office_text = _normalize_text(await _ng_dropdown_text(page, "#input-vanPhong"))
    if not office_selected or _normalize_text(office_val) not in office_text:
        raise RuntimeError(f"Không chọn được Văn phòng thẩm định trên Web: {office_val}")
    logger.info("Chọn Văn Phòng: %s", office_val)

    # Ghi chú: Bỏ qua (Skip)
    await _hide_handover_authorization_fields(page)


# ---------------------------------------------------------------------------
# Form filling — THÔNG TIN TÀI SẢN THẨM ĐỊNH
# ---------------------------------------------------------------------------

async def _select_cascading_dropdown(
    page,
    label: str,
    value: str,
    *,
    wait_after: bool = True,
) -> bool:
    """Chọn giá trị trong dropdown phụ thuộc (cascading).

    Sau khi chọn xong sẽ gọi ``wait_for_load_state('networkidle')`` để
    đợi server trả về danh sách con tương ứng (ví dụ: chọn Tỉnh → load
    danh sách Quận).

    Returns
    -------
    bool
        ``True`` nếu chọn được giá trị, ``False`` nếu không tìm thấy.
    """
    if not value:
        return False

    select = page.get_by_label(label)

    # Đợi dropdown hiện diện trên trang
    try:
        await select.wait_for(state="attached", timeout=DEFAULT_ACTION_TIMEOUT)
    except Exception:
        logger.warning("Dropdown '%s' không tồn tại trên trang.", label)
        return False

    # Thử chọn chính xác
    matched = False
    try:
        await select.select_option(label=value, timeout=3000)
        matched = True
    except Exception:
        pass

    # Thử khớp không phân biệt hoa/thường hoặc chứa chuỗi con
    if not matched:
        try:
            options = await select.locator("option").all_text_contents()
            needle = value.strip().casefold()
            for option_text in options:
                text = option_text.strip()
                if not text or text.casefold() in ("chọn", "chọn...", "chọn tỉnh/thành phố", "-- chọn --"):
                    continue

                if text.casefold() == needle or needle in text.casefold() or text.casefold() in needle:
                    await select.select_option(label=text)
                    matched = True
                    break
        except Exception:
            pass

    if matched:
        logger.info("Cascading dropdown '%s' → '%s'", label, value)
        if wait_after:
            # Đợi server cập nhật danh sách dropdown con
            await page.wait_for_load_state("networkidle")
            # Thêm khoảng chờ ngắn để JS render xong options mới
            await page.wait_for_timeout(500)
        return True

    logger.warning(
        "Cascading dropdown '%s': không tìm thấy '%s' trong danh sách.",
        label,
        value,
    )
    return False


async def fill_asset_info(page, data: Mapping[str, str]) -> None:
    """Điền phần **THÔNG TIN TÀI SẢN THẨM ĐỊNH** trên form YCTD.

    Parameters
    ----------
    page : playwright.async_api.Page
        Trang đã mở sẵn form YCTD.
    data : Mapping[str, str]
        Dữ liệu hồ sơ.  Các key được sử dụng:

        ========================  =========================================
        Key                       Trường trên form
        ========================  =========================================
        ``tinh_thanh_pho``        Tỉnh/ thành phố  (cascading)
        ``quan_huyen``            Quận/ huyện       (cascading)
        ``phuong_xa``             Phường/ xã        (cascading)
        ``duong_pho``             Đường/phố
        ``so_nha``                Số nhà
        ``asset_description``     Tài sản thẩm định *
        ``valuation_purpose``     Mục đích thẩm định *
        ``asset_type``            Loại tài sản *
        ``asset_group``           Nhóm tài sản *
        ========================  =========================================

    Notes
    -----
    Ba dropdown địa chỉ (Tỉnh → Quận → Phường) là **cascading**: sau khi
    chọn Tỉnh, trang sẽ gọi API để load danh sách Quận, tương tự khi chọn
    Quận sẽ load Phường.  Hàm sử dụng ``wait_for_load_state('networkidle')``
    giữa mỗi bước để đảm bảo danh sách con đã sẵn sàng.
    """
    # ── Địa chỉ tài sản (cascading dropdowns) ────────────────────────────

    # Tinh/thanh pho: tim ten tinh trong data
    city = str(data.get("city") or "").strip()
    dia_chi = str(data.get("dia_chi") or "").strip()
    
    # Nếu không có city rõ ràng nhưng có dia_chi, tách phần cuối của địa chỉ làm tỉnh/thành phố
    if not city and dia_chi:
        parts = [p.strip() for p in dia_chi.split(",")]
        if parts:
            if len(parts) > 1 and parts[-1].casefold() in ("việt nam", "viet nam", "vn"):
                city = parts[-2]
            else:
                city = parts[-1]

    if city:
        await _select_ng_dropdown_matching_text(page, "Tỉnh/ thành phố", city)
    
    asset_description = str(data.get("asset_description") or dia_chi or city).strip()
    if asset_description:
        await page.locator("#input-taisanthamdinh").fill(asset_description)
        logger.info("Dien Tai san tham dinh: %s", asset_description)

    # Quận/huyện, Phường/xã, Đường/phố, Số nhà, Tài sản thẩm định: Bỏ qua (Skip)

    # ── Dropdowns thường ─────────────────────────────────────────────────

    # Muc dich tham dinh: map du lieu Word/SQLite sang text dropdown web.
    muc_dich = str(data.get("valuation_purpose") or "").strip()
    await _select_dropdown(page, "Mục đích thẩm định", _purpose_web_value(muc_dich))

    source = str(data.get("source") or "").strip()
    for source_candidate in _source_web_candidates(source):
        if await _select_dropdown(page, "Nguồn/đối tác", source_candidate):
            break

    # Loại tài sản & Nhóm tài sản (Dynamic mapping)
    asset_type = str(data.get("asset_type") or "").strip()
    target_type, target_group = _asset_web_values(asset_type)

    if target_type:
        if await _ng_dropdown_is_disabled(page, "#input-loaiTaiSanDesk"):
            logger.info("Bo qua Loai tai san vi web dang disable truong #input-loaiTaiSanDesk.")
        else:
            type_selected = await _select_ng_dropdown_by_selector(
                page,
                "#input-loaiTaiSanDesk",
                target_type,
                label="Loại tài sản",
            )
            if not type_selected:
                raise RuntimeError(f"Không chọn được Loại tài sản trên Web: {target_type} (dữ liệu app: {asset_type})")

        group_selected = await _select_ng_dropdown_by_selector(
            page,
            "#input-nhomTaiSan",
            target_group,
            label="Nhóm tài sản",
        )
        group_text = _normalize_text(await _ng_dropdown_text(page, "#input-nhomTaiSan"))
        if not group_selected or _normalize_text(target_group) not in group_text:
            raise RuntimeError(f"Không chọn được Nhóm tài sản trên Web: {target_group} (dữ liệu app: {asset_type})")
    await _hide_handover_authorization_fields(page)


# ---------------------------------------------------------------------------
# Form filling — Tài liệu, Tín dụng & Gửi form
# ---------------------------------------------------------------------------

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


async def fill_credit_and_submit(page, data: Mapping[str, str]) -> str:
    """Hoàn thiện phần cuối của form và nhấn **Yêu Cầu Thẩm Định**.

    Thực hiện 3 việc:

    1. Tải lên tệp PDF tại ô *Tài liệu/Pháp lý **.
    2. Điền *Ngân Hàng* và *Hồ sơ / C.Nhánh* trong phần THÔNG TIN TÍN DỤNG.
    3. Nhấn nút *Yêu Cầu Thẩm Định* và chờ phản hồi server.

    Parameters
    ----------
    page : playwright.async_api.Page
        Trang đã mở sẵn form YCTD (đã gọi ``fill_basic_info`` và
        ``fill_asset_info`` trước đó).
    data : Mapping[str, str]
        Dữ liệu hồ sơ.  Các key được sử dụng:

        ========================  =========================================
        Key                       Trường trên form
        ========================  =========================================
        ``file_path``             Đường dẫn tệp PDF (tuyệt đối hoặc
                                  tương đối so với ``data/uploads/``)
        ``source``                Ngân Hàng  (dropdown)
        ``bank_branch``           Hồ sơ / C.Nhánh
        ``appraisal_fee``         Phí thẩm định
        ``has_vat``               Có xuất hóa đơn (+10% VAT) không
        ``include_survey_fee``    Có bao gồm phí khảo sát không
        ``deposit_amount``        Phí tạm ứng
        ========================  =========================================

    Returns
    -------
    str
        Thông báo kết quả: thành công hoặc mô tả lỗi.

    Raises
    ------
    FileNotFoundError
        Khi ``file_path`` không tồn tại trên hệ thống.
    RuntimeError
        Khi không tìm thấy nút gửi hoặc server trả lỗi.
    """
    # ── 1. Tải lên tệp tại Tài liệu/Pháp lý * ─────────────────────────
    raw_path = str(data.get("file_path") or "").strip()
    file_path = None
    if raw_path:
        file_path = Path(raw_path)
        if not file_path.is_absolute():
            file_path = UPLOAD_DIR / file_path
        
        if not file_path.exists():
            file_path = None
            
    if not file_path:
        file_path = UPLOAD_DIR / "blank_document.pdf"
        if not file_path.exists():
            import fitz
            doc = fitz.open()
            doc.new_page()
            doc.save(str(file_path))
            doc.close()

    # Tìm input[type=file] cho ô Tài liệu/Pháp lý
    if file_path and file_path.exists():
        file_input = page.locator(
            "input[type='file']"
        ).first
        await file_input.set_input_files(str(file_path))
        logger.info("Đã tải lên tệp: %s", file_path.name)

        # Chờ upload hoàn tất
        await page.wait_for_load_state("networkidle")
    else:
        logger.warning("Không có file_path — bỏ qua tải lên tài liệu.")

    # ── 2. THÔNG TIN TÍN DỤNG ───────────────────────────────────────────

    # Ngan hang: map theo Nguon/doi tac trong data.
    await _select_dropdown(page, "Ngân Hàng", _bank_web_value(str(data.get("source") or "")))

    # Hội sở / C.Nhánh: Bỏ qua (Skip)
    
    # Ten tin dung, Phong giao dich: de trong.

    # Số điện thoại tín dụng (Fixed)
    try:
        await page.locator("#input-sdtTinDung").fill("0905226968")
        logger.info("Điền Số điện thoại tín dụng (Fixed): 0905226968")
    except Exception as exc:
        logger.warning("Không thể điền Số điện thoại tín dụng: %s", exc)

    try:
        admin_email = os.getenv("ADMIN_EMAIL", "truongpham.sacc@gmail.com")
        await page.locator("#input-emailTinDung").fill(admin_email)
        logger.info(f"Dien Email tin dung (Env): {admin_email}")
    except Exception as exc:
        logger.warning("Khong the dien Email tin dung: %s", exc)

    # ── 3. THÔNG TIN HỢP ĐỒNG ──────────────────────────────────────────

    # Số hợp đồng (Dynamic)
    contract_number = str(data.get("contract_number") or "").strip()
    if contract_number:
        try:
            input_so_hop_dong = page.locator("#input-soHopDong")
            if await input_so_hop_dong.count() > 0:
                await input_so_hop_dong.fill(contract_number, timeout=5000)
            else:
                input_fallback = page.locator("xpath=//label[contains(text(), 'Số hợp đồng')]/following-sibling::*//input | //label[contains(text(), 'Số hợp đồng')]/..//input[not(@type='hidden')]").first
                if await input_fallback.count() > 0:
                    await input_fallback.fill(contract_number, timeout=5000)
                else:
                    await page.get_by_label("Số hợp đồng").fill(contract_number, timeout=5000)
            logger.info("Điền Số hợp đồng: %s", contract_number)
        except Exception as exc:
            logger.warning("Không tìm thấy ô Số hợp đồng trên form: %s", exc)

    # Phí thẩm định (Fixed)
    fee_filled = False
    try:
        await page.locator("#input-phi").fill("3000000", timeout=5000)
        fee_filled = True
        logger.info("Điền Phí thẩm định (Fixed): 3000000")
    except Exception:
        logger.warning("Không tìm thấy ô Phí thẩm định trên form.")

    # Xuat hoa don/chung tu +10% VAT: tich chon. (ĐÃ BỎ THEO YÊU CẦU)
    # if not await _check_by_label_text(page, "+10% VAT"):
    #     logger.warning("Khong the tich chon '+10%% VAT'.")

    # Co bao gom phi khao sat: tich chon.
    if not await _check_by_label_text(page, "Có bao gồm phí khảo sát"):
        logger.warning("Khong the tich chon 'Co bao gom phi khao sat'.")

    # Phí tạm ứng cần thu (Fixed)
    try:
        await page.locator("#input-phiTamUngCanThu").fill("0", timeout=5000)
        logger.info("Điền Phí tạm ứng (Fixed): 0")
    except Exception:
        logger.warning("Không tìm thấy ô Phí tạm ứng trên form.")
        
    # Chờ 1s để hệ thống web nội bộ kịp tính toán/định dạng dấu phân cách hàng nghìn
    await page.wait_for_timeout(1000)

    # ── 4. Nhấn nút Yêu Cầu Thẩm Định ──────────────────────────────────

    submit_btn = page.locator(
        "button:has-text('Yêu Cầu Thẩm Định'), "
        "button:has-text('YÊU CẦU THẨM ĐỊNH'), "
        "input[type='submit'][value*='Thẩm Định'], "
        "button[type='submit']:has-text('Thẩm Định')"
    ).first

    if await submit_btn.count() == 0:
        raise RuntimeError("Không tìm thấy nút 'Yêu Cầu Thẩm Định' trên trang.")

    logger.info("Đang nhấn nút Yêu Cầu Thẩm Định...")

    # Cuộn nút vào tầm nhìn trước khi click
    await submit_btn.scroll_into_view_if_needed()
    await page.wait_for_timeout(500)

    submit_failures: list[str] = []

    def _capture_submit_failure(request) -> None:
        if WEB_SUBMIT_API_PATH in request.url:
            submit_failures.append(str(request.failure or "không nhận được phản hồi"))

    page.on("requestfailed", _capture_submit_failure)
    try:
        # Lắng nghe đúng phản hồi API submit, kể cả khi API trả về lỗi HTTP.
        try:
            async with page.expect_response(
                _is_submit_response,
                timeout=WEB_SUBMIT_TIMEOUT,
            ) as response_info:
                try:
                    # Thử click bình thường trước
                    await submit_btn.click(timeout=5000)
                except Exception:
                    logger.info("Click thường bị chặn bởi overlay, thử force click...")
                    try:
                        await submit_btn.click(force=True, timeout=5000)
                    except Exception:
                        # Fallback cuối: dùng JavaScript click để bỏ qua mọi overlay
                        logger.info("Force click cũng thất bại, dùng JavaScript click...")
                        await submit_btn.evaluate("el => el.click()")

            response = await response_info.value
        except Exception as exc:
            if submit_failures:
                raise RuntimeError(f"API gửi yêu cầu không nhận được phản hồi: {submit_failures[-1]}") from exc
            raise RuntimeError("Không nhận được phản hồi từ API gửi yêu cầu trong 120 giây.") from exc
    finally:
        page.remove_listener("requestfailed", _capture_submit_failure)

    logger.info(
        "Server phản hồi: %s %s",
        response.status,
        response.url,
    )

    if response.status >= 400:
        try:
            error_text = (await response.text()).strip()
        except Exception:
            error_text = ""
        detail = f": {error_text[:500]}" if error_text else ""
        raise RuntimeError(f"API gửi yêu cầu trả lỗi HTTP {response.status}{detail}")

    # Chờ trang xử lý xong
    await page.wait_for_load_state("networkidle")

    # Kiểm tra có thông báo lỗi trên giao diện không
    error_banner = page.locator(
        ".alert-danger, "
        ".error-message, "
        ".toast-error, "
        "[class*='error']:visible"
    ).first
    if await error_banner.count() > 0:
        error_text = (await error_banner.text_content() or "").strip()
        logger.error("Server trả về lỗi: %s", error_text)
        raise RuntimeError(f"Gửi yêu cầu thất bại: {error_text}")

    # Kiểm tra thông báo thành công
    success_banner = page.locator(
        ".alert-success, "
        ".success-message, "
        ".toast-success, "
        "[class*='success']:visible"
    ).first
    if await success_banner.count() > 0:
        success_text = (await success_banner.text_content() or "").strip()
        logger.info("Thông báo thành công: %s", success_text)
        return f"Gửi yêu cầu thành công: {success_text}"

    record_id = data.get("id", "?")
    result = f"Đã gửi yêu cầu thẩm định cho hồ sơ #{record_id} (HTTP {response.status})."
    logger.info(result)
    return result


async def find_created_web_case_id(page, data: Mapping[str, str]) -> str:
    async def _click_status_tab() -> None:
        candidates = [
            page.get_by_role("link", name=re.compile(r"Trạng thái", re.IGNORECASE)),
            page.get_by_role("button", name=re.compile(r"Trạng thái", re.IGNORECASE)),
            page.get_by_text("Trạng thái", exact=True),
        ]
        for locator in candidates:
            try:
                if await locator.count() > 0:
                    await locator.first.click(timeout=5000)
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(800)
                    return
            except Exception:
                continue
        raise RuntimeError("Không tìm thấy tab Trạng thái sau khi gửi yêu cầu định giá.")

    await _click_status_tab()

    attempts = WEB_STATUS_TABLE_TIMEOUT // WEB_STATUS_TABLE_POLL_INTERVAL
    for _attempt in range(attempts):
        web_id = await page.evaluate(
            """() => {
                const isVisible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const box = el.getBoundingClientRect();
                    return box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                };
                const rowSelectors = [
                    'table tbody tr',
                    '.table tbody tr',
                    '.p-datatable-tbody tr',
                    '.ant-table-tbody tr',
                    '[role="row"]'
                ];
                const rows = [];
                for (const selector of rowSelectors) {
                    for (const row of Array.from(document.querySelectorAll(selector))) {
                        if (!rows.includes(row) && isVisible(row)) rows.push(row);
                    }
                }
                for (const row of rows) {
                    const cells = Array.from(row.querySelectorAll('td, th, [role="cell"], [role="gridcell"]'))
                        .filter(isVisible)
                        .map(cell => (cell.innerText || cell.textContent || '').trim())
                        .filter(Boolean);
                    if (!cells.length) continue;
                    const firstCellMatch = cells[0].match(/\\b\\d{3,}\\b/);
                    if (firstCellMatch) return firstCellMatch[0];
                    const rowMatch = (row.innerText || row.textContent || '').trim().match(/^\\s*(\\d{3,})\\b/);
                    if (rowMatch) return rowMatch[1];
                }
                return '';
            }"""
        )
        web_id = str(web_id or "").strip()
        if web_id:
            return web_id
        await page.wait_for_timeout(WEB_STATUS_TABLE_POLL_INTERVAL)
    raise RuntimeError("Đã gửi yêu cầu nhưng không đọc được ID hồ sơ ở dòng đầu tiên trên tab Trạng thái sau 120 giây.")


def _cases_db_path() -> Path:
    configured = os.getenv("SQLITE_DATABASE", "").strip()
    return Path(configured) if configured else PROJECT_ROOT / "data" / "cases.db"


def _web_case_asset_label(index: int, record: Mapping[str, str], web_case_id: str) -> str:
    asset_text = str(record.get("dia_chi") or record.get("asset_description") or "").strip().replace("\n", ", ")
    if len(asset_text) > 80:
        asset_text = asset_text[:77].rstrip() + "..."
    suffix = f" - {asset_text}" if asset_text else ""
    return f"TS{index + 1}: {web_case_id}{suffix}"


async def save_web_case_id_to_case(record: Mapping[str, str], web_case_ids: list[str]) -> None:
    unique_ids = []
    seen = set()
    for value in web_case_ids:
        web_id = str(value or "").strip()
        if web_id and web_id not in seen:
            seen.add(web_id)
            unique_ids.append(web_id)
    if not unique_ids:
        return
    if "case_status" not in record and "payment_status" not in record and "case_folder" not in record:
        return
    raw_case_id = str(record.get("id") or "").strip()
    if not raw_case_id.isdigit():
        return
    db_path = _cases_db_path()
    logger.info("Lưu ID Web cho hồ sơ #%s vào %s: %s", raw_case_id, db_path, unique_ids)
    await asyncio.to_thread(update_case, db_path, int(raw_case_id), {"web_case_id": "\n".join(unique_ids)})


from pydantic import BaseModel, Field
from typing import List, Optional

class WebErrorDiagnosis(BaseModel):
    status: str = Field(description="Phân loại lỗi: SERVER_ERROR, POPUP_BLOCKED, LOADING_HANG, VALIDATION_ERROR, UNKNOWN")
    description: str = Field(description="Mô tả chi tiết nguyên nhân lỗi bằng tiếng Việt")
    missing_fields: List[str] = Field(description="Danh sách các trường bắt buộc bị phát hiện chưa điền/chọn trên giao diện web (nếu có)")
    recovery_action: str = Field(description="Đề xuất hành động khắc phục: REFRESH, CLOSE_MODAL, RE_LOGIN, NONE")
    recovery_selector: Optional[str] = Field(description="CSS selector của nút bấm cần click nếu hành động là CLOSE_MODAL")

async def analyze_web_error_with_gemini(
    screenshot_path: Path,
    html_path: Path,
    error_message: str
) -> WebErrorDiagnosis | None:
    try:
        from google import genai
        from google.genai import types
        
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.warning("Không tìm thấy GEMINI_API_KEY. Bỏ qua phân tích AI.")
            return None
            
        client = genai.Client(api_key=api_key)
        
        # Read screenshot bytes
        if not screenshot_path.exists():
            logger.warning("Không tìm thấy ảnh chụp lỗi: %s", screenshot_path)
            return None
            
        image_part = types.Part.from_bytes(
            data=screenshot_path.read_bytes(),
            mime_type="image/png"
        )
        
        # Read first 10000 characters of HTML to avoid token overflow
        html_text = ""
        if html_path.exists():
            html_text = html_path.read_text(encoding="utf-8")[:10000]
            
        prompt = f"""
        Bạn là một chuyên gia giám sát tự động hóa trình duyệt. Hãy phân tích ảnh chụp màn hình lỗi và một phần mã nguồn HTML dưới đây để chẩn đoán sự cố khi tự động điền form "Gửi Yêu Cầu Thẩm Định" trên web Cenvalue.
        
        Lỗi hệ thống ghi nhận: {error_message}
        
        Một phần HTML trang web:
        {html_text}
        
        Danh sách các trường bắt buộc phải nhập trên form Cenvalue:
        1. Họ tên (Họ tên khách hàng)
        2. Số điện thoại
        3. Email
        4. Địa chỉ
        5. Kiểu thẩm định (Thẩm định giá / Định giá sơ bộ)
        6. Chi nhánh thẩm định
        7. Chọn Văn Phòng
        8. Tỉnh/ thành phố
        9. Tài sản thẩm định
        10. Mục đích thẩm định
        11. Loại tài sản
        12. Nhóm tài sản
        13. Nguồn/đối tác
        14. Tài liệu/Pháp lý (File upload)
        15. Ngân Hàng
        16. Số hợp đồng
        17. Phí thẩm định
        18. Phí tạm ứng cần thu
        
        Hãy xác định xem có bất kỳ trường bắt buộc nào ở trên bị thiếu/không được điền hoặc chọn hay không.
        Hãy trả về chẩn đoán lỗi chi tiết theo cấu trúc JSON định nghĩa sẵn.
        """
        
        # Run models.generate_content in to_thread because the SDK might block
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WebErrorDiagnosis,
                temperature=0.1
            )
        )
        
        # Parse output JSON into WebErrorDiagnosis
        import json
        data = json.loads(response.text)
        return WebErrorDiagnosis(**data)
        
    except Exception as exc:
        logger.error("Lỗi khi phân tích lỗi bằng Gemini: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Playwright helpers (kept from original implementation)
# ---------------------------------------------------------------------------

def _required_selector(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thieu cau hinh selector Playwright: {name}")
    return value


async def notify_telegram(text: str) -> None:
    """Gửi thông báo qua Telegram."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        logger.warning("Không có TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID. Bỏ qua thông báo.")
        return

    try:
        from telegram import Bot
        bot = Bot(bot_token)
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as exc:
        logger.error("Gửi tin nhắn Telegram thất bại: %s", exc)


async def _capture_web_entry_error_artifacts(page, error_dir: Path, *, record_id: object, timestamp: int, asset_index: int | None = None) -> list[Path]:
    suffix = f"_asset_{asset_index}" if asset_index is not None else ""
    base_name = f"error_web_entry_{record_id}{suffix}_{timestamp}"
    captured: list[Path] = []

    async def _screenshot(name: str, *, full_page: bool = True) -> None:
        path = error_dir / f"{base_name}_{name}.png"
        await page.screenshot(path=str(path), full_page=full_page)
        captured.append(path)

    # Keep the exact failing state before changing any scroll position.
    await _screenshot("current")

    try:
        await page.evaluate(
            """() => {
                const isScrollable = (el) => el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
                for (const el of Array.from(document.querySelectorAll("*"))) {
                    if (isScrollable(el)) {
                        el.scrollTop = 0;
                        el.scrollLeft = 0;
                    }
                }
                window.scrollTo(0, 0);
            }"""
        )
        await page.wait_for_timeout(300)
        await _screenshot("form_top")
    except Exception as exc:
        logger.warning("Khong the chup anh phan dau form loi: %s", exc)

    try:
        await page.evaluate(
            """() => {
                const isScrollable = (el) => el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
                for (const el of Array.from(document.querySelectorAll("*"))) {
                    if (isScrollable(el)) {
                        el.scrollTop = el.scrollHeight;
                        el.scrollLeft = 0;
                    }
                }
                window.scrollTo(0, document.body.scrollHeight);
            }"""
        )
        await page.wait_for_timeout(300)
        await _screenshot("form_bottom")
    except Exception as exc:
        logger.warning("Khong the chup anh phan cuoi form loi: %s", exc)

    try:
        html_path = error_dir / f"{base_name}.html"
        html_path.write_text(await page.content(), encoding="utf-8")
        captured.append(html_path)
    except Exception as exc:
        logger.warning("Khong the luu HTML trang loi: %s", exc)

    return captured


async def run_company_web_entry(record: Mapping[str, str], *, web_url: str) -> str:
    """Thực hiện toàn bộ quy trình nhập Web Công ty.

    Sử dụng Playwright để mở trình duyệt, đăng nhập, điền toàn bộ các phần
    thông tin và gửi yêu cầu. Cập nhật trạng thái nếu thành công, chụp ảnh
    màn hình nếu lỗi.
    """
    settings = load_web_automation_settings()
    # Ưu tiên url truyền vào, nếu không có thì dùng trong settings
    target_url = web_url.strip() if web_url and web_url.strip() else settings.internal_web_url
    
    if not target_url:
        raise RuntimeError("Thiếu URL trang web nội bộ.")

    missing_fields = missing_web_entry_fields(record)
    if missing_fields:
        missing_labels = ", ".join(item["label"] for item in missing_fields)
        raise RuntimeError(f"Thiếu thông tin bắt buộc để nhập Web: {missing_labels}")

    record_id = record.get("id", "?")
    logger.info("Bắt đầu nhập liệu tự động cho hồ sơ #%s", record_id)

    # KIỂM TRA DỮ LIỆU ĐẦU VÀO (Nhóm 4 - Dynamic Data)
    missing = []
    if not (record.get("customer_info") or record.get("customer_name")): missing.append("Họ tên (customer_info)")
    if not record.get("customer_address"): missing.append("Địa chỉ (customer_address)")
    if not (record.get("asset_description") or record.get("city")): missing.append("Tỉnh/ thành phố (asset_description)")
    # File path validation removed since we upload a blank PDF if it's missing
    if not record.get("valuation_purpose"): missing.append("Mục đích thẩm định (valuation_purpose)")
    
    if missing:
        err_msg = f"❌ Lỗi: Hồ sơ #{record_id} thiếu dữ liệu bắt buộc để nhập Web Công ty:\n- " + "\n- ".join(missing)
        await notify_telegram(err_msg)
        raise ValueError(err_msg)

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Chưa cài Playwright. Chạy: pip install playwright && playwright install chromium") from exc

    # Xử lý cắt chuỗi (split) để tính số lượng tài sản N
    raw_asset_descriptions = [p.strip() for p in str(record.get("asset_description") or "").split("\n") if p.strip()]
    raw_dia_chis = [p.strip() for p in str(record.get("dia_chi") or "").split("\n") if p.strip()]
    N = max(len(raw_asset_descriptions), len(raw_dia_chis), 1)

    logger.info("Phát hiện %d tài sản trong hồ sơ #%s", N, record_id)

    def get_split_value(raw_val: str, index: int) -> str:
        parts = [p.strip() for p in (raw_val or "").split("\n") if p.strip()]
        if not parts:
            return ""
        if index < len(parts):
            return parts[index]
        return parts[-1]
    browser = None
    page = None
    try:
        async with async_playwright() as playwright:
            # Tự động chọn headless=True trên Linux/VPS, hoặc cho phép tuỳ cấu hình qua env PLAYWRIGHT_HEADLESS
            is_headless = os.getenv("PLAYWRIGHT_HEADLESS", "true" if os.name != "nt" else "false").strip().casefold() in ("true", "1", "yes")
            browser = await playwright.chromium.launch(headless=is_headless)
            context = await browser.new_context()
            
            results_msg = []
            web_case_ids: list[str] = []

            for i in range(N):
                logger.info("Đang xử lý tài sản %d/%d của hồ sơ #%s", i + 1, N, record_id)
                sub_record = dict(record)
                
                # Thông tin tài sản lấy theo index `i`
                sub_record["asset_description"] = get_split_value(str(record.get("asset_description") or ""), i)
                sub_record["dia_chi"] = get_split_value(str(record.get("dia_chi") or ""), i)
                sub_record["so_thua"] = get_split_value(str(record.get("so_thua") or ""), i)
                sub_record["so_to"] = get_split_value(str(record.get("so_to") or ""), i)

                # Thông tin chung giữ nguyên nhưng cần gộp thành 1 dòng (tránh lỗi web)
                for common_field in ["customer_info", "customer_address", "citizen_id", "chu_so_huu"]:
                    if sub_record.get(common_field):
                        sub_record[common_field] = sub_record[common_field].replace("\n", ", ")

                retries = 0
                max_retries = 1
                while retries <= max_retries:
                    try:
                        # Log chi tiết các giá trị điền form trước khi chạy để kiểm tra
                        log_dir = PROJECT_ROOT / "logs"
                        log_dir.mkdir(parents=True, exist_ok=True)
                        import datetime
                        run_log_path = log_dir / "web_entry_runs.log"
                        with open(run_log_path, "a", encoding="utf-8") as f_log:
                            f_log.write(
                                f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                f"Hồ sơ #{record_id} (Tài sản {i + 1}/{N}):\n"
                                f"  - Loại tài sản (SQLite): '{sub_record.get('asset_type')}' => Web sẽ điền: Loại='{_asset_web_values(str(sub_record.get('asset_type')))[0]}', Nhóm='{_asset_web_values(str(sub_record.get('asset_type')))[1]}'\n"
                                f"  - Mục đích thẩm định (SQLite): '{sub_record.get('valuation_purpose')}' => Web sẽ điền: '{_purpose_web_value(str(sub_record.get('valuation_purpose')))}'\n"
                                f"  - Chi nhánh: '{sub_record.get('valuation_branch') or sub_record.get('branch')}' | Văn phòng: '{sub_record.get('office')}'\n"
                                f"  - Khách hàng: '{sub_record.get('customer_info')}' | Địa chỉ: '{sub_record.get('customer_address')}'\n"
                                f"  - Tài sản chi tiết: '{sub_record.get('asset_description')}'\n"
                                f"--------------------------------------------------------------------------------\n"
                            )
                        # --- 1. Mở trang và Đăng nhập ---
                        if retries > 0:
                            logger.info("Thử lại lần %d cho tài sản %d/%d của hồ sơ #%s", retries, i + 1, N, record_id)
                            if page:
                                try:
                                    await page.close()
                                except Exception:
                                    pass
                        
                        page = await context.new_page()
                        page = await start_browser_and_login(context, page=page)
                        
                        # --- 2. Điền thông tin ---
                        await fill_basic_info(page, sub_record)
                        await fill_asset_info(page, sub_record)
                        
                        # --- 3. Tài liệu, Tín dụng & Gửi ---
                        res = await fill_credit_and_submit(page, sub_record)
                        web_case_id = await find_created_web_case_id(page, sub_record)
                        web_case_label = _web_case_asset_label(i, sub_record, web_case_id)
                        web_case_ids.append(web_case_label)
                        results_msg.append(f"- Tài sản {i + 1}: {res} | ID Web: {web_case_label}")
                        break  # Thành công -> thoát khỏi vòng lặp retry
                        
                    except Exception as exc:
                        import traceback
                        tb_str = traceback.format_exc()
                        err_msg = f"❌ Lỗi khi nhập Web C.Ty cho hồ sơ #{record_id} (Tài sản {i + 1}/{N}): {type(exc).__name__}: {exc}\nChi tiết:\n{tb_str}"
                        logger.error(err_msg)
                        
                        error_artifacts = []
                        if page:
                            try:
                                error_dir = PROJECT_ROOT / "logs" / "errors"
                                error_dir.mkdir(parents=True, exist_ok=True)
                                import time
                                timestamp = int(time.time())
                                error_artifacts = await _capture_web_entry_error_artifacts(
                                    page,
                                    error_dir,
                                    record_id=record_id,
                                    asset_index=i + 1,
                                    timestamp=timestamp,
                                )
                                logger.info("Đã lưu artifact lỗi tại: %s", ", ".join(str(path) for path in error_artifacts))
                                err_msg += "\nArtifact lỗi: " + ", ".join(path.name for path in error_artifacts)
                            except Exception as ss_exc:
                                logger.error("Không thể chụp ảnh màn hình: %s", ss_exc)
                        
                        # Tìm ảnh current chụp trạng thái lỗi hiện tại và file HTML
                        screenshot_file = None
                        html_file = None
                        for art in error_artifacts:
                            if art.name.endswith("current.png"):
                                screenshot_file = art
                            elif art.name.endswith(".html"):
                                html_file = art
                                
                        diagnosis = None
                        if screenshot_file and html_file:
                            logger.info("Đang gọi AI phân tích lỗi...")
                            diagnosis = await analyze_web_error_with_gemini(screenshot_file, html_file, str(exc))
                            
                        if diagnosis:
                            logger.info("AI chẩn đoán lỗi: %s (Hành động: %s)", diagnosis.description, diagnosis.recovery_action)
                            err_msg += f"\n\n🤖 **Chẩn đoán bởi AI:**\n- Trạng thái: {diagnosis.status}\n- Chi tiết: {diagnosis.description}"
                            if diagnosis.missing_fields:
                                err_msg += f"\n- ⚠️ **Thiếu trường bắt buộc:** {', '.join(diagnosis.missing_fields)}"
                                # Nếu thiếu trường bắt buộc, không cần thử lại
                                await notify_telegram(err_msg)
                                raise RuntimeError(err_msg) from exc
                                
                            # Xử lý tự phục hồi
                            if diagnosis.recovery_action in ("REFRESH", "CLOSE_MODAL") and retries < max_retries:
                                retries += 1
                                logger.info("Tiến hành tự phục hồi qua đề xuất AI: %s", diagnosis.recovery_action)
                                if diagnosis.recovery_action == "CLOSE_MODAL" and diagnosis.recovery_selector and page:
                                    try:
                                        logger.info("Đóng popup bằng selector: %s", diagnosis.recovery_selector)
                                        await page.locator(diagnosis.recovery_selector).first.click(timeout=3000)
                                        # Không close page, tăng retries và chạy tiếp mà không load lại toàn trang
                                        continue
                                    except Exception as close_exc:
                                        logger.warning("Không thể click đóng popup bằng selector gợi ý: %s", close_exc)
                                continue
                                
                        # Nếu không thể khôi phục hoặc đã hết lượt thử lại
                        await notify_telegram(err_msg)
                        raise RuntimeError(err_msg) from exc
                    finally:
                        if page:
                            try:
                                await page.close()
                                page = None
                            except Exception:
                                pass

            # --- 4. Cập nhật DB & Báo cáo thành công (Chỉ khi tất cả đều thành công) ---
            from .database_manager import update_record_status
            try:
                # Chỉ cập nhật DB nếu record_id là số nguyên hợp lệ (hồ sơ từ Telegram/Email)
                valid_id = int(str(record_id))
                await update_record_status(settings.records_db_path, valid_id, "COMPLETED_ON_WEB")
            except (ValueError, TypeError):
                logger.info("Bỏ qua cập nhật trạng thái records.db vì record_id không hợp lệ: %s", record_id)
            await save_web_case_id_to_case(record, web_case_ids)
            
            success_text = f"✅ Đã nhập Web C.Ty thành công hồ sơ #{record_id} ({N} tài sản).\n" + "\n".join(results_msg)
            await notify_telegram(success_text)
            
            return success_text

    except Exception as exc:
        import traceback
        tb_str = traceback.format_exc()
        err_msg = f"❌ Lỗi khi nhập Web C.Ty cho hồ sơ #{record_id}: {type(exc).__name__}: {exc}\nChi tiết:\n{tb_str}"
        logger.error(err_msg)
        
        # Chụp ảnh màn hình nếu page đang mở
        if page:
            try:
                error_dir = PROJECT_ROOT / "logs" / "errors"
                error_dir.mkdir(parents=True, exist_ok=True)
                import time
                timestamp = int(time.time())
                error_artifacts = await _capture_web_entry_error_artifacts(
                    page,
                    error_dir,
                    record_id=record_id,
                    timestamp=timestamp,
                )
                logger.info("Đã lưu artifact lỗi tại: %s", ", ".join(str(path) for path in error_artifacts))
                err_msg += "\nArtifact lỗi: " + ", ".join(path.name for path in error_artifacts)
            except Exception as ss_exc:
                logger.error("Không thể chụp ảnh màn hình: %s", ss_exc)
                
        await notify_telegram(err_msg)
        raise RuntimeError(err_msg) from exc
        
    finally:
        if browser:
            await browser.close()
