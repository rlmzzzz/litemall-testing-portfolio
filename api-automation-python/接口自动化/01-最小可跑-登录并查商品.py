# -*- coding: utf-8 -*-
"""
第一个接口自动化脚本：登录 → 查商品列表 → 顺手复现你之前发现的 Bug-8

运行方式（用我给你建好的虚拟环境）：
  C:\\Users\\李玉亭\\.workbuddy\\binaries\\python\\envs\\litemall-auto\\Scripts\\python.exe 01-最小可跑-登录并查商品.py

这一版是"纯脚本"：不用 pytest，跑完直接把结果打印出来。
目的只有一个 —— 让你先看到"代码真的把接口跑通了"。
"""

import os
import sys

# ★ 本机服务必须绕开系统代理
# 这台机器设置了 HTTP_PROXY=http://127.0.0.1:55705。requests 默认会读这个环境变量，
# 于是连 127.0.0.1:8080 的请求也发给代理，代理访问不到你的本机服务 → 返回 502。
# 这是新手最容易卡住的第一个坑：脚本没错，是代理把它带偏了。
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 用 127.0.0.1，不用 localhost —— 你在 Postman 阶段踩过：localhost 上残留的 cookie
# 会替请求开门，导致结论不可信。
BASE_URL = "http://127.0.0.1:8080"
USERNAME = "admin123"
PASSWORD = "admin123"


def login():
    """登录并取出 token。这一步就是你在 Postman 里做的'关联'。"""
    url = f"{BASE_URL}/admin/auth/login"
    resp = requests.post(
        url,
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    assert body["errno"] == 0, f"登录失败，响应：{body}"
    return body["data"]["token"]


def list_goods(token, page=1, limit=20):
    """查询商品列表，带上登录拿到的 token。"""
    url = f"{BASE_URL}/admin/goods/list"
    headers = {"X-Litemall-Admin-Token": token}
    params = {"page": page, "limit": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    token = login()
    print(f"[1] 登录成功，token = {token[:16]}...")

    body = list_goods(token, limit=20)
    items = body["data"]["list"]
    print(f"[2] limit=20 → 返回 {len(items)} 条，total = {body['data']['total']}")

    body0 = list_goods(token, limit=0)
    items0 = body0["data"]["list"]
    print(f"[3] limit=0  → 返回 {len(items0)} 条")
    print("     ↑ 本该只返回 0 条或报错，实际返回了全量 —— 这就是你提的禅道 #4（Bug-8）")
