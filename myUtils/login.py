import asyncio
import sqlite3

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH


# UPSERT：如果存在同 type + userName 的记录则 UPDATE，否则 INSERT
def _upsert_account(conn, type_val, file_path, user_name):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM user_info WHERE type = ? AND userName = ?
    ''', (type_val, user_name))
    existing = cursor.fetchone()
    if existing:
        cursor.execute('''
            UPDATE user_info SET filePath = ?, status = 1 WHERE id = ?
        ''', (file_path, existing[0]))
        print(f"✅ 已更新账号 {user_name}（类型 {type_val}）的 cookie")
    else:
        cursor.execute('''
            INSERT INTO user_info (type, filePath, userName, status) VALUES (?, ?, ?, ?)
        ''', (type_val, file_path, user_name, 1))
        print(f"✅ 已添加新账号 {user_name}（类型 {type_val}）")
    conn.commit()

# 统一获取浏览器启动配置（防风控+引入本地浏览器）
def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
        'args': [
            '--disable-blink-features=AutomationControlled',  # 核心防爬屏蔽：去掉 window.navigator.webdriver 标签
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized'
        ]
    }
    # 如果用户在 conf.py 里配置了本地 Chrome，就用本地的，这样成功率极高
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH

    return options


def get_login_browser_options(force_headed: bool = False):
    options = get_browser_options()
    if force_headed:
        options['headless'] = False
    if not LOCAL_CHROME_PATH:
        options['channel'] = 'chrome'
    return options


async def _is_tencent_login_completed(page):
    publish_markers = [
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    ]
    for marker in publish_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue

    if not (
        page.url.startswith("https://channels.weixin.qq.com/platform/post/create")
        or page.url.startswith("https://channels.weixin.qq.com/platform/post/list")
    ):
        return False

    login_markers = [
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    ]
    for marker in login_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _probe_tencent_login_in_context(context):
    probe_page = await context.new_page()
    try:
        print("🔎 开始主动探测视频号登录态")
        await probe_page.goto("https://channels.weixin.qq.com/platform/post/create", timeout=10000)
        await probe_page.wait_for_load_state("domcontentloaded", timeout=10000)
        await asyncio.sleep(1)
        probe_success = await asyncio.wait_for(_is_tencent_login_completed(probe_page), timeout=5)
        print(f"🔎 主动探测结果: success={probe_success}, url={probe_page.url}")
        return probe_success, probe_page.url
    except Exception as exc:
        print(f"⚠️ 主动探测视频号登录态异常: {exc}")
        return False, ""
    finally:
        await probe_page.close()

# 抖音登录
async def douyin_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            _upsert_account(conn, 3, f"{uuid_v1}.json", id)
        status_queue.put("200")


# 视频号登录
async def get_tencent_cookie(id, status_queue, is_scan_confirmed=None):
    async with async_playwright() as playwright:
        options = get_login_browser_options(force_headed=True)
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url
        print(f"📋 视频号页面URL: {original_url}")

        # 等待 iframe 出现并获取二维码
        iframe_locator = page.frame_locator("iframe").first
        img_locator = iframe_locator.get_by_role("img").first
        src = await img_locator.get_attribute("src")
        print("✅ 二维码图片地址:", src)
        status_queue.put(src)

        # ========== 轮询检测登录完成 ==========
        # 手动确认只表示“用户说自己完成了扫码确认”，
        # 真正保存 cookie 之前，仍然必须检测页面已经离开登录态。
        login_detected = False
        scan_confirmed_logged = False
        print(f"⏳ 等待扫码登录...（URL 变化自动检测，或点「我已扫码登录」按钮）")
        for i in range(200):  # 最多等 200 秒
            try:
                if await _is_tencent_login_completed(page):
                    print(f"✅ 视频号已进入登录后页面: {page.url}")
                    login_detected = True
                    break
            except Exception:
                pass

            # 检测: URL 是否发生变化
            try:
                if page.url != original_url:
                    print(f"📍 页面URL 已变化: {original_url} → {page.url}")
            except:
                pass

            # 记录: 用户手动点击了"我已扫码登录"按钮，但还要继续等待页面真正登录完成
            try:
                if not scan_confirmed_logged and callable(is_scan_confirmed) and is_scan_confirmed():
                    print("✅ 用户手动确认已扫码登录，继续等待页面完成跳转")
                    scan_confirmed_logged = True
                    probe_success, probe_url = await _probe_tencent_login_in_context(context)
                    if probe_success:
                        print(f"✅ 手动确认后立即探测到视频号登录态已生效: {probe_url}")
                        login_detected = True
                        break
            except Exception:
                pass

            # 某些情况下手机确认后 cookie 已经生效，但当前二维码页不会自动跳转。
            # 这时主动在同一上下文里探测一次登录后页面。
            if scan_confirmed_logged:
                try:
                    probe_success, probe_url = await _probe_tencent_login_in_context(context)
                    if probe_success:
                        print(f"✅ 主动探测到视频号登录态已生效: {probe_url}")
                        login_detected = True
                        break
                except Exception as exc:
                    print(f"⚠️ 主动探测视频号登录态失败，继续等待: {exc}")

            await asyncio.sleep(1)

        if not login_detected:
            status_queue.put("500")
            print(f"❌ 视频号登录超时：200秒内未检测到登录成功")
            print(f"   当前URL: {page.url}")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 统一切到登录后目标页，确保上下文状态稳定后再保存 cookie
        try:
            await page.goto("https://channels.weixin.qq.com/platform/post/create")
            await page.wait_for_load_state('networkidle')
        except Exception:
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(1)
        print("✅ 页面加载完成，准备保存 cookie")

        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(2, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            _upsert_account(conn, 2, f"{uuid_v1}.json", id)
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击"立即登录"按钮（类型为 link）
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            _upsert_account(conn, 4, f"{uuid_v1}.json", id)
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator('img.css-wemwzq').click()

        img_locator = page.get_by_role("img").nth(2)
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            _upsert_account(conn, 1, f"{uuid_v1}.json", id)
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)
