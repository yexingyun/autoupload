import asyncio
import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from uploader.bilibili_uploader.runtime import run_biliup_command
from uploader.douyin_uploader.main import DouYinVideo, DouYinNote
from uploader.ks_uploader.main import KSVideo, KSNote
from uploader.tk_uploader.main_chrome import TiktokVideo
from uploader.tencent_uploader.main import TencentVideo, TencentNote
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo, XiaoHongShuNote
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day


def _resolve_account_files(account_file):
    return [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]


def _resolve_video_files(files):
    return [str(Path(BASE_DIR / "videoFile" / file)) for file in files]


def _resolve_image_files(files):
    return [str(Path(BASE_DIR / "videoFile" / file)) for file in files]


# ==================== 视频发布函数 ====================

def post_video_tencent(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                       enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, is_draft=False):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]
    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{desc}")
            print(f"Hashtag：{tags}")
            app = TencentVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
                category=category,
                desc=desc or None,
                is_draft=is_draft,
            )
            asyncio.run(app.main(), debug=False)


def post_video_DouYin(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                      enableTimer=False, videos_per_day=1, daily_times=None, start_days=0,
                      thumbnail_path='', productLink='', productTitle=''):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]
    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{desc}")
            print(f"Hashtag：{tags}")
            app = DouYinVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
                desc=desc or None,
                thumbnail_portrait_path=thumbnail_path or None,
                productLink=productLink,
                productTitle=productTitle,
            )
            asyncio.run(app.douyin_upload_video(), debug=False)


def post_video_ks(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                  enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]
    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{desc}")
            print(f"Hashtag：{tags}")
            app = KSVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
                desc=desc or None,
            )
            asyncio.run(app.main(), debug=False)


def post_video_xhs(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                   enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    file_num = len(video_files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{desc}")
            print(f"Hashtag：{tags}")
            app = XiaoHongShuVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes,
                account_file=str(cookie),
                desc=desc or None,
            )
            asyncio.run(app.main(), debug=False)


def post_video_baijiahao(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                         enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]

    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = BaiJiaHaoVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
            )
            asyncio.run(app.main(), debug=False)


def post_video_tiktok(title, files, tags, account_file, desc='', category=TencentZoneTypes.LIFESTYLE.value,
                      enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, thumbnail_path=''):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]

    for index, file in enumerate(video_files):
        for cookie in account_files:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = TiktokVideo(
                title=title,
                file_path=file,
                tags=tags,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
                thumbnail_path=thumbnail_path or None,
            )
            asyncio.run(app.main(), debug=False)


def post_video_bilibili(title, files, tags, account_file, desc='', category=None,
                        enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_files = _resolve_account_files(account_file)
    video_files = _resolve_video_files(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(video_files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for _ in range(len(video_files))]

    default_tid = 174
    for index, file in enumerate(video_files):
        schedule_text = ''
        if publish_datetimes[index]:
            schedule_text = publish_datetimes[index].strftime("%Y-%m-%d %H:%M")

        for cookie in account_files:
            arguments = [
                "-u",
                str(cookie),
                "upload",
                str(file),
                "--title",
                title,
                "--desc",
                desc or title,
                "--tid",
                str(default_tid),
            ]
            if tags:
                arguments.extend(["--tag", ",".join(tags)])
            if schedule_text:
                arguments.extend(["--dtime", str(int(publish_datetimes[index].timestamp()))])

            result = run_biliup_command(arguments)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout or "Bilibili 投稿失败")


# ==================== 图文发布函数 ====================
# 所有图文 Note 类接受 image_paths=图片列表作为一次性参数，多张图发布为一个图文笔记。

def _post_note_common(note_class, title, note_text, files, tags, account_file, enableTimer,
                      videos_per_day, daily_times, start_days, **extra_kwargs):
    """通用图文发布：所有图片作为一个列表传入 Note 类，对每个账号发布一次。"""
    account_files = _resolve_account_files(account_file)
    image_paths = _resolve_image_files(files)
    if enableTimer:
        publish_dates = generate_schedule_time_next_day(1, videos_per_day, daily_times, start_days)
        publish_date = publish_dates[0] if isinstance(publish_dates, list) else publish_dates
    else:
        publish_date = 0

    for cookie in account_files:
        print(f"图片列表：{image_paths}")
        print(f"标题：{title}")
        print(f"正文：{note_text}")
        print(f"Hashtag：{tags}")
        app = note_class(
            image_paths=image_paths,
            title=title,
            note=note_text or '',
            tags=tags,
            publish_date=publish_date,
            account_file=str(cookie),
            **extra_kwargs,
        )
        asyncio.run(app.main(), debug=False)


def post_note_xhs(title, desc, files, tags, account_file, category=None, enableTimer=False,
                  videos_per_day=1, daily_times=None, start_days=0):
    """小红书图文发布 — 对应 CLI: sau xiaohongshu upload-note"""
    _post_note_common(
        XiaoHongShuNote, title, desc, files, tags, account_file,
        enableTimer, videos_per_day, daily_times, start_days,
        desc=desc,  # XiaoHongShuNote 同时接受 note(正文) 和 desc
    )


def post_note_tencent(title, desc, files, tags, account_file, category=None, enableTimer=False,
                      videos_per_day=1, daily_times=None, start_days=0, is_draft=False):
    """视频号图文发布"""
    _post_note_common(
        TencentNote, title, desc, files, tags, account_file,
        enableTimer, videos_per_day, daily_times, start_days,
        is_draft=is_draft,
    )


def post_note_douyin(title, desc, files, tags, account_file, category=None, enableTimer=False,
                     videos_per_day=1, daily_times=None, start_days=0):
    """抖音图文发布 — 对应 CLI: sau douyin upload-note"""
    _post_note_common(
        DouYinNote, title, desc, files, tags, account_file,
        enableTimer, videos_per_day, daily_times, start_days,
    )


def post_note_ks(title, desc, files, tags, account_file, category=None, enableTimer=False,
                 videos_per_day=1, daily_times=None, start_days=0):
    """快手图文发布 — 对应 CLI: sau kuaishou upload-note"""
    _post_note_common(
        KSNote, title, desc, files, tags, account_file,
        enableTimer, videos_per_day, daily_times, start_days,
    )
