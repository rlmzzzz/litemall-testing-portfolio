# -*- coding: utf-8 -*-
"""
litemall 自动化回归 · 一键运行

做的事（一条命令完成四步）：
    1. 用 selenium-side-runner 跑 scripts/ 下的 .side 脚本（可指定单个）
    2. 失败自动截图到 reports/screenshots/
    3. 把生成的 JSON 结果转成 HTML 报告
    4. 自动用默认浏览器打开报告

用法：
    python run_regression.py                       # 跑 scripts/ 下所有 .side（默认 Chrome）
    python run_regression.py scripts/01-xxx.side   # 只跑指定脚本
    python run_regression.py --filter 登录          # 只跑套件名含"登录"的
    python run_regression.py --browser edge        # 改用 Edge 跑（Chrome 卡时用它）
    python run_regression.py --headless            # 无头模式（不弹浏览器，跑得快）

浏览器取值（2026-09-24 本机实测通过）：
    chrome -> browserName=chrome
    edge   -> browserName=MicrosoftEdge   ← 注意不是 "edge"，写错会起不来
"""
import glob
import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
REPORTS = os.path.join(ROOT, "reports")
SHOTS = os.path.join(REPORTS, "screenshots")
CONVERTER = os.path.join(HERE, "jest_json_to_html.py")
BASE_URL = "http://localhost:9527"


def find_runner():
    """先找 PATH，再退回 npm 全局安装位置"""
    p = shutil.which("selenium-side-runner") or shutil.which("selenium-side-runner.cmd")
    if p:
        return p
    cand = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "selenium-side-runner.cmd")
    if os.path.exists(cand):
        return cand
    raise SystemExit("找不到 selenium-side-runner，请先执行：npm install -g selenium-side-runner")


def latest_json():
    files = sorted(glob.glob(os.path.join(REPORTS, "results-*.json")), key=os.path.getmtime)
    return files[-1] if files else None


def main():
    args = sys.argv[1:]
    headless = "--headless" in args
    args = [a for a in args if a != "--headless"]

    browser = "chrome"
    if "--browser" in args:
        i = args.index("--browser")
        browser = args[i + 1].lower()
        del args[i:i + 2]

    filter_name = None
    if "--filter" in args:
        i = args.index("--filter")
        filter_name = args[i + 1]
        del args[i:i + 2]

    targets = [a for a in args if a.endswith(".side")]
    if not targets:
        targets = sorted(glob.glob(os.path.join(SCRIPTS, "*.side")))
    if not targets:
        raise SystemExit(f"{SCRIPTS} 下没有 .side 脚本，先用 Selenium IDE 录一个放进来")

    os.makedirs(SHOTS, exist_ok=True)
    runner = find_runner()

    # 多个 capability 之间必须用【空格】分隔，不能用逗号：
    # 用逗号会被当成一个整体，报 "Do not know how to build driver: MicrosoftEdge,ms:edgeOptions..."
    if browser in ("edge", "msedge", "microsoftedge"):
        caps = "browserName=MicrosoftEdge"
        if headless:
            caps += " ms:edgeOptions.args=[headless,disable-gpu,window-size=1920,1080]"
    elif browser == "firefox":
        caps = "browserName=firefox"
        if headless:
            caps += " moz:firefoxOptions.args=[-headless]"
    else:
        caps = "browserName=chrome"
        if headless:
            caps += " goog:chromeOptions.args=[headless,disable-gpu,window-size=1920,1080]"
    print(f"浏览器：{browser}  →  {caps}")

    cmd = [runner, "-c", caps,
           "--output-directory", REPORTS,
           "--screenshot-failure-directory", SHOTS,
           "--timeout", "20000",
           "--jest-timeout", "120000"]
    # 注意：--base-url 会【强制覆盖】脚本里录制时填的 URL，
    # 所以默认不传（用脚本自己的），只有你显式指定时才传。
    if "--base-url" in args:
        i = args.index("--base-url")
        cmd += ["--base-url", args[i + 1]]
        del args[i:i + 2]
    if filter_name:
        cmd += ["--filter", filter_name]
    cmd += targets

    print("=" * 68)
    print("运行命令：")
    print("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    print("=" * 68)

    started = datetime.now()
    proc = subprocess.run(cmd, cwd=ROOT)
    elapsed = (datetime.now() - started).total_seconds()

    json_file = latest_json()
    if not json_file:
        print("\n没有生成结果 JSON —— 上面大概率是启动阶段的错误（如驱动/浏览器没装好）。")
        sys.exit(proc.returncode)

    html_out = os.path.join(REPORTS, "回归测试报告.html")
    subprocess.run([sys.executable, CONVERTER, json_file, html_out], check=False)

    print("\n" + "=" * 68)
    print(f"耗时 {elapsed:.1f} s　｜　退出码 {proc.returncode}")
    print(f"HTML 报告：{html_out}")
    print("=" * 68)

    if "--no-open" not in sys.argv:
        webbrowser.open("file:///" + html_out.replace("\\", "/"))

    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
