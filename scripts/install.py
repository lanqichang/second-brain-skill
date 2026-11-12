#!/usr/bin/env python3
"""第二大脑安装器：把 template/ 里的骨架装到用户指定的文件夹。

只用 Python 标准库，macOS / Windows / Linux 通用。
原则：只新增，不覆盖。目标位置已有的同名文件一律跳过并列出来。

用法：
  python3 install.py --suggest                 # 列出本机推荐的安装位置（JSON）
  python3 install.py --target "<文件夹路径>"     # 安装
  python3 install.py --target "<路径>" --dry-run # 只看会做什么，不写入
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / 'template'
FOLDER_NAME = '第二大脑'
CLAUDE_STUB = """# CLAUDE.md

本库的规则统一写在 `AGENTS.md`，请直接读那一份并照着执行。这里不写规则。

@AGENTS.md
"""
RISKY = ('Desktop', 'Downloads', '桌面', '下载')


def suggest():
    """按操作系统给出推荐位置，第一项是首选。"""
    home = Path.home()
    out = []
    if sys.platform == 'darwin':
        icloud = home / 'Library/Mobile Documents/com~apple~CloudDocs'
        if icloud.is_dir():
            out.append({'label': 'iCloud 云盘', 'path': str(icloud / FOLDER_NAME),
                        'why': '多台苹果设备自动同步，电脑坏了也不丢'})
    elif sys.platform.startswith('win'):
        if Path('D:/').exists():
            out.append({'label': 'D 盘根目录', 'path': 'D:\\' + FOLDER_NAME,
                        'why': '路径短，重装系统不受影响'})
        onedrive = os.environ.get('OneDrive')
        if onedrive and Path(onedrive).is_dir():
            out.append({'label': 'OneDrive', 'path': str(Path(onedrive) / FOLDER_NAME),
                        'why': '多台设备自动同步'})
    out.append({'label': '文稿（Documents）', 'path': str(home / 'Documents' / FOLDER_NAME),
                'why': '只存在本机，最简单'})
    return out


def plan(target):
    """返回 (要建的目录, 要复制的文件, 已存在而跳过的文件)。"""
    dirs, copies, skipped = [], [], []
    for src in sorted(TEMPLATE.rglob('*')):
        if src.name == '.DS_Store':
            continue
        dst = target / src.relative_to(TEMPLATE)
        if src.is_dir():
            if not dst.exists():
                dirs.append(dst)
        elif dst.exists():
            skipped.append(dst)
        else:
            copies.append((src, dst))
    return dirs, copies, skipped


def link_claude(target, dry):
    """CLAUDE.md 指向 AGENTS.md：优先软链接，建不了（常见于 Windows）就写一份指路文件。"""
    dst = target / 'CLAUDE.md'
    if dst.exists() or dst.is_symlink():
        return '已存在，未改动'
    if dry:
        return '将创建'
    try:
        os.symlink('AGENTS.md', dst)
        return '软链接 → AGENTS.md'
    except (OSError, NotImplementedError):
        dst.write_text(CLAUDE_STUB, encoding='utf-8')
        return '指路文件（本机不支持软链接）'


def main():
    # 中文 Windows 的控制台默认不是 UTF-8，不处理的话打印表情符号会报错
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description='第二大脑安装器')
    ap.add_argument('--target', help='安装到哪个文件夹（完整路径，不存在会新建）')
    ap.add_argument('--suggest', action='store_true', help='列出推荐的安装位置')
    ap.add_argument('--dry-run', action='store_true', help='只预览，不写入')
    a = ap.parse_args()

    if a.suggest:
        print(json.dumps(suggest(), ensure_ascii=False, indent=2))
        return 0
    if not a.target:
        ap.error('请用 --target 指定安装位置，或先用 --suggest 看推荐位置')
    if not TEMPLATE.is_dir():
        print('❌ 找不到模板目录：' + str(TEMPLATE))
        return 2

    target = Path(a.target).expanduser().resolve()
    if target.is_file():
        print('❌ 这个路径是一个文件，不是文件夹：' + str(target))
        return 2
    if TEMPLATE in target.parents or target == TEMPLATE:
        print('❌ 不能装进 skill 自己的模板目录，请换一个位置')
        return 2

    existing = [p.name for p in target.iterdir() if p.name != '.DS_Store'] if target.is_dir() else []
    dirs, copies, skipped = plan(target)

    print(('【预览】' if a.dry_run else '') + '安装位置：' + str(target))
    if any(part in RISKY for part in target.parts):
        print('⚠️ 这个位置在桌面或下载文件夹里，容易被误删或清理，建议换一个')
    if existing:
        print(f'ℹ️ 文件夹里已有 {len(existing)} 项内容，只补缺少的，不覆盖已有的')

    if not a.dry_run:
        target.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        for src, dst in copies:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    claude = link_claude(target, a.dry_run)

    verb = '将新增' if a.dry_run else '已新增'
    print(f'{verb} {len(copies)} 个文件、{len(dirs)} 个文件夹；CLAUDE.md：{claude}')
    for _, dst in copies:
        print('  + ' + str(dst.relative_to(target)))
    if skipped:
        print(f'已存在而跳过 {len(skipped)} 个文件（未改动）：')
        for p in skipped:
            print('  = ' + str(p.relative_to(target)))
    if not a.dry_run:
        print('✅ 完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
