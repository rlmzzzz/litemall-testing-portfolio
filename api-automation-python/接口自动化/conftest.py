# -*- coding: utf-8 -*-
"""
conftest.py —— pytest 的"公共配置"文件

这个文件叫什么名字是固定的（不能改），pytest 运行时会自动先加载它。
它的作用：**把多个用例都要用的东西放这里，避免每条用例都重复写一遍。**

这个文件里有两个东西值得学：
  1. 代理绕行的开关（放这里，所有用例自动生效）
  2. fixture —— pytest 最核心的概念，看下面 token 那个
"""

import os

# ★ 本机服务必须绕开系统代理（所有测试用例共享这一个开关）
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import pytest
import requests

# 用 127.0.0.1 而不是 localhost —— 你在 Postman 阶段踩过：localhost 上残留的
# JSESSIONID cookie 会替请求开门，导致"假绿"。
BASE_URL = "http://127.0.0.1:8080"

ADMIN_USER = "admin123"
ADMIN_PASS = "admin123"

HEADER_TOKEN = "X-Litemall-Admin-Token"


def login(username, password):
    """登录。失败会抛异常，让用例变红。"""
    resp = requests.post(
        f"{BASE_URL}/admin/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_goods_list(token=None, page=1, limit=20):
    """查商品列表。token 不传就是"未登录"的请求。"""
    headers = {HEADER_TOKEN: token} if token else {}
    resp = requests.get(
        f"{BASE_URL}/admin/goods/list",
        params={"page": page, "limit": limit},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# fixture：pytest 的核心概念
#
# 一句话理解：**fixture 就是"用例运行前，由 pytest 自动帮你准备好的东西"。**
#
# 对比一下你就懂了：
#   不用 fixture：每条用例第一行都写一遍 "登录 → 拿 token"，重复 N 次
#   用 fixture  ：只写一次，谁需要就在参数里写它的名字，pytest 自动传进来
#
# scope="session" 表示：整个测试过程只登录一次，所有用例共用这同一个 token。
#   为什么？因为登录接口内部要做 BCrypt 加密，故意做得慢（你压测时测过它占
#   整个事务 90% 的耗时）。10 条用例各登一次 = 白白多花好几秒。
#   如果设成 scope="function"（默认），就是每条用例跑之前都重新登录一次。
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def token():
    """给所有需要登录态的用例提供 token。"""
    body = login(ADMIN_USER, ADMIN_PASS)
    assert body["errno"] == 0, f"前置登录失败：{body}"
    return body["data"]["token"]
