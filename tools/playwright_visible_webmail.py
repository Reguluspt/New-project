import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


def read_env(path):
    data = {}
    for line in Path(path).read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip().strip('"')
    return data


async def fill_first(page, selectors, value):
    for selector in selectors:
        loc = page.locator(selector).first
        try:
            if await loc.count() > 0:
                await loc.fill(value, timeout=5000)
                return selector
        except Exception:
            pass
    return None


async def click_first(page, selectors):
    for selector in selectors:
        loc = page.locator(selector).first
        try:
            if await loc.count() > 0:
                await loc.click(timeout=5000)
                return selector
        except Exception:
            pass
    return None


async def main():
    env = read_env('API.env')
    url = env.get('WEBMAIL_URL') or 'https://owa.cengroup.vn/'
    username = env.get('MAIL_USERNAME') or ''
    password = env.get('MAIL_PASSWORD') or ''
    profile = str((Path('.playwright-visible-webmail-profile')).resolve())

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            profile,
            headless=False,
            viewport={'width': 1366, 'height': 820},
            slow_mo=400,
            args=['--start-maximized', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        print('OPEN', url, flush=True)
        try:
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        except PlaywrightTimeoutError:
            print('WARN navigation timeout, continuing', flush=True)
        await page.wait_for_timeout(3000)
        print('TITLE', await page.title(), flush=True)
        print('URL', page.url, flush=True)

        user_selector = await fill_first(page, [
            'input#username',
            'input[name="username"]',
            'input[type="email"]',
            'input[name="loginfmt"]',
            'input[type="text"]',
        ], username)
        if user_selector:
            print('FILLED_USERNAME', user_selector, flush=True)
            await page.wait_for_timeout(800)

        pass_selector = await fill_first(page, [
            'input#password',
            'input[name="password"]',
            'input[type="password"]',
        ], password)
        if pass_selector:
            print('FILLED_PASSWORD', pass_selector, flush=True)
            await page.wait_for_timeout(800)

        if user_selector or pass_selector:
            clicked = await click_first(page, [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Sign in")',
                'button:has-text("Đăng nhập")',
                'div[role="button"]:has-text("Sign in")',
            ])
            print('CLICKED_LOGIN', clicked, flush=True)
            await page.wait_for_timeout(10000)

        print('AFTER_TITLE', await page.title(), flush=True)
        print('AFTER_URL', page.url, flush=True)
        print('PASSWORD_FIELDS', await page.locator('input[type="password"]').count(), flush=True)
        print('SEARCH_BOXES', await page.locator('input[aria-label*="Search"], input[aria-label*="Tìm"], [role="searchbox"]').count(), flush=True)
        print('HOLDING_OPEN_SECONDS 600', flush=True)
        await page.wait_for_timeout(600000)
        await context.close()

asyncio.run(main())
