"""
一键运行：启动 mock 服务 -> 跑 pytest -> 出 HTML 报告 -> 自动关服务。
用法：
    & "C:/Users/李玉亭/.workbuddy/binaries/python/envs/litemall-auto/Scripts/python.exe" run_tests.py
"""
import os
import sys
import time
import threading
import subprocess

# 本机请求不走代理（避免你之前遇到的 502）
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from mock_api import run_server

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"


def main():
    os.chdir(ROOT)
    os.makedirs("reports", exist_ok=True)

    # 后台启动 mock 服务
    t = threading.Thread(target=run_server, kwargs={"port": PORT}, daemon=True)
    t.start()
    time.sleep(1.5)  # 等一秒确保服务就绪

    env = os.environ.copy()
    env["BASE_URL"] = BASE

    cmd = [
        sys.executable, "-m", "pytest", "tests",
        "--html=reports/api-test-report.html",
        "--self-contained-html",
        "-v",
    ]
    result = subprocess.run(cmd, env=env)
    print("\n报告已生成：reports/api-test-report.html")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
