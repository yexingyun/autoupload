import asyncio
import configparser
import os

from playwright.async_api import async_playwright
from xhs import XhsClient

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger, douyin_logger
from pathlib import Path
from uploader.baijiahao_uploader.main import cookie_auth as baijiahao_cookie_auth
from uploader.bilibili_uploader.runtime import run_biliup_command
from uploader.tk_uploader.main_chrome import cookie_auth as tiktok_cookie_auth
from uploader.xhs_uploader.main import sign_local


async def cookie_auth_douyin(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
            # 2024.06.17 抖音创作者中心改版
            # 判断
            # 等待“扫码登录”元素出现，超时 5 秒（如果 5 秒没出现，说明 cookie 有效）
            try:
                await page.get_by_text("扫码登录").wait_for(timeout=5000)
                douyin_logger.error("[+] cookie 失效，需要扫码登录")
                return False
            except:
                douyin_logger.success("[+]  cookie 有效")
                return True
        except:
            douyin_logger.error("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False


async def cookie_auth_tencent(account_file):
    async with async_playwright() as playwright:
        launch_kwargs = {
            "headless": LOCAL_CHROME_HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--lang=zh-CN",
                "--disable-infobars",
                "--start-maximized",
            ],
        }
        if LOCAL_CHROME_PATH:
            launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
        else:
            launch_kwargs["channel"] = "chrome"

        browser = await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create", timeout=5000)
        except Exception as exc:
            tencent_logger.error(f"[+] 视频号 cookie 校验跳转异常，按失效处理: {exc}")
            await context.close()
            await browser.close()
            return False

        login_markers = [
            page.get_by_text("扫码登录", exact=True).first,
            page.locator("div.login-qrcode-wrap").first,
            page.locator("div.qrcode-wrap").first,
            page.locator("img.qrcode").first,
            page.locator('span:has-text("微信扫码登录 视频号助手")').first,
        ]
        for marker in login_markers:
            try:
                if await marker.count() and await marker.is_visible():
                    tencent_logger.error("[+] 视频号仍停留在扫码登录页，cookie 失效")
                    await context.close()
                    await browser.close()
                    return False
            except Exception:
                continue

        success_markers = [
            page.locator('div:has-text("发表视频")').first,
            page.locator('button:has-text("发表")').first,
            page.locator('button:has-text("保存草稿")').first,
        ]
        for marker in success_markers:
            try:
                if await marker.count() and await marker.is_visible():
                    tencent_logger.success("[+] cookie 有效")
                    await context.close()
                    await browser.close()
                    return True
            except Exception:
                continue

        tencent_logger.success("[+] cookie 有效")
        await context.close()
        await browser.close()
        return True


async def cookie_auth_ks(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒

            kuaishou_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            kuaishou_logger.success("[+] cookie 有效")
            return True


async def cookie_auth_xhs(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def check_cookie(type, file_path):
    match type:
        # 小红书
        case 1:
            return await cookie_auth_xhs(Path(BASE_DIR / "cookiesFile" / file_path))
        # 视频号
        case 2:
            return await cookie_auth_tencent(Path(BASE_DIR / "cookiesFile" / file_path))
        # 抖音
        case 3:
            return await cookie_auth_douyin(Path(BASE_DIR / "cookiesFile" / file_path))
        # 快手
        case 4:
            return await cookie_auth_ks(Path(BASE_DIR / "cookiesFile" / file_path))
        # 百家号
        case 5:
            return await baijiahao_cookie_auth(Path(BASE_DIR / "cookiesFile" / file_path))
        # TikTok
        case 6:
            return await tiktok_cookie_auth(Path(BASE_DIR / "cookiesFile" / file_path))
        # Bilibili
        case 7:
            full_path = Path(BASE_DIR / "cookiesFile" / file_path)
            if not full_path.exists():
                return False
            result = run_biliup_command(["-u", str(full_path), "renew"])
            return result.returncode == 0
        case _:
            return False

# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)
